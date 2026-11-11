"""Daily FLake integration with explicit configuration and state handoff.

Original FLake physics: DWD, Dmitrii Mironov and collaborators.
This module supplies daily inputs to the Python engine and records its outputs.
"""
from dataclasses import dataclass,asdict
from pathlib import Path
import importlib.util
import sys
import uuid
import numpy as np
import pandas as pd
from .configuration import Lake,ModelOptions,InitialConditions
from .inputs import validate_meteorology


@dataclass
class Simulation:
    lake: Lake
    options: ModelOptions
    daily: pd.DataFrame
    final_state: dict
    initialization: str


def _engine(options):
    # Each run owns an independent engine namespace; settings never leak to
    # another lake or to a later run with different module switches.
    name='flake_engine_'+uuid.uuid4().hex
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name('physics.py'))
    engine=importlib.util.module_from_spec(spec)
    sys.modules[name]=engine
    try:spec.loader.exec_module(engine)
    finally:sys.modules.pop(name,None)
    engine.lflk_botsed_use=bool(options.sediments)
    engine.flake_configure_snow_tuning(
        dry_snow_albedo=options.dry_snow_albedo,melting_snow_albedo=options.melting_snow_albedo,
        whiteice_albedo=options.white_ice_albedo,blueice_albedo=options.blue_ice_albedo,
        rho_snow_min=100.0,rho_snow_max=400.0,gamma_rho_snow=2000.0,
        kappa_snow_min=options.minimum_snow_conductivity,kappa_snow_max=1.5,gamma_kappa_snow=1.3)
    return engine


def simulate(lake, meteorology, options=None, initial_conditions=None, restart=None):
    """Run one daily lake column and return a Simulation.

    Use InitialConditions for a new experiment, or a full restart mapping for
    continuation. Snow off represents bare ice: initial snow must be zero and
    no new snow is supplied. Ice thermodynamics remain active in both modes.
    """
    options=options or ModelOptions()
    lake.validate();options.validate()
    data=validate_meteorology(meteorology,options)
    if initial_conditions is not None and restart is not None:
        raise ValueError('Choose either initial conditions or a restart, not both.')
    if restart is None:
        state=(initial_conditions or InitialConditions()).state(lake,options)
        initialization='Specified initial conditions'
    else:
        state=dict(restart)
        initialization='Historical restart'
    keys=['T_snow_K','T_ice_K','T_mnw_K','T_wML_K','T_bot_K','T_B1_K','C_T',
          'h_snow_m','h_ice_m','h_ML_m','H_B1_m','T_sfc_K']
    if set(keys)-set(state):raise ValueError('Restart is missing model state variables.')
    state={k:float(state[k]) for k in keys}
    if not all(np.isfinite(list(state.values()))):raise ValueError('Initial state must be finite.')
    if min(state[k] for k in ['h_snow_m','h_ice_m','h_ML_m','H_B1_m'])<0:
        raise ValueError('Initial thicknesses must be nonnegative.')
    if state['h_ML_m']>lake.mean_depth_m+1e-10:raise ValueError('Initial mixed layer exceeds lake depth.')
    if not options.snow and state['h_snow_m']>0:
        raise ValueError('Snow-off requires a new initial state without snow.')
    if not .5-1e-10<=state['C_T']<=.8+1e-10:raise ValueError('Thermocline shape factor must be within 0.5–0.8.')
    engine=_engine(options)
    coriolis=lake.coriolis_s_inv if lake.coriolis_s_inv is not None else 2*7.292115e-5*np.sin(np.deg2rad(lake.latitude))
    variables={'surface_temperature_c':'T_sfc_K','mean_water_temperature_c':'T_mnw_K',
        'mixed_layer_temperature_c':'T_wML_K','bottom_temperature_c':'T_bot_K',
        'mixed_layer_depth_m':'h_ML_m','thermocline_shape_factor':'C_T',
        'ice_thickness_m':'h_ice_m','snow_thickness_m':'h_snow_m',
        'ice_temperature_c':'T_ice_K','snow_temperature_c':'T_snow_K',
        'sediment_layer_m':'H_B1_m','sediment_temperature_c':'T_B1_K'}
    fluxes={'sensible_heat_w_m2':'Q_sensible_out','latent_heat_w_m2':'Q_latent_out',
            'outgoing_longwave_w_m2':'Q_lww_out','bottom_heat_w_m2':'Q_bot_out',
            'water_heat_w_m2':'Q_w_out','water_shortwave_w_m2':'I_w_out',
            'air_friction_velocity_m_s':'ufr_a_out','water_friction_velocity_m_s':'ufr_w_out',
            'convective_velocity_m_s':'Wconv_out','snow_albedo':'albedo_snow_out','ice_albedo':'albedo_ice_out'}
    arrays={name:np.zeros(len(data)) for name in list(variables)+list(fluxes)}
    current_kd=None;optic=None
    for k,row in enumerate(data.itertuples(index=False)):
        for name,key in variables.items():
            arrays[name][k]=state[key]-(273.15 if key.endswith('_K') else 0)
        # Match the runner's displayed surface-temperature convention under ice.
        if state['h_ice_m']>engine.h_Ice_min_flk:arrays['surface_temperature_c'][k]=0.0
        kd=float(row.light_extinction_m_inv)
        if kd!=current_kd:
            current_kd=kd
            frac,ext=engine.create_optic_arrays(nband=1,fractions=[1.0],extinctions=[kd])
            optic=engine.OpticparMedium(nband_optic=np.int32(1),frac_optic=frac,extincoef_optic=ext)
        snow_rate=lake.snow_retention*max(float(row.snowfall_kg_m2_s),0.0) if options.snow else 0.0
        output=engine.flake_interface(
            dMsnowdt_in=snow_rate,I_atm_in=row.shortwave_w_m2,Q_atm_lw_in=float(row.longwave_w_m2),
            height_u_in=options.wind_height_m,height_tq_in=options.temperature_humidity_height_m,
            U_a_in=max(row.wind_speed_m_s,.01),T_a_in=row.air_temperature_c+273.15,
            q_a_in=engine.SfcFlx_spechum(row.vapor_pressure_mb*100.0,options.air_pressure_pa),
            P_a_in=options.air_pressure_pa,depth_w=lake.mean_depth_m,fetch=lake.fetch_m,
            depth_bs=options.sediment_depth_m,T_bs=options.sediment_temperature_c+273.15,
            par_Coriolis=coriolis,del_time=86400.0,
            T_snow_in=state['T_snow_K'],T_ice_in=state['T_ice_K'],T_mnw_in=state['T_mnw_K'],
            T_wML_in=state['T_wML_K'],T_bot_in=state['T_bot_K'],T_B1_in=state['T_B1_K'],
            C_T_in=state['C_T'],h_snow_in=state['h_snow_m'],h_ice_in=state['h_ice_m'],
            h_ML_in=state['h_ML_m'],H_B1_in=state['H_B1_m'],T_sfc_p=state['T_sfc_K'],opticpar_water=optic)
        for name,key in fluxes.items():arrays[name][k]=output[key]
        state=dict(zip(keys,[output[k] for k in ['T_snow_out','T_ice_out','T_mnw_out','T_wML_out',
            'T_bot_out','T_B1_out','C_T_out','h_snow_out','h_ice_out','h_ML_out','H_B1_out','T_sfc_n']]))
    daily=pd.concat([data,pd.DataFrame(arrays)],axis=1)
    daily.attrs.update(lake=asdict(lake),options=asdict(options),initialization=initialization,
                       scenario=meteorology.attrs.get('scenario','custom'),forcing_model=meteorology.attrs.get('forcing_model','user supplied'),
                       state_timing='State columns are at the start of the labeled day; fluxes cover its integration step.')
    return Simulation(lake,options,daily,{k:float(v) for k,v in state.items()},initialization)
