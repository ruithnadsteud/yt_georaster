import numpy as np
import rasterio
from scipy.ndimage import zoom

from yt.frontends.ytdata.io import \
    IOHandlerYTGridHDF5
from yt.funcs import mylog
from yt.geometry.selection_routines import \
    GridSelector

class IOHandlerGeoRaster(IOHandlerYTGridHDF5):
    _dataset_type = "GeoRaster"
    _base = slice(None)
    _field_dtype = "float64"
    _cache_on = False

    def __init__(self, ds, *args, **kwargs):
        super(IOHandlerGeoRaster, self).__init__(ds)

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
            if len(rv) == len(fields):
                return rv

            for field in fields:
                if field in rv:
                    self._hits += 1
                    continue
                self._misses += 1

                rv[field] = self._read_rasterio_data(selector, g, field)

        if size is None:
            size = sum((g.count(selector) for chunk in chunks for g in chunk.objs))
        for field in fields:
            ftype, fname = field
            rv[field] = np.empty(int(size), dtype=self._field_dtype)

        ind = 0
        for chunk in chunks:
            for g in chunk.objs:
                if g.filename is None:
                    continue

                gf = self._cached_fields.get(g.id, {})
                nd = 0

                for field in fields:
                    if field in gf:
                        for dim in range(len(gf[field].shape), 3):
                            gf[field] = np.expand_dims(gf[field], dim)

                        nd = g.select(selector, gf[field], rv[field], ind)
                        self._hits += 1
                        continue
                    self._misses += 1

                    data = self._read_rasterio_data(selector, g, field)
                    for dim in range(len(data.shape), 3):
                        data = np.expand_dims(data, dim)

                    nd = g.select(selector, data, rv[field], ind)
                ind += nd

        return rv

    def _read_rasterio_data(self, selector, grid, field):
        """
        Perform rasterio read and do all transformations and resamples.
        """

        ftype, fname = field
        filename = self.ds._field_band_map[fname]['filename']
        band = self.ds._field_band_map[fname]['band']

        src = rasterio.open(filename, "r")

        # Round up rasterio window width and height.
        rasterio_window = grid._get_rasterio_window(selector, src.crs, src.transform)
        rasterio_window = rasterio_window.round_shape(op='ceil', pixel_precision=None)

        # Read in the band/field.
        data = src.read(
            band, window=rasterio_window,
            out_dtype=self._field_dtype, boundless=True)

        # Transform data to correct shape.
        data = data.T
        if self.ds._flip_axes:
            data = np.flip(data, axis=self.ds._flip_axes)

        # Resample to base resolution if necessary.
        image_resolution = src.res[0]
        base_resolution = self.ds.resolution.d[0]
        if image_resolution != base_resolution:
            scale_factor = image_resolution / base_resolution
            mylog.info(f"Resampling {fname}: {image_resolution} to {base_resolution} m.")
            data = zoom(data, scale_factor, order=0)

        # Now clip to the size of the window in the base resolution.
        base_window = grid._get_rasterio_window(
            selector, self.ds.parameters['crs'], self.ds.parameters['transform'])
        data = data[:int(base_window.width), :int(base_window.height)]

        if self._cache_on:
            self._cached_fields.setdefault(grid.id, {})
            self._cached_fields[grid.id][field] = data

        return data

