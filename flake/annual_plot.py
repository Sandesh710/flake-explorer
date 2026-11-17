"""One annual indicator at a time, with Sen's slope as its only statistic."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from .plotting import STYLE, _axis, BLUE, RED
from .indicators import METRICS
from .experiments import SCENARIO_LABELS
from .trends import sen_slope

TITLES = ['Open-water mean mixed-layer temperature', 'Open-water duration', 'Ice-on date', 'Ice-off date']
Y_LABELS = [r'$\langle T_{\mathrm{ML}}\rangle$ (°C)', r'$D_{\mathrm{OW}}$ (days)', r'$d_{\mathrm{on}}$', r'$d_{\mathrm{off}}$']


def annual_figure(result, annual, metric=None, trend_period=(2015, 2099)):
    metric = METRICS[0] if metric is None else metric
    if metric not in METRICS:
        raise ValueError('Choose one of the four annual indicators.')
    i = METRICS.index(metric)
    y = annual[metric].to_numpy(float)
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(12, 4.8), constrained_layout=True)
        if i >= 2:
            y = y + mdates.date2num(pd.Timestamp('2001-07-01'))
            ax.yaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            ax.yaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=6))
        ax.plot(annual.year, y, color=RED if i == 0 else BLUE, lw=1.5)
        for label, first, last, color in [('Baseline',1995,2014,'#e9edf0'),
                ('Near',2020,2040,'#e2efe6'), ('Mid',2050,2070,'#fff0d8'), ('End',2080,2099,'#f7e1de')]:
            ax.axvspan(first-.5, last+.5, color=color, zorder=-2)
            ax.text((first+last)/2, .975, label, transform=ax.get_xaxis_transform(),
                    ha='center', va='top', fontsize=10, color='#475662')
        slope = sen_slope(annual.year, annual[metric], *trend_period)
        unit = '°C decade⁻¹' if i == 0 else 'days decade⁻¹'
        annotation = 'Sen’s slope: {:+.2f} {}'.format(slope, unit) if slope is not None else 'Sen’s slope: undefined'
        ax.text(.02, .04, annotation, transform=ax.transAxes, ha='left', va='bottom',
                fontsize=11, bbox=dict(boxstyle='square,pad=0.35', fc='white', ec='black', lw=.7, alpha=.95))
        if not np.isfinite(y).any():
            ax.text(.5, .5, 'No defined values', transform=ax.transAxes, ha='center')
        ax.set_title('{} | {}\n{}'.format(result.simulation.lake.name,
                    SCENARIO_LABELS[result.scenario], TITLES[i]), loc='center', pad=12)
        ax.set_ylabel(Y_LABELS[i])
        ax.set_xlabel('Winter-ending year' if i >= 2 else 'Calendar year')
        ax.set_xlim(1995, 2099)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=7, integer=True))
        ax.grid(axis='y', color='#e7eaed', lw=.6)
        _axis(ax)
    return fig

