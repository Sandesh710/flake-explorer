"""Export the experiment, annual indicators and the selected figures."""
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import hashlib
import json
import zipfile
from .indicators import baseline_statistics
from .trends import trend_statistics


def export_experiment(result, annual, figures, output_base, views=None):
    folder = Path(output_base) / ('FLake_{}_{}'.format(result.simulation.lake.lake_id, datetime.utcnow().strftime('%Y%m%dT%H%M%S_%fZ')))
    folder.mkdir(parents=True, exist_ok=False)
    result.display_daily.to_csv(folder / 'daily_simulation.csv', index=False, float_format='%.17g')
    context = result.simulation.daily.loc[result.simulation.daily.date < '1995-01-01']
    if not context.empty:
        context.to_csv(folder / 'winter_context_1994.csv', index=False, float_format='%.17g')
    annual.to_csv(folder / 'annual_indicators.csv', index=False, float_format='%.17g')
    settings = dict(result.settings, final_state=result.simulation.final_state, views=views or {}, timestep_seconds=86400,
        baseline_statistics=baseline_statistics(annual), model_version='2.0.0',
        sen_slopes=trend_statistics(annual),
        physics_sha256=hashlib.sha256(Path(__file__).with_name('physics.py').read_bytes()).hexdigest(),
        annual_definitions={'open_water_temperature': 'Mean T_ML over ALL days with h_ice < 0.01 m in the calendar year.',
            'open_water_days': 'Count of modeled days with h_ice < 0.01 m in the complete 365-day calendar year.',
            'ice_dates': 'First of three consecutive days at/above 0.01 m; breakup first persistent below-threshold run after the last persistent ice run, within the complete July–June winter.',
            'season_day': 'Zero-based noleap day since preceding July 1; ice metrics labeled by winter-ending year.',
            'state_timing': 'State variables at start of labeled day; fluxes cover its daily integration.'})
    (folder / 'experiment.json').write_text(json.dumps(settings, indent=2, allow_nan=False))
    for name, figure in figures.items():
        figure.savefig(folder / (name + '.png'), dpi=300, bbox_inches='tight', facecolor='white')
        figure.savefig(folder / (name + '.pdf'), bbox_inches='tight', facecolor='white')
    archive = folder.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as destination:
        for path in sorted(folder.iterdir()):
            destination.write(path, path.name)
    return archive
