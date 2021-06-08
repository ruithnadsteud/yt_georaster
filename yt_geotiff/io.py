import numpy as np
import rasterio

import scipy.ndimage

from yt.geometry.selection_routines import \
    GridSelector

from yt.frontends.ytdata.io import \
    IOHandlerYTGridHDF5

from yt.funcs import mylog

class IOHandlerGeoRaster(IOHandlerYTGridHDF5):
    _dataset_type = "GeoRaster"
    _base = slice(None)
    _field_dtype = "float64"
    _cache_on = False

    def __init__(self, ds, *args, **kwargs):
        super(IOHandlerGeoRaster, self).__init__(ds)

    def _transform_data(self, data):
        data = data.T
        if self.ds._flip_axes:
            data = np.flip(data, axis=self.ds._flip_axes)
        return data

    def _resample(self, data, fname, scale_factor, original_res, load_res, order):
        mylog.info(f"Resampling {fname}: {original_res} to {load_res} m.")        
        data_resample = scipy.ndimage.zoom(data,scale_factor, order=order)     
        return data_resample

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
                ftype, fname = field 
                
                filename=self.ds._file_band_number[fname]['filename']      
                band_number= self.ds._file_band_number[fname]['band']                        

                src = rasterio.open(filename, "r")
                rasterio_window = g._get_rasterio_window(selector, src.crs, src.transform)

                # round up rasterio window width and height
                rasterio_window = rasterio_window.round_shape(op='ceil', pixel_precision=None)

                # Read in the band/field

                data = src.read(band_number, window=rasterio_window, boundless=True).astype(
                    self._field_dtype) # could be multiband
                data = self._transform_data(data)
                
                # Get resolution from load image
                load_resolution = self.ds.resolution.d[0]
                                
                if src.res[0] !=load_resolution:
                    # Calculate scale factor to adjust resolution
                    scale_factor = src.res[0]/load_resolution
                     
                    # Order of spline interpolation- has to be in the range 0 (no interp.) to 5.
                    data = self._resample(data, \
                        fname, scale_factor, src.res[0], load_resolution, order=0)
                    
                base_window = g._get_rasterio_window(
                    selector, self.ds.parameters['crs'], self.ds.parameters['transform'])
                rv[(ftype, fname)] = data[:int(base_window.width), :int(base_window.height)]

            if self._cache_on:
                self._cached_fields.setdefault(g.id, {})
                self._cached_fields[g.id].update(rv)
            return rv

        if size is None:
            size = sum((g.count(selector) for chunk in chunks for g in chunk.objs))
        for field in fields:
            ftype, fname = field
            fsize = size
            rv[field] = np.empty(int(fsize), dtype="float64")
        ind = 0
                
        for chunk in chunks:
            src = None
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
                   
                    ftype, fname = field
                    filename= self.ds._file_band_number[fname]['filename']  
                    band_number = self.ds._file_band_number[fname]['band']
                    
                    src = rasterio.open(filename, "r")

                    base_window = g._get_rasterio_window(
                        selector, self.ds.parameters['crs'], self.ds.parameters['transform'])

                    rasterio_window = g._get_rasterio_window(
                        selector, src.crs, src.transform)

                    # Round up rasterio window width and height
                    rasterio_window = rasterio_window.round_shape(op='ceil', pixel_precision=None)

                    # Perform Rasterio window read
                    data = src.read(band_number, window=rasterio_window, boundless=True).astype(
                            self._field_dtype)
                    data = self._transform_data(data)
                    
                    # Get resolution from load image
                    load_resolution = self.ds.resolution.d[0]

                    if src.res[0] != load_resolution:
                        scale_factor = src.res[0] / load_resolution
                        # Order of the spline interpolation, 0 (no interp.) to 5.
                        data = self._resample(data, fname, scale_factor,
                                              src.res[0], load_resolution, order=0)

                    data = data[:int(base_window.width), :int(base_window.height)]

                    for dim in range(len(data.shape), 3):
                        data = np.expand_dims(data, dim)

                    if self._cache_on:
                        self._cached_fields.setdefault(g.id, {})
                        self._cached_fields[g.id][field] = data

                    nd = g.select(selector, data, rv[field], ind)

                ind += nd

        return rv
