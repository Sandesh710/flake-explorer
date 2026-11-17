"""Period means and changes for the annual-response view."""
from html import escape
import numpy as np
import pandas as pd
from .indicators import METRICS
from .experiments import SCENARIO_LABELS

LABELS = ['Open-water mixed-layer temperature', 'Open-water duration', 'Ice-on date', 'Ice-off date']
SYMBOLS = ['⟨T<sub>ML</sub>⟩', 'D<sub>OW</sub>', 'd<sub>on</sub>', 'd<sub>off</sub>']


def response_statistics(annual):
    """Equal-weight annual means; undefined events remain omitted."""
    rows = {}
    for key in METRICS:
        groups = []
        for first, last in [(1995, 2014), (2015, 2099)]:
            values = annual.loc[annual.year.between(first, last), key].to_numpy(float)
            values = values[np.isfinite(values)]
            groups.append((float(np.mean(values)) if len(values) else None, len(values)))
        baseline, future = groups
        rows[key] = {'baseline_mean': baseline[0], 'future_mean': future[0],
                     'mean_change': future[0] - baseline[0] if future[0] is not None and baseline[0] is not None else None,
                     'baseline_valid_years': baseline[1], 'future_valid_years': future[1],
                     'change_units': 'degC' if key == METRICS[0] else 'days'}
    return rows


def mean_label(value, index):
    if value is None:
        return 'Undefined'
    if index >= 2:
        return (pd.Timestamp('2001-07-01') + pd.Timedelta(days=int(np.floor(value + .5)))).strftime('%b %d')
    return '{:.2f} °C'.format(value) if index == 0 else '{:.1f} days'.format(value)


def statistics_html(result, annual):
    stats = response_statistics(annual)
    head = ('<h3 style="margin:12px 0 8px">{} · {}</h3>'
            '<table style="border-collapse:collapse;width:100%;font-size:14px">'
            '<thead><tr><th style="text-align:left">Variable</th>'
            '<th>Mean · 1995–2014</th><th>Mean · 2015–2099</th>'
            '<th>Δ Mean</th></tr></thead><tbody>').format(
                escape(result.simulation.lake.name), escape(SCENARIO_LABELS[result.scenario]))
    body, notes = [], []
    for i, key in enumerate(METRICS):
        row = stats[key]
        delta = row['mean_change']
        change = 'Undefined' if delta is None else '{:+.2f} {}'.format(delta, '°C' if i == 0 else 'days')
        body.append('<tr style="border-top:1px solid #dce3e7">'
                    '<td style="padding:9px 6px"><b>{}</b> · {}</td>'
                    '<td style="text-align:center">{}</td><td style="text-align:center">{}</td>'
                    '<td style="text-align:center"><b>{}</b></td></tr>'.format(
                        SYMBOLS[i], LABELS[i], mean_label(row['baseline_mean'], i),
                        mean_label(row['future_mean'], i), change))
        if row['baseline_valid_years'] < 20 or row['future_valid_years'] < 85:
            notes.append('{}: {} baseline and {} future {} with defined values.'.format(
                LABELS[i], row['baseline_valid_years'], row['future_valid_years'], 'winters' if i >= 2 else 'years'))
    return head + ''.join(body) + '</tbody></table><p class="flake-small">Δ = future mean − baseline mean. Positive ice-date changes indicate later dates.</p>' + ''.join('<p class="flake-small">{}</p>'.format(escape(note)) for note in notes)

