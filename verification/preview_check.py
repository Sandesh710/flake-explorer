"""Check the new experiment wrapper on MSI and prepare a small Colab preview."""
from pathlib import Path
import io
import json
import shutil
import zipfile
import numpy as np
import pandas as pd
from flake.data_access import InputStore, sha256
from flake.experiments import ExperimentRunner, lake_from_row, default_options, default_initial
from flake.indicators import annual_indicators

EXPECTED_EXPORT = '2b7ad9b6e0fbbdf6c57468f6921b601c4793e3d0a0e3fe5367c07d82a595270f'
COLUMNS = {'Tm':'mean_water_temperature_c', 'T_wML':'mixed_layer_temperature_c', 'Tb':'bottom_temperature_c',
    'h_ML':'mixed_layer_depth_m', 'C_T':'thermocline_shape_factor', 'H_ice':'ice_thickness_m',
    'H_snow':'snow_thickness_m', 'T_ice':'ice_temperature_c', 'T_snow':'snow_temperature_c',
    'H_B1':'sediment_layer_m', 'T_B1':'sediment_temperature_c', 'Ts':'surface_temperature_c', 'Qbot':'bottom_heat_w_m2'}


def find_export(base, explicit=None):
    folders = [Path(explicit)] if explicit else sorted(Path(base).glob('Century_Export_*'), reverse=True)
    for folder in folders:
        manifest = folder / 'catalogue/data_manifest.json'
        if manifest.is_file() and sha256(manifest) == EXPECTED_EXPORT:
            return folder
    raise FileNotFoundError('Set EXPORT_DIRECTORY to the passing Century_Export_... folder.')


def verify_preview(root, export, output):
    root, export, output = Path(root), Path(export), Path(output)
    store = InputStore(root, export, cache=output / 'cache')
    cat = store.catalogue
    ids = list(dict.fromkeys(['10000200', str(cat.loc[cat.depth_w.idxmin(), 'DOWLKNUM']), str(cat.loc[cat.depth_w.idxmax(), 'DOWLKNUM'])]))
    checks, errors = [], []
    runner = ExperimentRunner(store)
    source_checks = json.loads((export / 'reports/case_checks.json').read_text())
    source_lookup = {(r['lake_id'], r['scenario']): r for r in source_checks}
    summary = {'status': 'RUNNING', 'selected_lakes': ids, 'scope': 'New setup, warm-up, annual-indicator and scenario wrapper; three-lake representative check.',
               'physics_changed': False, 'github_upload_performed': False, 'originals_modified': False}
    try:
        for key in ids:
            row = cat.loc[cat.DOWLKNUM.eq(key)].iloc[0].to_dict()
            print('Checking dashboard defaults:', key, row['LAKE_NAME'], flush=True)
            result = runner.run(lake_from_row(row), default_options(row), default_initial(row), 'ssp245', print)
            if result.settings['initialization_mode'] != 'production_defaults':
                raise ValueError('Default setup did not preserve production initialization.')
            for scenario, start, end in [('historical', '1995-01-01', '2014-12-31'), ('ssp245', '2015-01-01', '2099-12-31')]:
                record = source_lookup[(key, scenario)]
                if sha256(record['source_path']) != record['source_sha256']:
                    raise ValueError('Production reference changed since export.')
                reference = pd.read_csv(record['source_path'], usecols=['Date'] + list(COLUMNS), parse_dates=['Date'], float_precision='round_trip')
                ref = reference.loc[reference.Date.between(start, end)].reset_index(drop=True)
                actual = result.display_daily.loc[lambda d: d.date.between(start, end)].reset_index(drop=True)
                if not np.array_equal(actual.date.to_numpy(), ref.Date.to_numpy()):
                    raise ValueError('Dashboard dates differ from production.')
                variables = {}
                for old, new in COLUMNS.items():
                    delta = float(np.max(np.abs(actual[new].to_numpy() - ref[old].to_numpy())))
                    tolerance = 2e-8 if old in ['H_ice', 'H_snow', 'C_T'] else (2e-6 if old == 'Qbot' else 2e-7)
                    variables[old] = {'max_absolute_difference': delta, 'tolerance': tolerance, 'pass': bool(np.isfinite(delta) and delta <= tolerance)}
                same_ice = bool(np.array_equal(actual.ice_thickness_m.ge(.01), ref.H_ice.ge(.01)))
                passed = all(v['pass'] for v in variables.values()) and same_ice
                checks.append({'lake_id': key, 'scenario': scenario, 'rows': len(actual), 'status': 'PASS' if passed else 'REVIEW',
                    'variables': variables, 'ice_classification_identical': same_ice})
                print('  {}: {}'.format(scenario, checks[-1]['status']), flush=True)
            annual = annual_indicators(result.simulation.daily)
            if len(annual) != 105 or annual.winter_status.eq('incomplete_winter').any() or annual.open_water_days.isna().any():
                raise ValueError('Annual metrics lack complete calendar years or first-winter context.')
            for year, group in result.display_daily.groupby(result.display_daily.date.dt.year):
                a = annual.loc[annual.year.eq(year)].iloc[0]
                free = group.ice_thickness_m.lt(.01)
                if a.open_water_days != int(free.sum()):
                    raise ValueError('Open-water count mismatch.')
                expected = float(group.loc[free, 'mixed_layer_temperature_c'].mean()) if free.any() else np.nan
                if not (np.isnan(expected) and pd.isna(a.open_water_temperature_c)) and abs(a.open_water_temperature_c - expected) > 1e-12:
                    raise ValueError('Open-water TML mismatch.')
            annual.to_csv(output / ('annual_' + key + '.csv'), index=False, float_format='%.17g')
        success = len(checks) == len(ids) * 2 and all(c['status'] == 'PASS' for c in checks)
        summary.update(status='PASS_DASHBOARD_WRAPPER' if success else 'REVIEW', cases_passed=sum(c['status'] == 'PASS' for c in checks),
            cases_expected=len(ids) * 2, full_input_lakes=1925, annual_calendar_checked=True)
    except Exception as exc:
        summary['status'] = 'REVIEW'; errors.append(type(exc).__name__ + ': ' + str(exc))
    for name, value in [('summary.json', summary), ('checks.json', checks), ('errors.json', errors)]:
        (output / name).write_text(json.dumps(value, indent=2, allow_nan=False))
    report = output / 'DASHBOARD_PREVIEW_REPORTS.zip'
    with zipfile.ZipFile(report, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output.glob('*.json')):
            archive.write(path, path.name)
        for path in sorted(output.glob('annual_*.csv')):
            archive.write(path, path.name)
    print('STATUS:', summary['status'], flush=True)
    print('SEND REPORT:', report, flush=True)
    return summary


def prepare_colab_preview(root, export, output, ids):
    """Pack three real lakes' full inputs for testing Colab before a public release."""
    root, export, output = Path(root), Path(export), Path(output)
    manifest = json.loads((root / 'data/data_manifest.json').read_text())
    destination = output / 'FLake_Century_Colab_Preview.zip'
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            archive.write(path, str(Path('flake-python') / path.relative_to(root)))
        archive.writestr('flake-python/preview_lakes.json', json.dumps(ids))
        archive.write(export / 'catalogue/data_manifest.json', 'flake-python/preview_inputs/catalogue/data_manifest.json')
        for record in manifest['records']:
            if record['lake_id'] not in ids:
                continue
            source = export / record['member']
            if sha256(source) != record['npz_sha256']:
                raise ValueError('Preview input hash mismatch.')
            archive.write(source, str(Path('flake-python/preview_inputs') / record['member']))
    print('COLAB PREVIEW:', destination, '({:.1f} MiB)'.format(destination.stat().st_size / 1024**2), flush=True)
    return destination
