import numpy as np
import rasterio
from rasterio.warp import reproject

from yt.frontends.ytdata.io import IOHandlerYTGridHDF5
from yt.funcs import mylog
from yt.geometry.selection_routines import GridSelector


class IOHandlerGeoRaster(IOHandlerYTGridHDF5):
    """
    IOHandler for GeoRasterDataset.

    This is responsible for reading data from files.
    """

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

        read_info = self.ds.index.geo_manager.fields[field]
        filename = read_info["filename"]
        band = read_info["band"]
        resample_method = self.ds.resample_method

        with rasterio.open(filename, "r") as src:
            src_crs = src.crs
            src_transform = src.transform
            # Round up rasterio window width and height.
            rasterio_window = grid._get_full_rasterio_window(selector, src_crs, src_transform)
            src_window_transform = src.window_transform(rasterio_window)
            # Read in the band/field.
            data = src.read(
                band,
                window=rasterio_window,
                out_dtype=self._field_dtype,
                boundless=True
            )

        # get target window
        base_window_transform, width, height = grid._get_rasterio_window_transform(
            selector, None, full=True
        )
        image_units = src_crs.linear_units
        base_units = self.ds.parameters["units"]
        dst_crs = self.ds.parameters["crs"]

        # reproject to base
        if (base_window_transform != src_window_transform) or (dst_crs != src_crs):
            if dst_crs != src_crs:
                mylog.info(
                    f"Reprojecting {field}: {src_crs} "
                    f"to {dst_crs}."
                )
            if src_window_transform[0] != base_window_transform[0]:
                mylog.info(
                    f"Resampling {field}: {src_window_transform[0]} {image_units} "
                    f"to {base_window_transform[0]} {base_units}."
                )

            reproj_data = np.zeros((height, width), dtype=data.dtype)
            reproject(
                data,
                reproj_data,
                src_transform=src_window_transform,
                src_crs=src_crs,
                dst_transform=base_window_transform,
                dst_crs=dst_crs,
                resampling=resample_method
            )

            data = reproj_data

        # trim data to encompase pixels only overlapped by selector
        full_window = grid._get_full_rasterio_window(
            selector,
            dst_crs,
            self.ds.parameters['transform']
        ).flatten()
        trimmed_window = grid._get_trimmed_rasterio_window(
            selector,
            dst_crs,
            self.ds.parameters['transform']
        ).flatten()
        col_off = trimmed_window[0] - full_window[0]
        row_off = trimmed_window[1] - full_window[1]
        data = data[
            row_off: row_off + trimmed_window[3],
            col_off: col_off + trimmed_window[2]
        ]
        # Transform data to correct shape.
        data = data.T
        if self.ds._flip_axes:
            data = np.flip(data, axis=self.ds._flip_axes)

        if self._cache_on:
            self._cached_fields.setdefault(grid.id, {})
            self._cached_fields[grid.id][field] = data

        return data
