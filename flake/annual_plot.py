"""A compact annual-response figure, with a matched-experiment baseline."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from .plotting import STYLE, _axis, BLUE, RED
from .indicators import METRICS, baseline_statistics, relative_to_baseline
from .experiments import SCENARIO_LABELS
from .trends import sen_slope


def annual_figure(result, annual, changes=False, trend_period=(2015, 2099)):
    stats = baseline_statistics(annual)
    d = relative_to_baseline(annual) if changes else annual
    titles = ['Open-water mean mixed-layer temperature', 'Open-water duration', 'Ice-on date', 'Ice-off date']
    reference = mdates.date2num(pd.Timestamp('2001-07-01'))
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(2, 2, figsize=(14, 7.8), sharex=True, constrained_layout=True)
        for i, (ax, key, title) in enumerate(zip(axes.flat, METRICS, titles)):
            y = d[key].to_numpy(float)
            if i >= 2 and not changes:
                y = y + reference
                ax.yaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
                ax.yaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=6))
            ax.plot(d.year, y, color=RED if i == 0 else BLUE, lw=1.4, alpha=.95)
            for label, first, last, color in [('Baseline',1995,2014,'#e9edf0'),
                    ('Near',2020,2040,'#e2efe6'), ('Mid',2050,2070,'#fff0d8'), ('End',2080,2099,'#f7e1de')]:
                ax.axvspan(first-.5, last+.5, color=color, zorder=-2)
                if i < 2:
                    ax.text((first+last)/2, .975, label, transform=ax.get_xaxis_transform(),
                        ha='center', va='top', fontsize=9, color='#475662', clip_on=True)
            if changes:
                ax.axhline(0, color='#687783', lw=.9, ls='--')
            elif stats[key]['mean'] is not None:
                base = stats[key]['mean'] + (reference if i >= 2 else 0)
                ax.axhline(base, color='#687783', lw=.9, ls='--')
            ax.set_title('({}) {}'.format(chr(97+i), title), loc='center', fontsize=14, pad=10)
            ax.set_ylabel(('Change (°C)' if i == 0 else 'Change (days)') if changes else ('Temperature (°C)' if i == 0 else ('Days per year' if i == 1 else 'Date')))
            ax.set_xlim(1995, 2099)
            ax.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
            ax.grid(axis='y', color='#e7eaed', lw=.6)
            slope = sen_slope(d.year, d[key], *trend_period)
            unit = '°C decade⁻¹' if i == 0 else 'days decade⁻¹'
            annotation = "Sen’s slope: {:+.2f} {}".format(slope, unit) if slope is not None else 'Sen’s slope: undefined'
            ax.text(.025, .035, annotation, transform=ax.transAxes,
                ha='left', va='bottom', fontsize=10, bbox=dict(fc='white', ec='none', alpha=.9))
            if np.isfinite(y).sum() == 0:
                ax.text(.5, .5, 'No defined values', transform=ax.transAxes, ha='center', color='#555')
            _axis(ax)
        axes[1, 0].set_xlabel('Winter-ending year'); axes[1, 1].set_xlabel('Winter-ending year')
        for ax in axes[0]:
            ax.set_xlabel('Calendar year'); ax.tick_params(labelbottom=True)
        fig.suptitle('{} | {}{}'.format(result.simulation.lake.name, SCENARIO_LABELS[result.scenario],
            ' | Change from 1995–2014' if changes else ''), fontsize=18, fontweight='bold')
    return fig
