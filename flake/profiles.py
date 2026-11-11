"""Reconstruct vertical temperature from FLake's bulk state variables.

The thermocline polynomial is Eq. (55) of Mironov (2008), COSMO Technical
Report 11. It is a visualization of the modeled bulk profile, not a separate
vertically discretized heat solver.
"""
import numpy as np
import pandas as pd


def thermocline_shape(zeta, shape_factor):
    """Dimensionless profile; endpoints 0/1 and integral equal to C_T."""
    z=np.asarray(zeta,dtype=float)
    c=np.asarray(shape_factor,dtype=float)
    if not np.isfinite(z).all() or not np.isfinite(c).all():raise ValueError('Profile inputs must be finite.')
    if (z<0).any() or (z>1).any() or (c<.5-1e-9).any() or (c>.8+1e-9).any():
        raise ValueError('Use normalized depth 0–1 and shape factor 0.5–0.8.')
    return ((40*c-20)/3)*z+(18-30*c)*z**2+(20*c-12)*z**3+((5-10*c)/3)*z**4


def temperature_profiles(simulation, frame=None, levels=151):
    """Return physical depths and a depth × time temperature array in °C."""
    if levels<3:raise ValueError('Use at least three display depth levels.')
    d=simulation.daily if frame is None else frame
    depth=simulation.lake.mean_depth_m
    z=np.linspace(0,depth,levels)
    h=d.mixed_layer_depth_m.to_numpy(float)
    top=d.mixed_layer_temperature_c.to_numpy(float)
    bottom=d.bottom_temperature_c.to_numpy(float)
    c=d.thermocline_shape_factor.to_numpy(float)
    if ((h<0)|(h>depth+1e-8)).any():raise ValueError('Mixed-layer depth is outside the modeled column.')
    tc=np.maximum(depth-h,1e-12)
    xi=np.clip((z[:,None]-h[None,:])/tc[None,:],0,1)
    shape=thermocline_shape(xi,c[None,:])
    # Mironov (2008), Section 3.4.3: the cold, under-ice conductive
    # profile uses a linear thermocline. Open-water profiles are unchanged.
    cold_ice=(d.ice_thickness_m.to_numpy(float)>=.01)&(bottom<3.98)
    shape[:,cold_ice]=xi[:,cold_ice]
    profile=top[None,:]-(top-bottom)[None,:]*shape
    profile[:,h>=depth-1e-10]=top[h>=depth-1e-10]
    return z,profile


def open_water_season(simulation, year):
    """Longest continuous ice-free interval in a selected calendar year."""
    d=simulation.daily
    dates=pd.to_datetime(d.date)
    y=d.loc[dates.dt.year==int(year)].copy().reset_index(drop=True)
    if y.empty:raise ValueError('Selected year is outside the simulation dates.')
    free=y.ice_thickness_m<.01
    group=free.ne(free.shift()).cumsum()
    lengths=group[free].value_counts()
    if lengths.empty:raise ValueError('No ice-free interval in this year.')
    return y.loc[group.eq(lengths.index[0])].copy()
