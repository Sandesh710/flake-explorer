"""Read one lake's lossless inputs locally or from versioned release bundles."""
from pathlib import Path
import hashlib
import json
import tempfile
import zipfile
import urllib.request
import urllib.error
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RELEASE_URL = 'https://github.com/Sandesh710/flake-explorer/releases/download/data-v2.0.0'


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


class InputStore:
    def __init__(self, root=ROOT, local_export=None, cache=None):
        self.root = Path(root)
        self.manifest_path = self.root / 'data/data_manifest.json'
        self.identity = sha256(self.manifest_path)
        self.manifest = json.loads(self.manifest_path.read_text())
        self.records = {(r['lake_id'], r['scenario']): r for r in self.manifest['records']}
        self.bundles = {r['asset']: r for r in self.manifest['bundles']}
        if sha256(self.root / 'data/lakes.csv') != self.manifest['catalogue_sha256']:
            raise ValueError('Lake catalogue hash mismatch.')
        self.catalogue = pd.read_csv(self.root / 'data/lakes.csv', dtype={'DOWLKNUM': str}, float_precision='round_trip')
        self.local_export = Path(local_export) if local_export else None
        if self.local_export is not None and sha256(self.local_export / 'catalogue/data_manifest.json') != self.identity:
            raise ValueError('Local export differs from the reviewed input manifest.')
        self.cache = Path(cache) if cache else Path(tempfile.gettempdir()) / 'flake_inputs' / self.identity[:16]
        self.cache.mkdir(parents=True, exist_ok=True)

    def _download(self, asset, progress):
        expected = self.bundles[asset]
        path = self.cache / asset
        if path.is_file() and sha256(path) == expected['sha256']:
            return path
        progress('Downloading weather bundle ({:.0f} MiB)…'.format(expected['bytes'] / 1024**2))
        temporary = path.with_name(path.name + '.part')
        try:
            request = urllib.request.Request(RELEASE_URL + '/' + asset, headers={'User-Agent': 'FLake-Python/2.0'})
            with urllib.request.urlopen(request, timeout=120) as source, temporary.open('wb') as destination:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    destination.write(block)
            if temporary.stat().st_size != expected['bytes'] or sha256(temporary) != expected['sha256']:
                raise ValueError('Downloaded weather bundle failed its checksum. Please retry.')
            temporary.replace(path)
        except urllib.error.HTTPError as exc:
            raise RuntimeError('Weather bundle is unavailable (HTTP {}). The data-v2.0.0 release must contain {}. For the MSI preview, use the local export folder.'.format(exc.code, asset)) from exc
        finally:
            if temporary.exists():
                temporary.unlink()
        return path

    def load(self, lake_id, scenario, progress=lambda text: None):
        record = self.records[(str(lake_id), scenario)]
        if self.local_export:
            path = self.local_export / record['member']
        else:
            path = self.cache / record['member']
            if not path.is_file() or sha256(path) != record['npz_sha256']:
                bundle = self._download(record['asset'], progress)
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_name(path.name + '.part')
                with zipfile.ZipFile(bundle) as archive, archive.open(record['member']) as source, temporary.open('wb') as destination:
                    for block in iter(lambda: source.read(1024 * 1024), b''):
                        destination.write(block)
                if sha256(temporary) != record['npz_sha256']:
                    temporary.unlink()
                    raise ValueError('Extracted lake input failed its checksum.')
                temporary.replace(path)
        if sha256(path) != record['npz_sha256']:
            raise ValueError('Lake input checksum mismatch: ' + str(path))
        with np.load(str(path), allow_pickle=False) as packed:
            required = set(self.manifest['variables'])
            if set(packed.files) != required:
                raise ValueError('Unexpected packed input variables.')
            d = pd.DataFrame({k: packed[k] for k in packed.files if k != 'date_days'})
            d.insert(0, 'date', pd.to_datetime(packed['date_days'].astype('int64'), unit='D', origin='1970-01-01'))
        if len(d) != record['rows'] or str(d.date.iloc[0].date()) != record['first_date'] or str(d.date.iloc[-1].date()) != record['last_date']:
            raise ValueError('Packed input dates do not match the manifest.')
        d.attrs.update(scenario=scenario, forcing_model='GFDL-ESM4')
        return d
