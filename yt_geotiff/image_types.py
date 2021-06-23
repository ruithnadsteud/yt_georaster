import os
import rasterio
import re

class GeoImage:
    field_aliases = ()

    def split(self, filename):
        "Return a prefix and suffix for a filename."
        return filename.rsplit(".", 1)

    def identify(self, filename, resolution):
        prefix, _ = self.split(filename)
        return prefix, "band"

class SatGeoImage(GeoImage):
    def identify(self, filename, resolution):
        prefix, suffix = self.split(filename)
        if suffix.lower() != self._suffix:
            return None

        search = self._regex.search(prefix)
        if search is None:
            return None

        groups = search.groups()
        ftype = groups[0]
        fname = f"{self._field_prefix}_{groups[1]}_{resolution}"

        return ftype, fname

class Sentinel2(SatGeoImage):
    _regex = re.compile(r"(\w+)_([A-Za-z0-9]+)(_\d+m)?$")
    _suffix = "jp2"
    _field_prefix = "S2"

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

class GeoManager:
    image_types = (Sentinel2(), Landsat8(), GeoImage())

    def __init__(self):
        self.ftypes = []

    def process(self, index, fullpath):
        _, filename = os.path.split(fullpath)

        units = "m"
        with rasterio.open(fullpath, mode="r") as f:
            resolution = f"{int(f.res[0])}{units}"
            count = f.count

        for imager in self.image_types:
            res = imager.identify(filename, resolution)
            if res is None:
                continue
            ftype, fname = res

            if ftype not in self.ftypes:
                self.ftypes.append(ftype)

            for i in range(1, count + 1):
                fieldname = fname
                if count > 1 or fieldname == "band":
                    fieldname += f"_{i}"

                field = (ftype, fieldname)
                index.field_list.append(field)
                index.ds.field_units[field] = ""
                index.ds._field_band_map.update(
                    {fieldname: {'filename': fullpath, 'band': i}})
            break
