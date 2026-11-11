"""Lake properties, simulation options and initial conditions."""
from dataclasses import dataclass
from typing import Optional
import math


@dataclass(frozen=True)
class Lake:
    """A single FLake water column. Depth and fetch are in meters."""
    name: str
    mean_depth_m: float
    fetch_m: float
    latitude: float
    longitude: float = 0.0
    area_km2: float = 1.0
    snow_retention: float = 1.0
    lake_id: str = "custom"
    county: str = ""
    coriolis_s_inv: Optional[float] = None

    def validate(self):
        values = [self.mean_depth_m, self.fetch_m, self.latitude, self.longitude,
                  self.area_km2, self.snow_retention]
        if not all(math.isfinite(float(v)) for v in values):
            raise ValueError("Lake properties must be finite numbers.")
        if self.mean_depth_m <= 0 or self.fetch_m <= 0 or self.area_km2 <= 0:
            raise ValueError("Depth, fetch and lake area must be positive.")
        if not -90 <= self.latitude <= 90 or not -180 <= self.longitude <= 180:
            raise ValueError("Latitude or longitude is outside its geographic range.")
        if not 0 <= self.snow_retention <= 1:
            raise ValueError("Snow retention must be between 0 and 1.")
        if self.coriolis_s_inv is not None and not math.isfinite(self.coriolis_s_inv):
            raise ValueError("Coriolis parameter must be finite.")


@dataclass(frozen=True)
class ModelOptions:
    """Switches and physical parameters supplied to FLake."""
    sediments: bool = True
    snow: bool = True
    sediment_depth_m: float = 5.0
    sediment_temperature_c: float = 6.0
    light_extinction_m_inv: Optional[float] = None
    dry_snow_albedo: float = 0.60
    melting_snow_albedo: float = 0.10
    white_ice_albedo: float = 0.60
    blue_ice_albedo: float = 0.10
    minimum_snow_conductivity: float = 0.30
    wind_height_m: float = 10.0
    temperature_humidity_height_m: float = 2.0
    air_pressure_pa: float = 100000.0

    def validate(self):
        for name in ['sediment_depth_m','wind_height_m','temperature_humidity_height_m','air_pressure_pa']:
            if not math.isfinite(getattr(self,name)) or getattr(self,name) <= 0:
                raise ValueError(name + " must be positive and finite.")
        if not math.isfinite(self.sediment_temperature_c) or not 0 <= self.sediment_temperature_c <= 40:
            raise ValueError("Sediment boundary temperature must be between 0 and 40 °C.")
        if self.light_extinction_m_inv is not None and (not math.isfinite(self.light_extinction_m_inv) or self.light_extinction_m_inv <= 0):
            raise ValueError("Light extinction must be positive and finite.")
        for a in [self.dry_snow_albedo,self.melting_snow_albedo,self.white_ice_albedo,self.blue_ice_albedo]:
            if not math.isfinite(a) or not 0 <= a <= 1:
                raise ValueError("Albedo must be between 0 and 1.")
        if self.dry_snow_albedo < self.melting_snow_albedo or self.white_ice_albedo < self.blue_ice_albedo:
            raise ValueError("Cold-surface albedo must be at least the melting-surface value.")
        if not math.isfinite(self.minimum_snow_conductivity) or not 0.01 <= self.minimum_snow_conductivity <= 1.5:
            raise ValueError("Minimum snow conductivity must be between 0.01 and 1.5 W m⁻¹ K⁻¹.")


@dataclass(frozen=True)
class InitialConditions:
    """Independent lake states at the start of January 1950, before warm-up."""
    mixed_layer_temperature_c: float = 4.0
    bottom_temperature_c: float = 3.98
    mixed_layer_depth_m: Optional[float] = None
    thermocline_shape_factor: float = 0.5
    ice_thickness_m: float = 0.0
    snow_thickness_m: float = 0.0
    ice_temperature_c: float = 0.0
    snow_temperature_c: float = 0.0
    sediment_layer_m: Optional[float] = None
    sediment_temperature_c: Optional[float] = None

    def state(self, lake, options):
        h = lake.mean_depth_m if self.mixed_layer_depth_m is None else self.mixed_layer_depth_m
        hb = options.sediment_depth_m if self.sediment_layer_m is None else self.sediment_layer_m
        tb = options.sediment_temperature_c if self.sediment_temperature_c is None else self.sediment_temperature_c
        v = [self.mixed_layer_temperature_c, self.bottom_temperature_c, h,
             self.thermocline_shape_factor, self.ice_thickness_m, self.snow_thickness_m,
             self.ice_temperature_c, self.snow_temperature_c, hb, tb]
        if not all(math.isfinite(float(x)) for x in v):
            raise ValueError("Initial conditions must be finite.")
        if not 0 <= self.mixed_layer_temperature_c <= 40 or not 0 <= self.bottom_temperature_c <= 40:
            raise ValueError("Initial water temperatures must be between 0 and 40 °C.")
        if not 0 <= h <= lake.mean_depth_m or not 0.5 <= self.thermocline_shape_factor <= 0.8:
            raise ValueError("Initial mixed-layer depth must lie within the lake; C_T must be 0.5–0.8.")
        if min(self.ice_thickness_m, self.snow_thickness_m, hb) < 0 or not 0 <= tb <= 40:
            raise ValueError("Initial thicknesses must be nonnegative and sediment temperature 0–40 °C.")
        if not -80 <= self.ice_temperature_c <= 0 or not -80 <= self.snow_temperature_c <= 0:
            raise ValueError("Initial snow and ice temperatures must be between −80 and 0 °C.")
        if self.snow_thickness_m > 0 and (self.ice_thickness_m == 0 or not options.snow):
            raise ValueError("Initial snow requires ice and an enabled snow module.")
        if self.ice_thickness_m > 0 and self.mixed_layer_temperature_c > 4:
            raise ValueError("Use water temperature at most 4 °C when starting with ice.")
        ice = self.ice_thickness_m
        top = self.mixed_layer_temperature_c
        bottom = self.bottom_temperature_c
        mean = top - self.thermocline_shape_factor*(1-h/lake.mean_depth_m)*(top-bottom)
        surface = self.snow_temperature_c if self.snow_thickness_m > 0 else (self.ice_temperature_c if ice > 0 else top)
        return {'T_snow_K':self.snow_temperature_c+273.15,'T_ice_K':self.ice_temperature_c+273.15,'T_mnw_K':mean+273.15,
                'T_wML_K':top+273.15,'T_bot_K':bottom+273.15,
                'T_B1_K':tb+273.15,'C_T':self.thermocline_shape_factor,
                'h_snow_m':self.snow_thickness_m,'h_ice_m':ice,'h_ML_m':h,
                'H_B1_m':hb,'T_sfc_K':surface+273.15}
