"""Read one bundled lake outline and fit its full extent in the map view."""
from collections import OrderedDict
from pathlib import Path
import hashlib
import json
import math
import zipfile


class LakeOutlines:
    def __init__(self, root):
        self.path = Path(root) / 'assets/lake_outlines.zip'
        self.index = {}
        self._cache = OrderedDict()
        if self.path.is_file():
            with zipfile.ZipFile(self.path) as archive:
                index = json.loads(archive.read('index.json'))
            if index.get('format_version') != 1 or index.get('crs') != 'EPSG:4326':
                raise ValueError('Unsupported lake-outline archive.')
            self.index = index['lakes']

    def get(self, lake_id):
        record = self.index.get(lake_id)
        if record is None:
            return None
        if lake_id not in self._cache:
            member = 'lakes/' + lake_id + '.geojson'
            if record['member'] != member:
                raise ValueError('Unexpected outline archive member.')
            with zipfile.ZipFile(self.path) as archive:
                raw = archive.read(member)
            if hashlib.sha256(raw).hexdigest() != record['sha256']:
                raise ValueError('Lake-outline checksum mismatch.')
            feature = json.loads(raw)
            if feature['properties']['lake_id'] != lake_id:
                raise ValueError('Lake-outline ID mismatch.')
            self._cache[lake_id] = feature
            while len(self._cache) > 4:
                self._cache.popitem(last=False)
        self._cache.move_to_end(lake_id)
        return self._cache[lake_id], record


def _mercator(lon, lat):
    phi = math.radians(max(-85., min(85., lat)))
    return (lon + 180.) / 360., (1. - math.asinh(math.tan(phi)) / math.pi) / 2.


def fit_lake(map_widget, bounds):
    """Fit the complete outline, reserving room for the existing legends.

    Leaflet pixel bounds supply the rendered viewport dimensions. A conservative
    fallback is used before the widget has its first browser measurement.
    """
    west, south, east, north = [float(v) for v in bounds]
    x0, y0 = _mercator(west, north)
    x1, y1 = _mercator(east, south)
    pixels = map_widget.pixel_bounds
    width, height = 500., 430.
    if len(pixels) == 2 and all(len(p) == 2 for p in pixels):
        w, h = abs(pixels[1][0] - pixels[0][0]), abs(pixels[1][1] - pixels[0][1])
        if w > 0 and h > 0:
            width, height = float(w), float(h)
    scale = min(width * .60 / max(x1-x0, 1e-12), height * .65 / max(y1-y0, 1e-12))
    zoom = math.floor(math.log(scale / 256., 2) * 4.) / 4.
    zoom = max(float(map_widget.min_zoom), min(float(map_widget.max_zoom), zoom))
    center_lon = (x0+x1) / 2. * 360. - 180.
    center_lat = math.degrees(math.atan(math.sinh(math.pi * (1. - y0 - y1))))
    map_widget.center = (center_lat, center_lon)
    map_widget.zoom = zoom
