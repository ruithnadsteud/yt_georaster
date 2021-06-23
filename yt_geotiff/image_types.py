import os
import rasterio
import re

class GeoImage:
    field_aliases = ()

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
    _regex = re.compile(r"(\w+)_([A-Za-z0-9]+)(_\d+m)?$")
    _suffix = "jp2"
    _field_prefix = "S2"
    _band_aliases = (
        ("B01", ("ultra_blue",)),
        ("B02", ("blue",)),
        ("B03", ("green",)),
        ("B04", ("red",)),
        ("B05", ("vnir1", "red_edge1")),
        ("B06", ("vnir2", "red_edge2")),
        ("B07", ("vnir3",)),
        ("B08", ("vnir4",)),
        ("B8A", ("vnir5", "nir")),
        ("B09", ("swir1",)),
        ("B10", ("swir2",)),
        ("B11", ("swir3",)),
        ("B12", ("swir4",)),
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
    _regex = re.compile(r"(^L[COTEM]08_L\w{3}_\d{6}_\d{8}_\d{8}_\d{2}_\w{2})\w+_([A-Za-z0-9]+)$")
    _suffix = "tif"
    _field_prefix = "L8"
    _band_aliases = (
        ("B1", ("visible1",)),
        ("B2", ("visible2",)),
        ("B3", ("visible3",)),
        ("B4", ("red",)),
        ("B5", ("nir",)),
        ("B6", ("swir1",)),
        ("B7", ("swir2",)),
        ("B8", ("pan",)),
        ("B9", ("cirrus",)),
        ("B10", ("tirs1",)),
        ("B11", ("tirs2",)),
    )

class GeoManager:
    image_types = (Sentinel2(), Landsat8(), GeoImage())

    def __init__(self, index):
        self.index = index
        self.ftypes = []

    def add_field_type(self, ftype):
        if ftype not in self.ftypes:
            self.ftypes.append(ftype)

    def create_fields(self, fullpath, ftype, fprefix):
        units = "m"
        with rasterio.open(fullpath, mode="r") as f:
            resolution = f"{int(f.res[0])}{units}"
            count = f.count

        if fprefix is None:
            fname = "band"
        else:
            fname = f"{fprefix}_{resolution}"

        for i in range(1, count + 1):
            if count > 1 or fname == "band":
                fname += f"_{i}"

            field = (ftype, fname)
            self.index.field_list.append(field)
            self.index.ds.field_units[field] = ""
            self.index.ds._field_band_map.update(
                {fname: {'filename': fullpath, 'band': i}})

    def process(self, fullpath):
        _, filename = os.path.split(fullpath)

        for imager in self.image_types:
            res = imager.identify(filename)
            if res is None:
                continue

            ftype, fprefix = res
            self.add_field_type(ftype)
            self.create_fields(fullpath, ftype, fprefix)
            break
