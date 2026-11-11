# Verification scope

- `input_export_summary.json`: all 9,625 input cases passed full daily validation and lossless readback. The release manifest records input and bundle hashes.
- `model_summary.json`, `model_case_checks.json`: 60 numerical comparisons for 12 representative lakes, historical 1950–2014 and four SSPs 2015–2099; all passed. These use the same physics and daily integration source bundled here.
- `model_module_checks.json`: snow-off, sediment-off and customization smoke checks passed.
- `dashboard_wrapper_summary.json`, `dashboard_wrapper_checks.json`: six additional comparisons for Riley and the shallowest/deepest catalogue lakes passed, covering the new setup, warm-up and SSP2-4.5 wrapper. Complete annual metrics also passed. `preview_check.py` reproduces these checks on MSI.

The new annual definition averages all ice-free days, replacing the old manuscript analysis's fixed month filter intentionally. Calendar and seasonal-coordinate edge cases are checked separately. Source physics, integration and vertical-profile reconstruction remain unchanged.

No observations are bundled in this interface. Numerical reproduction of production runs is distinct from validation against measured lake conditions.
