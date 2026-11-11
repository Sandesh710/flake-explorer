"""Warm-up, historical integration and SSP continuation for one experiment."""
from dataclasses import dataclass, asdict
from collections import OrderedDict
import hashlib
import json
import numpy as np
import pandas as pd
from .configuration import Lake, ModelOptions, InitialConditions
from .model import simulate, Simulation, _engine

SCENARIO_LABELS = {'ssp126': 'SSP1-2.6', 'ssp245': 'SSP2-4.5', 'ssp370': 'SSP3-7.0', 'ssp585': 'SSP5-8.5'}


def area_retention(area_km2):
    area = float(area_km2)
    if not np.isfinite(area) or area <= 0:
        raise ValueError('Lake area must be positive and finite.')
    return float(.1 + .9 * np.exp(-((area / .5104) ** .2116)))


def lake_from_row(row):
    return Lake(name=str(row['LAKE_NAME']), lake_id=str(row['DOWLKNUM']), county=str(row['CTY_NAME']),
        mean_depth_m=float(row['depth_w']), fetch_m=float(row['fetch_m']), latitude=float(row['lat']),
        longitude=float(row['lon']), area_km2=float(row['area_km2']),
        snow_retention=float(row['retention_supplied_to_flake']), coriolis_s_inv=float(row['par_Coriolis']))


def default_options(row):
    return ModelOptions(sediment_depth_m=float(row['depth_bs_m']), sediment_temperature_c=float(row['T_bs_C']))


def production_state(row):
    """Exact production initialization arithmetic, including the density-maximum adjustment."""
    lake, options = lake_from_row(row), default_options(row)
    engine = _engine(options)
    top, bottom = float(row['T_wML_init_C']) + 273.15, float(row['T_bot_init_C']) + 273.15
    h, mean = float(row['h_ML_init_m']), top
    if abs(top - bottom) < 1e-12 and top > engine.tpl_T_r:
        bottom = engine.tpl_T_r
        mean = (h * top + max(lake.mean_depth_m - h, 0.) * (.5 * (top + bottom))) / lake.mean_depth_m
    return {'T_snow_K': float(engine.tpl_T_f), 'T_ice_K': float(engine.tpl_T_f),
        'T_mnw_K': float(mean), 'T_wML_K': float(top), 'T_bot_K': float(bottom),
        'T_B1_K': options.sediment_temperature_c + 273.15, 'C_T': float(engine.C_T_min),
        'h_snow_m': 0., 'h_ice_m': float(row['h_ice_init_m']), 'h_ML_m': h,
        'H_B1_m': options.sediment_depth_m, 'T_sfc_K': float(top)}


def default_initial(row):
    s = production_state(row)
    return InitialConditions(mixed_layer_temperature_c=s['T_wML_K'] - 273.15,
        bottom_temperature_c=s['T_bot_K'] - 273.15, mixed_layer_depth_m=s['h_ML_m'],
        thermocline_shape_factor=s['C_T'], ice_thickness_m=s['h_ice_m'], snow_thickness_m=s['h_snow_m'],
        ice_temperature_c=s['T_ice_K'] - 273.15, snow_temperature_c=s['T_snow_K'] - 273.15,
        sediment_layer_m=s['H_B1_m'], sediment_temperature_c=s['T_B1_K'] - 273.15)


@dataclass
class ExperimentResult:
    simulation: Simulation
    scenario: str
    settings: dict
    identity: str

    @property
    def display_daily(self):
        return self.simulation.daily.loc[self.simulation.daily.date >= '1995-01-01'].copy()


class ExperimentRunner:
    def __init__(self, store):
        self.store = store
        self.history_cache = OrderedDict()
        self.result_cache = OrderedDict()

    @staticmethod
    def _remember(cache, key, value, maximum=2):
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > maximum:
            cache.popitem(last=False)

    def run(self, lake, options, initial, scenario, progress=lambda message: None):
        if scenario not in SCENARIO_LABELS:
            raise ValueError('Choose one of the four SSP scenarios.')
        lake.validate(); options.validate()
        state = initial.state(lake, options)
        row = self.store.catalogue.loc[self.store.catalogue.DOWLKNUM.eq(lake.lake_id)]
        if len(row) != 1:
            raise ValueError('Choose a catalogue lake before running.')
        row = row.iloc[0].to_dict()
        default_mode = (lake == lake_from_row(row) and options == default_options(row) and initial == default_initial(row))
        if default_mode:
            state = production_state(row)
        settings = {'lake': asdict(lake), 'options': asdict(options), 'initial_conditions': asdict(initial),
            'initial_state': state, 'initial_date': '1950-01-01', 'warmup': [1950, 1994],
            'baseline': [1995, 2014], 'display_period': [1995, 2099],
            'forcing_model': 'GFDL-ESM4', 'calendar': '365_day', 'data_manifest_sha256': self.store.identity,
            'initialization_mode': 'production_defaults' if default_mode else 'user_defined'}
        history_key = hashlib.sha256(json.dumps(settings, sort_keys=True, allow_nan=False).encode()).hexdigest()
        key = history_key + ':' + scenario
        if key in self.result_cache:
            progress('Showing the cached result for these settings.')
            return self.result_cache[key]
        if history_key not in self.history_cache:
            progress('Loading historical weather…')
            historical = self.store.load(lake.lake_id, 'historical', progress)
            progress('Warming up the lake: 1950–1994…')
            warmup = simulate(lake, historical.loc[historical.date < '1995-01-01'], options, restart=state)
            # Preserve the preceding July–December for the complete winter ending in 1995.
            context = warmup.daily.loc[warmup.daily.date >= '1994-07-01'].copy()
            progress('Simulating the baseline: 1995–2014…')
            baseline = simulate(lake, historical.loc[historical.date >= '1995-01-01'], options, restart=warmup.final_state)
            self._remember(self.history_cache, history_key, (context, baseline))
        context, baseline = self.history_cache[history_key]
        progress('Loading {} weather…'.format(SCENARIO_LABELS[scenario]))
        future_inputs = self.store.load(lake.lake_id, scenario, progress)
        progress('Simulating {}: 2015–2099…'.format(SCENARIO_LABELS[scenario]))
        future = simulate(lake, future_inputs, options, restart=baseline.final_state)
        daily = pd.concat([context, baseline.daily, future.daily], ignore_index=True)
        daily.attrs.update(scenario=scenario, forcing_model='GFDL-ESM4', calendar='365_day',
            state_timing='States at the start of the labeled day; fluxes cover the day.')
        settings['scenario'] = scenario
        simulation = Simulation(lake, options, daily, future.final_state, '1950 initial state with 45-year warm-up')
        result = ExperimentResult(simulation, scenario, settings, key)
        self._remember(self.result_cache, key, result, maximum=3)
        return result
