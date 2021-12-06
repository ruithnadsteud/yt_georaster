import os
import rasterio
import re
import yaml


class GeoImage:
    _band_aliases = ()

    def split(self, filename):
        "Return a prefix and suffix for a filename."
        return filename.rsplit(".", 1)

    def identify(self, filename):
        prefix, _ = self.split(filename)
        return prefix, None


class SatGeoImage(GeoImage):
    def identify(self, filename):
        prefix, suffix = self.split(filename)
        if suffix.lower() != self._suffix:
            return None

        search = self._regex.search(prefix)
        if search is None:
            return None

        groups = search.groups()
        ftype = groups[0]
        fprefix = f"{self._field_prefix}_{groups[1]}"

        return ftype, fprefix


class Sentinel2(SatGeoImage):
    _regex = re.compile(
        r'^[A-Za-z0-9]+_[A-Za-z0-9]+_([A-Za-z0-9]+)_[A-Za-z0-9]+_'
        r'[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+_'
        r'([A-Za-z0-9]+)(?:_\\d+m)?$'
    )
    _suffix = "jp2"
    _field_prefix = "S2"
    _band_aliases = (
        ("B01", ("ultra_blue",)),
        ("B02", ("blue",)),
        ("B03", ("green",)),
        ("B04", ("red",)),
        ("B05", ("vnir_1", "red_edge_1")),
        ("B06", ("vnir_2", "red_edge_2")),
        ("B07", ("vnir_3",)),
        ("B08", ("vnir_4",)),
        ("B8A", ("vnir_5", "nir")),
        ("B09", ("swir_1",)),
        ("B10", ("swir_2",)),
        ("B11", ("swir_3",)),
        ("B12", ("swir_4",)),
    )


class Landsat8(SatGeoImage):
    """
    LXSS_LLLL_PPPRRR_YYYYMMDD_yyyymmdd_CC_TX
    L = Landsat (constant)
    X = Sensor (C = OLI / TIRS, O = OLI-only, T= TIRS-only, E = ETM+, T = TM, M= MSS)
    SS = Satellite (e.g., 04 for Landsat 4, 05 for Landsat 5, 07 for Landsat 7, etc.)
    LLLL = Processing level (L1TP, L1GT, L1GS)
    PPP = WRS path
    RRR = WRS row
    YYYYMMDD = Acquisition Year (YYYY) / Month (MM) / Day (DD)
    yyyymmdd = Processing Year (yyyy) / Month (mm) / Day (dd)
    CC = Collection number (e.g., 01, 02, etc.)
    TX= RT for Real-Time, T1 for Tier 1 (highest quality), and T2 for Tier 2
    """

    _regex = re.compile(
        r"(^L[COTEM]08_L\w{3}_\d{6}_\d{8}_\d{8}_\d{2}_\w{2})\w+_([A-Za-z0-9]+)$"
    )
    _suffix = "tif"
    _field_prefix = "L8"
    _band_aliases = (
        ("B1", ("visible_1",)),
        ("B2", ("visible_2",)),
        ("B3", ("visible_3",)),
        ("B4", ("red",)),
        ("B5", ("nir",)),
        ("B6", ("swir_1",)),
        ("B7", ("swir_2",)),
        ("B8", ("pan",)),
        ("B9", ("cirrus",)),
        ("B10", ("tirs_1",)),
        ("B11", ("tirs_2",)),
    )


class GeoManager:
    image_types = (Sentinel2(), Landsat8(), GeoImage())

    def __init__(self, index, field_map=None):
        self.index = index
        self.ftypes = []
        self.fields = {}

        self.load_field_map(field_map)

    def load_field_map(self, fn):
        if fn is None:
            self.field_map = {}
            return

        with open(fn, mode="r") as f:
            self.field_map = yaml.load(f, Loader=yaml.FullLoader)

    def add_field_type(self, ftype):
        if ftype not in self.ftypes:
            self.ftypes.append(ftype)

    @property
    def band_aliases(self):
        aliases = {}
        for it in self.image_types:
            for field, band_aliases in it._band_aliases:
                fname = f"{it._field_prefix}_{field}"
                aliases[fname] = band_aliases
        return aliases

    def create_fields(self, fullpath, ftype, fprefix):
        units = "m"
        with rasterio.open(fullpath, mode="r") as f:
            resolution = f"{int(f.res[0])}{units}"
            count = f.count

        if fprefix is None:
            fkey = "band"
        else:
            fkey = f"{fprefix}_{resolution}"

        fmap = self.field_map

        # get the path used as key by yaml file if available
        try:
            paths_in_yaml = list(fmap.keys())
            if not(fullpath in paths_in_yaml):
                # assumes field_map:file is 1:1
                path_from_yaml = paths_in_yaml[0]
            else:
                path_from_yaml = fullpath
        except AttributeError:
            path_from_yaml = fullpath

        for i in range(1, count + 1):
            fname = fkey
            if count > 1 or fname == "band":
                fname += f"_{i}"
            entry = fmap.get(path_from_yaml, {}).get(fname)
            if entry is not None:
                field = (entry["field_type"], entry["field_name"])
                units = entry.get("units", "")
            else:
                field = (ftype, fname)
                units = ""

            self.fields[field] = {"filename": fullpath, "band": i}
            self.index.field_list.append(field)
            self.index.ds.field_units[field] = units
            self.add_field_type(field[0])

    def process_files(self, fullpaths):
        for fn in fullpaths:
            self.process_file(fn)

    def process_file(self, fullpath):
        _, filename = os.path.split(fullpath)

        for imager in self.image_types:
            res = imager.identify(filename)
            if res is None:
                continue

            ftype, fprefix = res
            self.create_fields(fullpath, ftype, fprefix)
            break
