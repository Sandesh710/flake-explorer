"""Annual open-water metrics and persistent winter ice dates on a noleap calendar."""
import numpy as np
import pandas as pd

METRICS = ['open_water_temperature_c', 'open_water_days', 'ice_on_season_day', 'ice_off_season_day']


def noleap_dates(start, end):
    d = pd.date_range(start, end)
    return d[~((d.month == 2) & (d.day == 29))]


def true_runs(mask):
    edges = np.diff(np.r_[False, np.asarray(mask, dtype=bool), False].astype(int))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def annual_indicators(daily, first_year=1995, last_year=2099):
    """Year = calendar year for water metrics and winter-ending year for ice dates.

    Season day is the zero-based day since preceding July 1, with February 29
    excluded. Both ice events therefore stay on a continuous seasonal axis.
    """
    indexed = daily.set_index('date')
    if indexed.index.has_duplicates:
        raise ValueError('Duplicate simulation dates.')
    output = []
    for year in range(first_year, last_year + 1):
        row = {'year': year, **{k: np.nan for k in METRICS}, 'ice_on_date': pd.NaT,
            'ice_off_date': pd.NaT, 'winter_status': 'incomplete_winter'}
        expected = noleap_dates('{}-01-01'.format(year), '{}-12-31'.format(year))
        annual = indexed.reindex(expected)
        required = annual[['ice_thickness_m', 'mixed_layer_temperature_c']]
        if required.notna().all().all() and np.isfinite(required.to_numpy(float)).all():
            free = annual.ice_thickness_m < .01
            row['open_water_days'] = int(free.sum())
            row['open_water_temperature_c'] = float(annual.loc[free, 'mixed_layer_temperature_c'].mean()) if free.any() else np.nan
        winter_dates = noleap_dates('{}-07-01'.format(year - 1), '{}-06-30'.format(year))
        cover = indexed.ice_thickness_m.reindex(winter_dates)
        if cover.notna().all() and np.isfinite(cover.to_numpy(float)).all():
            ice = cover.to_numpy(float) >= .01
            persistent = [(a, b) for a, b in true_runs(ice) if b - a >= 3]
            if not persistent:
                row['winter_status'] = 'no_persistent_ice'
            else:
                onset, last_end = persistent[0][0], persistent[-1][1]
                # A run ending at b covers [a,b); first breakup day can be b.
                breaks = [(a, b) for a, b in true_runs(~ice) if a >= last_end and b - a >= 3]
                row.update(ice_on_date=winter_dates[onset], ice_on_season_day=float(onset),
                           winter_status='persistent_ice_no_breakup')
                if breaks:
                    off = breaks[0][0]
                    row.update(ice_off_date=winter_dates[off], ice_off_season_day=float(off), winter_status='complete_ice_season')
        output.append(row)
    return pd.DataFrame(output)


def baseline_statistics(annual):
    baseline = annual.loc[annual.year.between(1995, 2014)]
    return {k: {'mean': float(baseline[k].mean()) if baseline[k].notna().any() else None,
                'valid_years': int(baseline[k].notna().sum())} for k in METRICS}


def relative_to_baseline(annual):
    stats = baseline_statistics(annual)
    output = annual.copy()
    for key in METRICS:
        mean = stats[key]['mean']
        output[key] = output[key] - mean if mean is not None else np.nan
    return output
