"""
yt_geotiff data-file handling function.



"""
from collections import defaultdict

import numpy as np

import rasterio

from yt.geometry.selection_routines import \
    GridSelector
# from yt.utilities.io_handler import \
#     BaseIOHandler
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
        # Now we have to do something unpleasant
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
                rv[(ftype, fname)] = src.read(int(fname)) # read in the band/field
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
        ng = sum(len(c.objs) for c in chunks)
        # mylog.debug("Reading %s cells of %s fields in %s grids",
        #            size, [f2 for f1, f2 in fields], ng)
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
                    data = src.read(int(fname))#.astype(self._field_dtype)
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
    # def _read_fluid_selection(self, chunks, selector, fields, size):
    #     chunks = list(chunks)
    #     # if any(( not (ftype == "boxlib" or ftype == 'raw') for ftype, fname in fields)):
    #     #     raise NotImplementedError
    #     rv = {}
    #     raw_fields = []
    #     for field in fields:
    #         rv[field] = np.empty(size, dtype="float64")
    #     ng = sum(len(c.objs) for c in chunks)
    #     # mylog.debug("Reading %s cells of %s fields in %s grids",
    #     #             size, [f2 for f1, f2 in fields], ng)
    #     ind = 0
    #     for chunk in chunks:
    #         data = self._read_chunk_data(chunk, fields)
    #         for g in chunk.objs:
    #             for field in fields:
    #                 ds = self._read_raw_field(g, field)
    #                 nd = g.select(selector, ds, rv[field], ind)
    #             ind += nd
    #             data.pop(g.id)
    #     return rv

    # def _read_raw_field(self, grid, field):
    #     band = field[1] # band number
    #     with rasterio.open(self.ds.parameter_filename, "r") as f:
    #         field_data = f.read(int(band))
    #     return field_data

    # def _read_chunk_data(self, chunk, fields):
    #     data = {}
    #     grids_by_file = defaultdict(list)
    #     if len(chunk.objs) == 0: return data
    #     for g in chunk.objs:
    #         if g.filename is None:
    #             continue
    #         grids_by_file[g.filename].append(g)
    #     dtype = np.float64
    #     bpr = dtype.itemsize
    #     for filename in grids_by_file:
    #         grids = grids_by_file[filename]
    #         grids.sort(key = lambda a: a._offset)
    #         f = rasterio.open(filename, "r")
    #         for grid in grids:
    #             data[grid.id] = {}
    #             local_offset = grid._get_offset(f) - f.tell()
    #             count = grid.ActiveDimensions.prod()
    #             size = count * bpr
    #             for field in self.ds.index.field_order:
    #                 if field in fields:
    #                     # We read it ...
    #                     f.seek(local_offset, os.SEEK_CUR)
    #                     v = np.fromfile(f, dtype=dtype, count=count)
    #                     v = v.reshape(grid.ActiveDimensions, order='F')
    #                     data[grid.id][field] = v
    #                     local_offset = 0
    #                 else:
    #                     local_offset += size
    #     return data