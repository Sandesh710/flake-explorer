"""Sen slopes of annual indicators, expressed per decade."""
import numpy as np
from .indicators import METRICS


def sen_slope(years, values, first_year=2015, last_year=2099):
    """Median of all valid pairwise slopes; omitted ice events stay omitted."""
    x = np.asarray(years, dtype=float)
    y = np.asarray(values, dtype=float)
    keep = np.isfinite(x) & np.isfinite(y) & (x >= first_year) & (x <= last_year)
    x, y = x[keep], y[keep]
    if len(x) < 2:
        return None
    if len(np.unique(x)) != len(x):
        raise ValueError('Sen slope requires unique annual years.')
    order = np.argsort(x); x, y = x[order], y[order]
    slopes = np.concatenate([(y[i+1:] - y[i]) / (x[i+1:] - x[i]) for i in range(len(x)-1)])
    return float(np.median(slopes) * 10.)


def trend_statistics(annual, first_year=2015, last_year=2099):
    return {key: {'sen_slope_per_decade': sen_slope(annual.year, annual[key], first_year, last_year),
                 'units': 'degC per decade' if key == METRICS[0] else 'days per decade',
                 'period': [first_year, last_year],
                 'valid_years': int((annual.year.between(first_year, last_year) & annual[key].notna()).sum())}
            for key in METRICS}
