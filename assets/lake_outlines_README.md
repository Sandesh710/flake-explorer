# Lake outlines for the interactive map

The outlines were supplied by the project author from the Minnesota DNR lake-browser workflow. Lake IDs match the model catalogue directly; no nearest-lake assignment is used.

`lake_outlines.zip` contains 1,920 individual GeoJSON features and a small index. Keep this file compressed. The notebook reads only the selected feature and needs no GeoPandas or Shapely installation.

Coordinates retain their original detail in EPSG:4326; no simplification or coordinate rounding was applied. Lory (30009600) had a self-intersecting ring repaired in this display copy with Shapely make_valid. The source shapefile and all simulation parameters are unchanged.

Five model basins have no matching outline: Jack the Horse North/South and Cross North East Bay/Main Basin/East Bay. Those selections retain their recorded location marker and display an outline-unavailable note.

The star uses the catalogue location where it falls inside the lake; otherwise it uses an interior representative point for display. These display points do not replace model coordinates. The map fits the full lake extent with room around it. Audit details are in verification/lake_outline_report.json.
