"""
yt_geotiff data-file handling function.



"""

import numpy as np
import rasterio

from yt.geometry.selection_routines import \
    GridSelector

from yt.frontends.ytdata.io import \
    IOHandlerYTGridHDF5


class IOHandlerYTGTiff(IOHandlerYTGridHDF5):
    _dataset_type = "ytgeotiff"
    _base = slice(None)
    _field_dtype = "float64"

    def __init__(self, ds, *args, **kwargs):
        super(IOHandlerYTGTiff, self).__init__(ds)

    def _read_fluid_selection(self, chunks, selector, fields, size):
        rv = {}
        chunks = list(chunks)
        if isinstance(selector, GridSelector):
            if not (len(chunks) == len(chunks[0].objs) == 1):
                raise RuntimeError
            g = chunks[0].objs[0]
            if g.id in self._cached_fields:
                gf = self._cached_fields[g.id]
                rv.update(gf)
            if len(rv) == len(fields): return rv
            src = rasterio.open(g.filename, "r")
            for field in fields:
                if field in rv:
                    self._hits += 1
                    continue
                self._misses += 1
                ftype, fname = field
                rv[(ftype, fname)] = src.read(int(fname)).astype(self._field_dtype) # read in the band/field
            if self._cache_on:
                for gid in rv:
                    self._cached_fields.setdefault(gid, {})
                    self._cached_fields[gid].update(rv[gid])
            return rv
        if size is None:
            size = sum((g.count(selector) for chunk in chunks
                        for g in chunk.objs))
        for field in fields:
            ftype, fname = field
            fsize = size
            rv[field] = np.empty(fsize, dtype="float64")
        ind = 0
        for chunk in chunks:
            src = None
            for g in chunk.objs:
                if g.filename is None: continue
                if src is None:
                    src = rasterio.open(g.filename, "r")
                gf = self._cached_fields.get(g.id, {})
                nd = 0
                for field in fields:
                    if field in gf:
                        nd = g.select(selector, gf[field], rv[field], ind)
                        self._hits += 1
                        continue
                    self._misses += 1
                    ftype, fname = field
                    # add extra dimensions to make data 3D
                    data = src.read(int(fname)).astype(self._field_dtype)
                    for dim in range(len(data.shape), 3):
                        data = np.expand_dims(data, dim)
                    if self._cache_on:
                        self._cached_fields.setdefault(g.id, {})
                        self._cached_fields[g.id][field] = data
                    nd = g.select(selector, data, rv[field], ind) # caches
                ind += nd
        return rv

    def _read_particle_coords(self, chunks, ptf):
        pass

    def _read_particle_fields(self, chunks, ptf, selector):
        pass
