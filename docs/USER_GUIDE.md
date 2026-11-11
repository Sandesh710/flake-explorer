# Using the Python FLake model

Open `Run_FLake.ipynb`, run setup, then launch the dashboard. A standard Colab CPU runtime is sufficient. The initial download is usually longer than the model calculation. Inputs and results are cached only within the current session unless you save them separately.

## Lake selection and properties

Search by lake name, county or eight-digit ID. Click a point on the map to select that lake; selection reloads its physical defaults and highlights its location. The overview button returns to Minnesota. The interactive background uses bundled state boundaries and makes no requests to raster tile servers. Point locations are from the catalogue; they are not lake outlines or bathymetric maps. Colors show mean depth, and point size follows lake area.

| Symbol | Quantity | Unit |
|---|---|---|
| D | Mean column depth, not maximum lake depth | m |
| F | Wind fetch | m |
| A | Surface area | km² |
| κd | Light extinction | m⁻¹ |
| Rs | Snow-retention factor | dimensionless, 0–1 |

The default optical mode uses the supplied daily series. Selecting constant κd replaces that series for the entire experiment, including warm-up. A constant value is not inferred silently from a lake's climatology.

Automatic snow retention uses the final Minnesota relationship, with A in km²:

$$R_s(A)=0.10+0.90\exp\left[-(A/0.5104)^{0.2116}\right].$$

Changing area updates this factor. Manual mode lets you set it independently. Retention changes modeled snow accumulation and the resulting snow depth. It is applied exactly once to the raw snowfall input. The model does not explicitly resolve spatial snow redistribution.

## Initial conditions and components

Expand **Initial conditions** to set the mixed-layer and bottom-water temperatures independently, mixed-layer depth, thermocline shape, surface-cover thicknesses and temperatures, and active sediment state. All values apply before the step for 1 January 1950. The production defaults include the original adjustment of the initial bottom-water temperature near the freshwater density maximum (approximately 3.98 °C).

The bulk water temperature is derived consistently from the selected layer states. Initial mixed-layer depth must be between zero and the configured mean depth; the shape factor is 0.5–0.8. Snow requires ice. Cover temperatures cannot exceed 0 °C. Invalid values are reported before integration.

**Snow cover off** prevents snow accumulation but keeps ice physics active. **Sediment heat exchange off** disables bottom-sediment heat exchange. The initial active sediment state HB1,0 / TB1,0 is distinct from the prescribed lower-boundary depth/temperature Dbs / Tbs.

Surface exchange and albedo controls are optional. Defaults use 10 m wind, 2 m air temperature/humidity and 100,000 Pa air pressure. The density range 100–400 kg m⁻³ and density coefficient 2000 remain those of the verified configuration. The daily timestep is fixed; no unsupported subdaily option is offered.

## Annual results

Water metrics use complete 365-day calendar years. Temperature averages every modeled ice-free day, including qualifying days outside March–October. An entirely covered year has zero open-water days and undefined open-water mean temperature.

Ice dates refer to complete July–June winters ending in the displayed year. Ice-on is the first day of the first run of at least three days with ice ≥1 cm. Ice-off is the first day of a run of at least three below-threshold days after the last persistent ice run. Winters without persistent ice have no ice-event dates. A winter with no completed breakup retains an undefined ice-off date.

Both dates are stored as actual dates and as noleap days since the preceding July 1. Changes from baseline use this continuous coordinate rather than a wrapped calendar day-of-year. Baseline means use valid values from 1995–2014 for the **same lake and experiment settings**, and the experiment download retains valid-year counts. Winter 1994–1995 is supported by the warm-up context. Winter 2099–2100 is not offered.

## Figures and download

The thermal view shows the longest continuous open-water interval in the chosen year. This is a display choice; annual duration includes all ice-free days. The temperature section uses the preserved FLake profile reconstruction and a thin mixed-layer overlay.

The winter view uses snow above the interface and ice extending downward, cropped around the modeled cover season. Year selectors redraw without recalculating the model.

**Download results** includes daily output for 1995–2099, annual indicators, a JSON record of the experiment and data identity, and the selected figures as PNG and PDF. The preceding 1994 winter context is included separately so the first winter’s indicators can be reconstructed. State columns describe the start of each labeled day; fluxes describe that day's integration step. Changing scientific controls marks previous results as out of date and disables downloading until a new run completes.

## Other lakes and meteorology

The Python model can accept other lakes. Instantiate `Lake`, `ModelOptions` and `InitialConditions`, create a pandas DataFrame with the required daily columns, and call `simulate`. Use `flake/inputs.py` for the column names and validation. Native longwave removes the need for cloud fraction. Supply raw, already-partitioned snowfall; do not multiply it by retention before calling this runner.

The bundled catalogue and area-retention relation are specific to the Minnesota application. Another region needs appropriate lake properties and snow settings. The notebook is an experiment interface; it does not imply that altered settings are calibrated or independently validated.

## Trend annotations

Annual figures show Sen’s slope over 2015–2099 as the median of all valid pairwise annual slopes, scaled to one decade: °C per decade for open-water mean mixed-layer temperature and days per decade for open-water duration and the two ice dates. Missing events are omitted, never replaced by zeros. Ice-date slopes use the continuous seasonal coordinate. Shading marks 2020–2040, 2050–2070 and 2080–2099. The same slopes are recorded in the experiment download.
