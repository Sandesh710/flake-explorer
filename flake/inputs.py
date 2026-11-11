"""Validate daily weather supplied to the unchanged FLake integration."""
import numpy as np
import pandas as pd
REQUIRED_COLUMNS = ['date', 'shortwave_w_m2', 'longwave_w_m2', 'air_temperature_c', 'vapor_pressure_mb', 'wind_speed_m_s', 'snowfall_kg_m2_s', 'light_extinction_m_inv']

def validate_meteorology(frame, options):
    """Accept daily Gregorian or noleap data without inventing missing forcing."""
    d=frame.copy().reset_index(drop=True)
    needed=[c for c in REQUIRED_COLUMNS if not (c=='light_extinction_m_inv' and options.light_extinction_m_inv is not None)]
    missing=sorted(set(needed)-set(d))
    if missing:raise ValueError('Meteorology lacks columns: '+', '.join(missing))
    d['date']=pd.to_datetime(d.date,errors='raise')
    if d.empty or d.date.isna().any() or d.date.duplicated().any() or not d.date.is_monotonic_increasing:
        raise ValueError('Dates must be valid, unique and increasing.')
    if not d.date.eq(d.date.dt.normalize()).all():raise ValueError('Use daily dates without time-of-day.')
    calendar=pd.date_range(d.date.iloc[0],d.date.iloc[-1],freq='D')
    noleap=calendar[~((calendar.month==2)&(calendar.day==29))]
    if not (pd.DatetimeIndex(d.date).equals(calendar) or pd.DatetimeIndex(d.date).equals(noleap)):
        raise ValueError('Daily forcing has gaps other than omitted February 29 dates.')
    for c in needed:
        if c=='date':continue
        d[c]=pd.to_numeric(d[c],errors='raise')
        if not np.isfinite(d[c]).all():raise ValueError(c+' must contain finite values.')
    # Native incoming longwave is used; cloud cover is not a model input.
    d=d.drop(columns=['cloud_fraction'],errors='ignore')
    for c in ['shortwave_w_m2','longwave_w_m2','vapor_pressure_mb','wind_speed_m_s','snowfall_kg_m2_s']:
        if (d[c]<0).any():raise ValueError(c+' must be nonnegative.')
    if options.light_extinction_m_inv is not None:d['light_extinction_m_inv']=options.light_extinction_m_inv
    if (d.light_extinction_m_inv<=0).any():raise ValueError('Light extinction must be positive.')
    if not d.air_temperature_c.between(-100,65).all():raise ValueError('Check air-temperature units: expected °C.')
    return d
