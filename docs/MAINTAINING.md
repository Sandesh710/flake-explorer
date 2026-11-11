# Updating the repository and data release

## Review before replacing the public notebook

Use `MSI_Preview_FLake_Dashboard.ipynb` supplied with this update. It writes a fresh scratch folder, checks the new experiment wrapper against production, and prepares a small three-lake Colab preview. Review its `DASHBOARD_PREVIEW_REPORTS.zip` and try the controls in Colab before replacing the working public version.

The preview archive contains real inputs for Riley and the catalogue's shallowest/deepest lakes. It is intended for testing; the full release still contains all 1,925. No observation data are needed for this interface.

## Repository files

The code update ZIP contains a top-level `flake-explorer` folder. Upload its **contents with folders intact**, using the existing GitHub web editor workflow. The `flake`, `assets`, `data`, `docs` and `verification` directories must remain directories. Commit the update yourself with a message such as `Add century simulation dashboard`.

The small `data/lakes.csv` and `data/data_manifest.json` belong in the code repository. The manifest is the exact one reviewed after the MSI export. The 78 large ZIP bundles stay outside Git history.

Retain the previous release `data-v1.0.0` so the earlier tutorial remains recoverable. Outdated root duplicates (`build_summary.json`, `model_checks.json`, `model_code_sha256.json`) and old guide modules that are no longer referenced can be removed during cleanup. `flake/notebook.py` and `flake/observations.py` are not part of this new interface; preserve them in repository history if removing them from the current tree. Do not delete original research files on MSI.

## Full input release

Prepare a new data release with tag **data-v2.0.0**, title **GFDL-ESM4 inputs — 1,925 lakes, 1950–2099**. Initially keep it as a draft while uploading and checking the asset list. The 1950–1994 portion supports warm-up; displayed baseline and projections are 1995–2099.

Upload the **78 individual ZIPs** from the existing MSI export's `release_assets` directory. Do not upload the entire 7.19 GiB dataset as one ZIP and do not attach it to the release-notes text box. Use the release's binary-asset attachment area. If uploading directly from MSI, use a dedicated authenticated uploader in your own Jupyter session rather than sharing a token in chat or putting one in the repository.

The code downloads assets from:

`https://github.com/Sandesh710/flake-explorer/releases/download/data-v2.0.0/<asset filename>`

Every required filename, size and SHA-256 is in `data/data_manifest.json`. Do not rename the bundles. After all assets match the manifest, publish the data release. Publishing a release is separate from committing source code.

## Test the published version

Open the repository's Colab badge in a fresh runtime. Check that setup loads the updated code, a default lake/scenario run downloads only its required bundles, the map and search selection agree, parameter changes mark results as out of date, and year changes only redraw. Try a second SSP, snow off, sediment off, a constant κd and a changed depth, then inspect the downloaded experiment settings.

The public repository and release must be accessible to Colab. Authorizing the notebook viewer to GitHub does not automatically authenticate a Python runtime's `git clone` or data download.

## Editing later

Change display text/layout in `flake/dashboard.py`, annual definitions in `flake/indicators.py`, and figures in the plotting modules. Keep scientific definitions documented. Changes to the physical engine or integration arithmetic need their own numerical checks; shortening code is not a reason to change the physics.

Update the release manifest only when exporting a new, verified dataset. A manifest change changes the input-cache identity. Existing live Colab sessions keep their loaded Python code until reloaded or restarted; opening a fresh runtime is the clearest way to test a repository update.

Keep the original third-party source notices and appropriate model/data citations. No blanket license for inherited code is asserted by this update.
