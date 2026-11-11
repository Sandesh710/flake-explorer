"""The single-panel Colab interface. Scientific calculations live in other modules."""
from pathlib import Path
from dataclasses import asdict, replace
from html import escape
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import ipywidgets as W
from IPython.display import display, HTML, FileLink
from .data_access import InputStore, ROOT
from .configuration import ModelOptions, InitialConditions
from .experiments import ExperimentRunner, lake_from_row, default_initial, default_options, area_retention, SCENARIO_LABELS
from .indicators import annual_indicators, baseline_statistics
from .annual_plot import annual_figure
from .plotting import thermal_figure, winter_figure, location_map
from .downloads import export_experiment

CSS = '''<style>
.flake-dashboard {font-family:Arial,sans-serif;color:#182b38;max-width:1320px;margin:auto;}
.flake-dashboard .widget-label {font-size:13px!important;color:#182b38!important;}
.flake-dashboard .widget-text input,.flake-dashboard select {font-size:14px!important;}
.flake-dashboard .widget-button {font-weight:600;border-radius:5px;}
.flake-card {border:1px solid #dce3e7;border-radius:8px;padding:14px;background:white;}
.flake-small {font-size:12px;color:#50616c;line-height:1.5;}
.flake-title {font-size:27px;font-weight:700;letter-spacing:-.5px;margin:0 0 7px;}
.flake-status {padding:10px 14px;border-radius:5px;background:#edf4f7;color:#264c62;font-size:14px;}
.flake-dashboard .widget-tab-contents {padding:12px!important;}
.flake-dashboard .leaflet-container {background:#eef3f6!important;}
.flake-region-label {background:none!important;border:0!important;}
</style>'''

MAP_CENTER = (46.1, -93.5)
MAP_ZOOM = 5.75
REGION_LABELS = [(46.2, -94.4, 'MINNESOTA'), (49.7, -94.4, 'CANADA'),
                 (44.8, -90.3, 'WISCONSIN'), (42.9, -93.5, 'IOWA')]


def _number(description, value=0):
    return W.FloatText(description=description, value=float(value),
        style={'description_width': '160px'}, layout=W.Layout(width='320px', max_width='100%'))


def _grid(children):
    return W.Box(children, layout=W.Layout(display='flex', flex_flow='row wrap', grid_gap='4px 14px'))


class Dashboard:
    def __init__(self, root=ROOT, local_export=None, cache=None, default_lake='10000200', store=None):
        self.root = Path(root)
        self.store = store or InputStore(root, local_export, cache)
        self.runner = ExperimentRunner(self.store)
        self.catalogue = self.store.catalogue
        preview_file = self.root / 'preview_lakes.json'
        if preview_file.is_file():
            import json
            available = json.loads(preview_file.read_text())
            self.catalogue = self.catalogue.loc[self.catalogue.DOWLKNUM.isin(available)].copy()
        self.result = None
        self.annual = None
        self.figures = {}
        self._updating = False
        self._stale = False
        self._building = True
        self._map_available = False
        self.labels = {str(r['DOWLKNUM']): '{} · {} · {}'.format(str(r['LAKE_NAME']), str(r['CTY_NAME']).title(), r['DOWLKNUM']) for r in self.catalogue.to_dict('records')}
        self.ids_by_label = {v: k for k, v in self.labels.items()}
        if default_lake not in self.labels:
            default_lake = str(self.catalogue.iloc[0].DOWLKNUM)
        self.lake_id = default_lake
        self.lake_choice = W.Combobox(options=sorted(self.ids_by_label), value=self.labels[default_lake],
            description='Lake', ensure_option=True, placeholder='Search lake name, county or ID',
            style={'description_width': '40px'}, layout=W.Layout(width='100%'))
        self.scenario = W.Dropdown(options=[(v, k) for k, v in SCENARIO_LABELS.items()], value='ssp245',
            description='Scenario', style={'description_width': '80px'}, layout=W.Layout(width='280px'))
        self.depth = _number('D · Mean depth (m)')
        self.fetch = _number('F · Fetch (m)')
        self.area = _number('A · Area (km²)')
        self.optics = W.ToggleButtons(options=[('Supplied optics', 'supplied'), ('Constant κd', 'constant')], value='supplied')
        self.kd = _number('κd · Extinction (m⁻¹)', 1)
        self.retention_mode = W.ToggleButtons(options=[('Area relation', 'area'), ('Manual retention', 'manual')], value='area')
        self.retention = _number('Rs · Snow retention', .5)
        self.snow = W.Checkbox(value=True, description='Snow cover', indent=False)
        self.sediments = W.Checkbox(value=True, description='Sediment heat exchange', indent=False)
        self.boundary_depth = _number('Dbs · Boundary depth (m)', 5)
        self.boundary_temp = _number('Tbs · Boundary temp. (°C)', 6)
        initial_labels = {'mixed_layer_temperature_c': 'TML,0 · Mixed layer (°C)', 'bottom_temperature_c': 'Tb,0 · Bottom water (°C)',
            'mixed_layer_depth_m': 'hML,0 · Mixed layer (m)', 'thermocline_shape_factor': 'CT,0 · Shape factor',
            'ice_thickness_m': 'hi,0 · Ice thickness (m)', 'snow_thickness_m': 'hs,0 · Snow thickness (m)',
            'ice_temperature_c': 'Ti,0 · Ice temp. (°C)', 'snow_temperature_c': 'Ts,0 · Snow temp. (°C)',
            'sediment_layer_m': 'HB1,0 · Sediment layer (m)', 'sediment_temperature_c': 'TB1,0 · Sediment temp. (°C)'}
        self.initial_fields = {k: _number(v) for k, v in initial_labels.items()}
        self.advanced_fields = {k: _number(label, default) for k, label, default in [
            ('dry_snow_albedo', 'αs,dry · Snow albedo', .6), ('melting_snow_albedo', 'αs,melt · Snow albedo', .1),
            ('white_ice_albedo', 'αi,white · Ice albedo', .6), ('blue_ice_albedo', 'αi,blue · Ice albedo', .1),
            ('minimum_snow_conductivity', 'κs,min · W m⁻¹ K⁻¹', .3), ('wind_height_m', 'zu · Wind height (m)', 10),
            ('temperature_humidity_height_m', 'ztq · T/humidity (m)', 2), ('air_pressure_pa', 'pa · Pressure (Pa)', 100000)]}
        initial_note = W.HTML('<p class="flake-small">Initial conditions apply on <b>1 January 1950</b>. The model warms up through 1994 before displaying 1995–2099. Defaults use the production state; its bottom-water adjustment is approximately 3.98 °C. Initial sediment temperature TB1,0 is separate from the lower-boundary temperature Tbs.</p>')
        self.extra = W.Accordion(children=[W.VBox([initial_note, _grid(list(self.initial_fields.values()))]), _grid(list(self.advanced_fields.values()))], selected_index=None)
        self.extra.set_title(0, 'Initial conditions · 1 January 1950')
        self.extra.set_title(1, 'Surface exchange and albedo')
        self.reset_button = W.Button(description='Restore lake defaults', icon='undo', layout=W.Layout(width='190px'))
        self.run_button = W.Button(description='Run simulation', button_style='primary', icon='play', layout=W.Layout(width='190px', height='40px'))
        self.download_button = W.Button(description='Download results', icon='download', disabled=True, layout=W.Layout(width='180px'))
        self.map_home = W.Button(description='Minnesota overview', icon='map', layout=W.Layout(width='180px'))
        self.info = W.HTML()
        self.status = W.HTML()
        self.baseline_info = W.HTML()
        self.errors = W.Output()
        self.map_panel = self._create_map()
        self.change_mode = W.ToggleButtons(options=[('Absolute values', False), ('Change from baseline', True)], value=False)
        self.thermal_year = W.Dropdown(options=list(range(1995, 2100)), value=2012, description='Year', disabled=True, layout=W.Layout(width='210px'))
        self.winter_year = W.Dropdown(options=[('{}–{}'.format(y-1, y), y) for y in range(1995, 2100)], value=2014, description='Winter', disabled=True, layout=W.Layout(width='230px'))
        self.outputs = [W.Output(), W.Output(), W.Output()]
        self.result_tabs = W.Tab(children=[W.VBox([self.change_mode, self.outputs[0], self.baseline_info]),
            W.VBox([self.thermal_year, self.outputs[1], W.HTML('<p class="flake-small">The longest continuous open-water interval in the selected year. Vertical temperatures follow FLake’s bulk-profile reconstruction (Mironov, 2008); the thin line marks mixed-layer depth.</p>')]),
            W.VBox([self.winter_year, self.outputs[2], W.HTML('<p class="flake-small">Snow above the interface; ice extends downward. The window follows cover formation and melt, with approximately ten days of padding.</p>')])])
        for i, title in enumerate(['Annual response', 'Thermal structure', 'Snow and ice']):
            self.result_tabs.set_title(i, title)
        coverage = '1,925 Minnesota lakes' if len(self.catalogue) == 1925 else '{} preview lakes · full catalogue: 1,925'.format(len(self.catalogue))
        heading = W.HTML('<div class="flake-title">FLake: a Python implementation</div><p>Explore lake temperature, mixing, snow and ice under a changing climate.</p><p class="flake-small"><b>GFDL-ESM4</b> · '+coverage+' · Baseline 1995–2014 · Projections 2015–2099</p>')
        self.setup_controls = [self.lake_choice, self.scenario, self.depth, self.fetch, self.area, self.optics, self.kd,
            self.retention_mode, self.retention, self.snow, self.sediments, self.boundary_depth, self.boundary_temp] + list(self.initial_fields.values()) + list(self.advanced_fields.values())
        properties = W.VBox([W.HTML('<h3 style="margin:3px 0 8px">Lake and model settings</h3>'),
            _grid([self.depth, self.fetch, self.area]), self.optics, self.kd,
            self.retention_mode, self.retention, W.HBox([self.snow, self.sediments]),
            W.HTML('<span class="flake-small">Retention adjusts snow accumulation using the lake-area relation or your chosen factor (0–1). Snow off keeps lake-ice thermodynamics active.</span>'),
            _grid([self.boundary_depth, self.boundary_temp])], layout=W.Layout(flex='1 1 340px', min_width='300px'))
        map_area = W.VBox([self.map_panel, self.info, self.map_home], layout=W.Layout(flex='1 1 440px', min_width='300px'))
        top = W.Box([map_area, properties], layout=W.Layout(display='flex', flex_flow='row wrap', grid_gap='18px', align_items='flex-start'))
        setup = W.VBox([W.HBox([self.lake_choice, self.scenario], layout=W.Layout(flex_flow='row wrap')), top,
            self.extra, W.HBox([self.run_button, self.reset_button, self.download_button], layout=W.Layout(flex_flow='row wrap', grid_gap='8px'))])
        setup.add_class('flake-card')
        self.widget = W.VBox([heading, setup, self.status, self.errors, self.result_tabs,
            W.HTML('<p class="flake-small">FLake: Dmitrii Mironov and collaborators, German Weather Service (DWD). Model reference: Mironov (2008), COSMO Technical Report 11. Native incoming longwave is supplied directly. Model data use a 365-day calendar.</p>')])
        self.widget.add_class('flake-dashboard')
        self.lake_choice.observe(self._lake_changed, names='value')
        self.area.observe(self._area_changed, names='value')
        self.retention_mode.observe(self._area_changed, names='value')
        self.optics.observe(self._enabled_fields, names='value')
        self.snow.observe(self._enabled_fields, names='value')
        self.sediments.observe(self._enabled_fields, names='value')
        self.depth.observe(self._depth_changed, names='value')
        for control in self.setup_controls:
            if control is not self.lake_choice:
                control.observe(self._mark_stale, names='value')
        self.run_button.on_click(self._run)
        self.reset_button.on_click(lambda button: self._set_lake(self.lake_id, move_map=False))
        self.download_button.on_click(self._download)
        self.map_home.on_click(self._overview)
        self.change_mode.observe(lambda change: self._draw(0), names='value')
        self.thermal_year.observe(lambda change: self._draw(1), names='value')
        self.winter_year.observe(lambda change: self._draw(2), names='value')
        self.result_tabs.observe(lambda change: self._draw(change['new']), names='selected_index')
        self._set_lake(default_lake, move_map=False)
        self._building = False
        self._set_status('Choose a lake and settings, then run the simulation.')
        for output in self.outputs:
            with output:
                display(HTML('<p class="flake-small">Results appear here after your run.</p>'))

    def _set_status(self, text, warning=False):
        color = '#fff5e4' if warning else '#edf4f7'
        self.status.value = '<div class="flake-status" style="background:{}">{}</div>'.format(color, escape(text))

    def _create_map(self):
        try:
            from ipyleaflet import Map, GeoJSON, CircleMarker, ScaleControl, WidgetControl, AttributionControl, Marker, Icon
            import base64
            # The background is bundled vector geometry. No raster tile provider,
            # API key, or external map request is needed in Colab.
            self.map = Map(layers=(), center=MAP_CENTER, zoom=MAP_ZOOM, zoom_snap=.25, zoom_delta=.5, min_zoom=5, max_zoom=13,
                attribution_control=False, scroll_wheel_zoom=True,
                layout=W.Layout(width='100%', height='430px'))
            boundary = __import__('json').loads((self.root / 'assets/region_states.geojson').read_text())
            def region_style(feature):
                is_mn = feature['properties']['name'] == 'Minnesota'
                return {'color': '#526975' if is_mn else '#a8b8c2', 'weight': 1.4 if is_mn else .8,
                        'fillColor': '#fffefa' if is_mn else '#e5edf1', 'fillOpacity': 1}
            self.map.add(GeoJSON(data=boundary, style_callback=region_style))
            for lat, lon, label in REGION_LABELS:
                # A transparent SVG image avoids DivIcon's default white box,
                # including in Colab where outer notebook CSS is isolated.
                svg = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="24"><text x="60" y="12" text-anchor="middle" dominant-baseline="central" font-family="Arial,sans-serif" font-size="11" font-weight="600" letter-spacing=".7" fill="#627987">'+label+'</text></svg>'
                icon = Icon(icon_url='data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode(),
                    icon_size=[120, 24], icon_anchor=[60, 12], shadow_url='')
                self.map.add(Marker(location=(lat, lon), icon=icon, draggable=False, keyboard=False))
            features = []
            for row in self.catalogue.to_dict('records'):
                features.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [float(row['lon']), float(row['lat'])]},
                    'properties': {'lake_id': str(row['DOWLKNUM']), 'depth': float(row['depth_w']), 'area': float(row['area_km2'])}})
            from .map_style import point_style, depth_legend_html, area_legend_html
            self.points = GeoJSON(data={'type': 'FeatureCollection', 'features': features},
                point_style={'radius': 4}, style_callback=point_style,
                hover_style={'color': '#142f42', 'weight': 2, 'fillOpacity': 1})
            self.points.on_click(self._map_selected)
            self.map.add(self.points)
            self.marker = CircleMarker(location=(46.2, -94.4), radius=10, color='#152f41',
                weight=2, fill_color='#f0aa38', fill_opacity=1)
            self.map.add(self.marker)
            self.map.add(ScaleControl(position='bottomleft', imperial=False))
            self.map.add(AttributionControl(position='bottomright', prefix='Boundaries: U.S. Census Bureau (2024)'))
            self.map.add(WidgetControl(widget=W.HTML(depth_legend_html()), position='topright'))
            self.map.add(WidgetControl(widget=W.HTML(area_legend_html()), position='bottomright'))
            self._map_available = True
            return self.map
        except ImportError:
            self.static_map = W.Output()
            return W.VBox([W.HTML('<p class="flake-small">Interactive map is unavailable in this environment. Use the lake search above; Colab setup installs the interactive map dependency.</p>'), self.static_map])

    def _overview(self, button=None):
        if self._map_available:
            self.map.center = MAP_CENTER; self.map.zoom = MAP_ZOOM

    def _map_selected(self, **event):
        key = str(event.get('feature', {}).get('properties', {}).get('lake_id', ''))
        if key in self.labels:
            self.lake_choice.value = self.labels[key]

    def _lake_changed(self, event):
        if not self._updating and event['new'] in self.ids_by_label:
            self._set_lake(self.ids_by_label[event['new']])

    def _set_lake(self, key, move_map=True):
        self._updating = True
        try:
            self.lake_id = key
            row = self.catalogue.loc[self.catalogue.DOWLKNUM.eq(key)].iloc[0].to_dict()
            self.lake_choice.value = self.labels[key]
            lake, options, initial = lake_from_row(row), default_options(row), default_initial(row)
            self.depth.value, self.fetch.value, self.area.value = lake.mean_depth_m, lake.fetch_m, lake.area_km2
            self.optics.value = 'supplied'; self.kd.value = float(row['kd_longterm_median'])
            self.retention_mode.value = 'area'; self.retention.value = lake.snow_retention
            self.snow.value = True; self.sediments.value = True
            self.boundary_depth.value, self.boundary_temp.value = options.sediment_depth_m, options.sediment_temperature_c
            for name, value in asdict(initial).items():
                self.initial_fields[name].value = value
            for name in self.advanced_fields:
                self.advanced_fields[name].value = getattr(options, name)
            self.info.value = '<p class="flake-small"><b>{}</b> · {} County · {:.3f}°N, {:.3f}°W<br>Recorded mean depth {:.2f} m · area {:.2f} km². Points show lake locations.</p>'.format(
                escape(lake.name), escape(lake.county.title()), lake.latitude, abs(lake.longitude), lake.mean_depth_m, lake.area_km2)
            if self._map_available:
                self.marker.location = (lake.latitude, lake.longitude)
                self.marker.popup = W.HTML('<b>{}</b><br>{:.2f} m mean depth'.format(escape(lake.name), lake.mean_depth_m))
                if move_map:
                    self.map.center = self.marker.location; self.map.zoom = 8
            else:
                renamed = self.catalogue.rename(columns={'DOWLKNUM': 'lake_id', 'LAKE_NAME': 'name', 'lon': 'longitude', 'lat': 'latitude', 'depth_w': 'mean_depth_m'})
                with self.static_map:
                    self.static_map.clear_output(wait=True)
                    figure = location_map(renamed, key, self.root)
                    display(figure); plt.close(figure)
        finally:
            self._updating = False
        self._enabled_fields()
        self._mark_stale()

    def _enabled_fields(self, event=None):
        self.kd.disabled = self.optics.value != 'constant'
        self.retention.disabled = self.retention_mode.value != 'manual'
        for field in [self.boundary_depth, self.boundary_temp, self.initial_fields['sediment_layer_m'], self.initial_fields['sediment_temperature_c']]:
            field.disabled = not self.sediments.value
        for field in [self.initial_fields['snow_thickness_m'], self.initial_fields['snow_temperature_c']]:
            field.disabled = not self.snow.value
        if not self.snow.value:
            self.initial_fields['snow_thickness_m'].value = 0

    def _area_changed(self, event=None):
        self.retention.disabled = self.retention_mode.value != 'manual'
        if self.retention_mode.value == 'area' and np.isfinite(self.area.value) and self.area.value > 0:
            self.retention.value = area_retention(self.area.value)

    def _depth_changed(self, event):
        if not self._updating and abs(self.initial_fields['mixed_layer_depth_m'].value - event['old']) < 1e-10:
            self.initial_fields['mixed_layer_depth_m'].value = event['new']

    def _mark_stale(self, event=None):
        if self._updating or self._building:
            return
        if self.result is not None:
            self._stale = True
            self.download_button.disabled = True
            self._set_status('Settings changed. Run the simulation to update the results below.', warning=True)

    def configuration(self):
        if self.lake_choice.value not in self.ids_by_label:
            raise ValueError('Choose a lake from the search suggestions.')
        row = self.catalogue.loc[self.catalogue.DOWLKNUM.eq(self.lake_id)].iloc[0].to_dict()
        lake = replace(lake_from_row(row), mean_depth_m=self.depth.value, fetch_m=self.fetch.value,
            area_km2=self.area.value, snow_retention=self.retention.value)
        options = ModelOptions(snow=self.snow.value, sediments=self.sediments.value,
            sediment_depth_m=self.boundary_depth.value, sediment_temperature_c=self.boundary_temp.value,
            light_extinction_m_inv=self.kd.value if self.optics.value == 'constant' else None,
            **{k: v.value for k, v in self.advanced_fields.items()})
        initial = InitialConditions(**{k: v.value for k, v in self.initial_fields.items()})
        return lake, options, initial

    def _run(self, button=None):
        self.errors.clear_output()
        disabled = [(w, w.disabled) for w in self.setup_controls]
        self.run_button.disabled = True; self.reset_button.disabled = True; self.download_button.disabled = True
        try:
            lake, options, initial = self.configuration()
            for control, old in disabled:
                control.disabled = True
            result = self.runner.run(lake, options, initial, self.scenario.value, self._set_status)
            annual = annual_indicators(result.simulation.daily)
            self.result, self.annual, self.figures = result, annual, {}
            self._stale = False
            self.thermal_year.disabled = False; self.winter_year.disabled = False
            self.result_tabs.selected_index = 0
            self._draw(0)
            self._set_status('Complete · {} · {} · 1995–2099. Choose a result tab or download your experiment.'.format(lake.name, SCENARIO_LABELS[result.scenario]))
        except Exception as exc:
            self._set_status(str(exc), warning=True)
            self._stale = True
        finally:
            for control, old in disabled:
                control.disabled = old
            self._enabled_fields()
            self.run_button.disabled = False; self.reset_button.disabled = False
            self.download_button.disabled = self.result is None or self._stale

    def _draw(self, index):
        if self.result is None or index is None:
            return
        output = self.outputs[index]
        with output:
            output.clear_output(wait=True)
            try:
                if index == 0:
                    figure = annual_figure(self.result, self.annual, self.change_mode.value)
                    name = 'annual_response'
                    self.baseline_info.value = '<p class="flake-small">Shading: near-century 2020–2040, mid-century 2050–2070, end-century 2080–2099. Sen’s slopes: 2015–2099.</p>'
                elif index == 1:
                    figure = thermal_figure(self.result.simulation, self.thermal_year.value, view='open_water')
                    name = 'thermal_{}'.format(self.thermal_year.value)
                else:
                    figure = winter_figure(self.result.simulation, self.winter_year.value)
                    name = 'winter_{}-{}'.format(self.winter_year.value-1, self.winter_year.value)
                self.figures[index] = (name, figure)
                display(figure); plt.close(figure)
            except ValueError as exc:
                self.figures.pop(index, None)
                display(HTML('<p>{}</p>'.format(escape(str(exc)))))

    def _download(self, button=None):
        if self.result is None or self._stale:
            return
        self.download_button.disabled = True
        try:
            for index in range(3):
                self._draw(index)
            figures = {name: figure for name, figure in self.figures.values()}
            archive = export_experiment(self.result, self.annual, figures, self.store.cache / 'results',
                views={'annual_changes_from_baseline': self.change_mode.value, 'thermal_year': self.thermal_year.value,
                       'winter_ending_year': self.winter_year.value})
            try:
                from google.colab import files
                files.download(str(archive))
            except ImportError:
                with self.errors:
                    print('Results:', archive)
                    display(FileLink(str(archive)))
        except Exception as exc:
            self._set_status('Download could not be prepared: ' + str(exc), warning=True)
        finally:
            self.download_button.disabled = False

    def display(self):
        display(HTML(CSS))
        display(self.widget)
        return self


def launch(root=ROOT, local_export=None, cache=None, default_lake='10000200'):
    return Dashboard(root=root, local_export=local_export, cache=cache, default_lake=default_lake).display()
