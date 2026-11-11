# Attribution and data sources

FLake was developed by Dmitrii Mironov and collaborators at the German Weather Service (DWD). The Python physics source retains the original code-owner notices for DWD, Dmitrii Mironov and Ulrich Schaettler, together with the original section histories and references. The module name has been simplified; the physics expressions remain those of the supplied Python implementation.

Primary model reference: Mironov, D. V. (2008). *Parameterization of Lakes in Numerical Weather Prediction. Description of a Lake Model.* COSMO Technical Report No. 11. DOI: 10.5676/DWD_pub/nwv/cosmo-tr_11.

The notebook, configuration interface, examples and plotting workflow form the accompanying Python guide. They do not imply endorsement by DWD. Original third-party notices are preserved. No blanket license is assigned to inherited material; confirm upstream reuse terms before the public repository release.

The example lake properties and optical parameters follow the Minnesota companion study. Meteorological origin: NEX-GDDP-CMIP6, GFDL-ESM4 historical and SSP1-2.6, SSP2-4.5, SSP3-7.0 and SSP5-8.5. Displayed historical coverage is 1995–2014; future coverage is 2015–2099. Historical forcing from 1950 is retained for warm-up. Example snow-retention assignments are specific to the Minnesota regional application.

Map boundaries: U.S. Census Bureau, 2024 cartographic state boundaries at 1:20 million, subset to Minnesota and neighboring states. Source: https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_20m.zip

Companion manuscript: Dahal, S., Ebtehaj, A., Olmanson, L., and Hondzo, M. *Projected Changes in Thermal Structure and Ice Phenology of Lakes in the Midwestern United States Over the Next Century.* Publication year, journal and DOI are not asserted here.

Meteorological dataset reference: Thrasher, B., Wang, W., Michaelis, A., Melton, F., Lee, T., and Nemani, R. (2022). *NASA Global Daily Downscaled Projections, CMIP6.* Scientific Data, 9, 262. https://doi.org/10.1038/s41597-022-01393-4. Dataset DOI: https://doi.org/10.7917/OFSG3345. Project information: https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/.
