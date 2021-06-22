import os
import rasterio
import re

class Imager:
    field_aliases = ()

    def split(self, filename):
        "Return a prefix and suffix for a filename."
        return filename.rsplit(".", 1)

    def process(self, filename, resolution):
        prefix, _ = self.split(filename)
        return prefix, "band"

class SatImager(Imager):
    def process(self, filename, resolution):
        prefix, suffix = self.split(filename)
        if suffix.lower() != self._suffix:
            return None

        search = self._regex.search(prefix)
        if search is None:
            return None

        groups = [g for g in search.groups() if g is not None]
        fname = f"{self._field_prefix}_{groups[0]}_{resolution}"

        fsearch = re.search(f"(.+)_{''.join(groups)}", filename)
        if fsearch is None:
            return None
        ftype = fsearch.groups()[0]

        return ftype, fname

class Sentinel2(SatImager):
    _regex = re.compile(r"_([A-Za-z0-9]+)(_\d+m)?$")
    _suffix = "jp2"
    _field_prefix = "S2"

class Landsat8(SatImager):
    _regex = re.compile(r"^LC.+_([A-Za-z0-9]+)$")
    _suffix = "tif"
    _field_prefix = "L8"


class GeoManager:
    def __init__(self):
        self.ftypes = []
        self.default_imager = Imager()
        self.imagers = [Sentinel2(), Landsat8()]

    @property
    def all_imagers(self):
        return self.imagers + [self.default_imager]

    def identify(self, index, fullpath):
        _, filename = os.path.split(fullpath)

        units = "m"
        with rasterio.open(fullpath, mode="r") as f:
            resolution = f"{int(f.res[0])}{units}"
            count = f.count

        for imager in self.all_imagers:
            res = imager.process(filename, resolution)
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
