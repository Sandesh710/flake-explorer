"""Shared depth colors and lake-area symbol classes for both location maps."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, to_hex

# Narrower shallow/deep intervals show the actual distribution without clipping
# rare deep lakes. Every color corresponds to the labeled depth band.
DEPTH_BOUNDS = np.array([0., 1., 2., 3., 5., 8., 12., 20., 60.])
DEPTH_CMAP = plt.get_cmap('viridis', len(DEPTH_BOUNDS)-1)
DEPTH_NORM = BoundaryNorm(DEPTH_BOUNDS, DEPTH_CMAP.N, clip=True)
AREA_BREAKS = np.array([.5, 2., 10.])
AREA_LABELS = ['≤0.5', '0.5–2', '2–10', '>10']
AREA_SIZES = np.array([8., 17., 32., 56.])  # Matplotlib marker area, points².
AREA_RADII = np.array([2.2, 3.2, 4.4, 5.8])  # Leaflet marker radius, CSS px.


def area_class(area):
    return np.searchsorted(AREA_BREAKS, np.asarray(area, dtype=float), side='left')


def symbol_sizes(area):
    return AREA_SIZES[area_class(area)]


def point_style(feature):
    p = feature['properties']
    return {'fillColor': to_hex(DEPTH_CMAP(DEPTH_NORM(float(p['depth'])))),
            'color': '#233841', 'weight': .3, 'fillOpacity': .9,
            'radius': float(AREA_RADII[area_class(p['area'])])}


def legend_html():
    depths = []
    for left, right in zip(DEPTH_BOUNDS[:-1], DEPTH_BOUNDS[1:]):
        color = to_hex(DEPTH_CMAP(DEPTH_NORM((left+right)/2)))
        depths.append('<span style="display:inline-flex;align-items:center;gap:4px;margin:3px 9px 3px 0"><i style="display:inline-block;width:12px;height:12px;background:{};border:1px solid #465760"></i>{:g}–{:g}</span>'.format(color, left, right))
    areas = []
    for radius, label in zip(AREA_RADII, AREA_LABELS):
        diameter = radius*2
        areas.append('<span style="display:inline-flex;align-items:center;gap:5px;margin:3px 14px 3px 0"><i style="display:inline-block;border-radius:50%;width:{:.1f}px;height:{:.1f}px;background:#6a7f89;border:1px solid white"></i>{}</span>'.format(diameter, diameter, label))
    return '<div style="font:12px Arial;color:#20333f;line-height:1.4;padding:6px 0"><b>Mean depth (m)</b><br>'+''.join(depths)+'<br><b>Lake area (km²)</b><br>'+''.join(areas)+'</div>'


def depth_legend_html():
    colors = [to_hex(DEPTH_CMAP(i)) for i in range(DEPTH_CMAP.N)]
    cells = ''.join('<div style="height:20px;background:{}"></div>'.format(color) for color in reversed(colors))
    ticks = ''.join('<span style="position:absolute;left:24px;top:{}px;transform:translateY(-50%)">{:g}</span>'.format(i*20, value)
                    for i, value in enumerate(reversed(DEPTH_BOUNDS)))
    return '<div style="background:white;padding:9px 10px 12px;border-radius:4px;font:11px Arial;color:#20333f"><b>Mean depth<br>(m)</b><div style="position:relative;width:58px;height:160px;margin-top:12px"><div style="width:16px;border:1px solid #526771">'+cells+'</div>'+ticks+'</div></div>'


def area_legend_html():
    rows = []
    for radius, label in zip(AREA_RADII, AREA_LABELS):
        diameter = radius*2
        rows.append('<div style="display:flex;align-items:center;gap:6px;height:19px"><span style="width:17px;text-align:center"><i style="display:inline-block;border-radius:50%;width:{:.1f}px;height:{:.1f}px;background:#687e8b;border:1px solid #233841"></i></span><span>{}</span></div>'.format(diameter, diameter, label))
    return '<div style="background:white;padding:8px 10px;margin-bottom:40px;border-radius:4px;font:11px Arial;color:#20333f"><b>Lake area (km²)</b>'+''.join(rows)+'</div>'
