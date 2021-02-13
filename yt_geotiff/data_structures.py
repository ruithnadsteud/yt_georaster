import glob
import numpy as np
import os
import rasterio
import stat

from yt.data_objects.static_output import \
    Dataset
from yt.data_objects.selection_objects.data_selection_objects import (
    YTSelectionContainer,
)
from yt.geometry.selection_routines import \
    GridSelector, \
    RegionSelector, \
    SphereSelector
from yt.frontends.ytdata.data_structures import \
    YTGridHierarchy, \
    YTGrid

from .fields import \
    GeoTiffFieldInfo
from .utilities import \
    left_aligned_coord_cal, \
    save_dataset_as_geotiff, \
    parse_awslandsat_metafile, \
    validate_coord_array

class GeoTiffWindowGrid(YTGrid):
    def __init__(self, gridobj, left_edge, right_edge):

        YTSelectionContainer.__init__(self, gridobj._index.dataset, None)

        self.id = gridobj.id
        self._child_mask = gridobj._child_indices = gridobj._child_index_mask = None
        self.ds = gridobj._index.dataset
        self._index = gridobj._index
        self.start_index = None
        self.filename = gridobj.filename
        self._last_mask = None
        self._last_count = -1
        self._last_selector_id = None
        self._children_ids = []
        self._parent_id = -1
        self.Level = 0

        self.LeftEdge = self.ds.arr(left_edge, 'm')
        self.RightEdge = self.ds.arr(right_edge, 'm')
        # Make sure z dimension edges are the same as parent grid.
        self.LeftEdge[2] = gridobj.LeftEdge[2]
        self.RightEdge[2] = gridobj.RightEdge[2]
        self.ActiveDimensions = \
          (gridobj.ActiveDimensions *
           (self.RightEdge - self.LeftEdge) / \
           (gridobj.RightEdge - gridobj.LeftEdge)).d.astype(np.int32)
        # Inherit dx values from parent.
        self.dds = gridobj.dds

class GeoTiffGrid(YTGrid):
    _last_wgrid = None
    _last_wgrid_id = None

    def select(self, selector, source, dest, offset):
        if isinstance(selector, GridSelector):
            return super().select(selector, source, dest, offset)
        wgrid = self._get_window_grid(selector)
        rvalue = wgrid.select(selector, source, dest, offset)
        return rvalue

    def count(self, selector):
        if isinstance(selector, GridSelector):
            return super().count(selector)
        wgrid = self._get_window_grid(selector)
        rvalue = wgrid.count(selector)
        return rvalue

    def select_icoords(self, dobj):
        if isinstance(dobj.selector, GridSelector):
            return super().select_icoords(dobj)
        wgrid = self._get_window_grid(dobj.selector)
        rvalue = wgrid.select_icoords(dobj)
        return rvalue

    def select_fcoords(self, dobj):
        if isinstance(dobj.selector, GridSelector):
            return super().select_fcoords(dobj)
        wgrid = self._get_window_grid(dobj.selector)
        rvalue = wgrid.select_fcoords(dobj)
        return rvalue

    def _get_selector_mask(self, selector):
        if isinstance(selector, GridSelector):
            return super()._get_selector_mask(selector)
        wgrid = self._get_window_grid(selector)
        rvalue = wgrid._get_selector_mask(selector)
        return rvalue

    def _get_window_grid(self, selector):
        """
        Return a GeoTiffWindowGrid for a given selector.
        """

        if self._last_wgrid and hash(selector) == self._last_wgrid_id:
            return self._last_wgrid

        left_edge, right_edge = self._get_selection_window(selector)
        wgrid = GeoTiffWindowGrid(self, left_edge, right_edge)
        self._last_wgrid = wgrid
        self._last_wgrid_id = hash(selector)
        return wgrid

    def _get_selection_window(self, selector):
        """
        Calculate bounding box for selectors.
        """

        dle = self.ds.domain_left_edge.d
        dre = self.ds.domain_right_edge.d

        if isinstance(selector, SphereSelector):
            left_edge = np.array(selector.center)
            left_edge[:2] -= selector.radius
            left_edge[2] = dle[2]

            right_edge = np.asarray(selector.center)
            right_edge[:2] += selector.radius
            right_edge[2] = dre[2]

        elif isinstance(selector, RegionSelector):
            left_edge = selector.left_edge
            right_edge = selector.right_edge

        else:
            raise NotImplementedError

        left_edge.clip(min=dle, max=dre, out=left_edge)
        right_edge.clip(min=dle, max=dre, out=right_edge)
        return left_edge, right_edge

    def _get_rasterio_window(self, selector):
        """
        Calculate position, width, and height for a rasterio window read.
        """

        left_edge, right_edge = self._get_selection_window(selector)
        width = ((right_edge - left_edge) / self.dds.d).astype(int)
        return left_edge[:2].astype(int), width[:2]

    def __repr__(self):
        ad = self.ActiveDimensions
        return f"GeoTiffGrid ({ad[0]}x{ad[1]})"
 
class GeoTiffHierarchy(YTGridHierarchy):
    grid = GeoTiffGrid

    def _detect_output_fields(self):
        self.field_list = []
        self.ds.field_units = self.ds.field_units or {}
        with rasterio.open(self.ds.parameter_filename, "r") as f:
            group = 'bands'
            for _i in range(1, f.count + 1):
                field_name = (group, str(_i))
                self.field_list.append(field_name)
                self.ds.field_units[field_name] = ""
                
    def _count_grids(self):
        self.num_grids = 1
        
class GeoTiffDataset(Dataset):
    """Dataset for saved covering grids, arbitrary grids, and FRBs."""
    _index_class = GeoTiffHierarchy
    _field_info_class = GeoTiffFieldInfo
    _dataset_type = 'geotiff'
    _valid_extensions = ('.tif', '.tiff')
    geometry = "cartesian"
    default_fluid_type = "bands"
    fluid_types = ("bands", "index", "sentinel2")
    periodicity = np.zeros(3, dtype=bool)
    cosmological_simulation = False       
    
    _con_attrs = ()
    
    def __init__(self, filename, field_map=None):
        self.field_map = field_map
        super(GeoTiffDataset, self).__init__(
            filename, self._dataset_type, unit_system="mks")
        self.data = self.index.grids[0]
        
    def _parse_parameter_file(self):
        self.num_particles = {}
        with rasterio.open(self.parameter_filename, "r") as f:
            for key in f.meta.keys():
                v = f.meta[key]
                self.parameters[key] = v

        ### TODO: can we get time info from metadata?
        self.current_time = 0

        width = self.parameters['width']
        height = self.parameters['height']
        transform = self.parameters['transform']
        self.dimensionality = 3
        self.domain_dimensions = np.array([height, width, 1], dtype=np.int32)

        rast_left = np.concatenate([transform * (0, 0), [0]])
        rast_right = np.concatenate([transform * (width, height), [1]])
        right_edge = rast_right - rast_left
        # up is down in GeoTiff
        right_edge[1] *= -1

        self.domain_left_edge = self.arr(np.zeros(self.dimensionality), 'm')
        self.domain_right_edge = self.arr(right_edge, 'm')

    def _set_code_unit_attributes(self):
        attrs = ('length_unit', 'mass_unit', 'time_unit',
                 'velocity_unit', 'magnetic_unit')
        si_units = ('m', 'kg', 's', 'm/s', 'T')
        base_units = np.ones(len(attrs), dtype=np.float64)
        for unit, attr, si_unit in zip(base_units, attrs, si_units):
            setattr(self, attr, self.quan(unit, si_unit))

    def save_as(self, filename):
        ### TODO: generalize this to save any dataset type as GeoTiff.
        return save_dataset_as_geotiff(self, filename)

    def __repr__(self):
        fn = self.basename
        for ext in self._valid_extensions:
            if fn.endswith(ext):
                fn = fn[:-len(ext)]
                break
        return fn

    def circle(self, center, radius):
        """
        Create a circular data container.

        This is a wrapper around the sphere data container
        that allows for specifying the center with only x
        and y values.

        Parameters
        ----------
        center : array_like of length 2 or 3
            Center of the circle. If center is of length 2,
            the third dimension is the domain center in the
            z direction. If center is of length 3, center is
            unaltered.
        radius : float, width specifier, or unyt_quantity
            The radius of the sphere. If passed a float,
            that will be interpreted in code units. Also
            accepts a (radius, unit) tuple or unyt_quantity
            instance with units attached.

        Examples
        --------
        >>> center = ds.arr([100, 100], 'm')
        >>> cir = ds.circle(center, (1, 'km'))
        >>> vals = cir[("Bands", "1")]
        """

        cc = validate_coord_array(
            self, center, "center",
            self.domain_center[2], "code_length")
        return self.sphere(cc, radius)

    def rectangle(self, left_edge, right_edge):
        """
        Create a rectangular data container.

        This is a wrapper around the box data container that allows
        the edges to be specified with only x and y values.

        Takes an array of two or three *left_edge* coordinates and two
        or three *right_edge* coordinates that can be anywhere in the
        domain. If the selected region extends past the edges of the
        domain, no data will be found there, though the object's
        *left_edge* or *right_edge* are not modified.

        Parameters
        ----------
        left_edge : array_like
            The left edge of the region. If array is of length 2,
            the third dimension is the domain left edge in the z
            direction. If array is of length 3, left_edge is
            unaltered.
        right_edge : array_like
            The right edge of the region. If array is of length 2,
            the third dimension is the domain right edge in the z
            direction. If array is of length 3, right_edge is
            unaltered.

        Examples
        --------
        >>> left_edge = ds.arr([1, 1], 'km')
        >>> right_edge = ds.arr(5, 5], 'km')
        >>> rec = ds.rectangle(left_edge, right_edge)
        >>> vals = rec[("Bands", "1")]
        """

        le = validate_coord_array(
            self, left_edge, "left_edge",
            self.domain_left_edge[2], "code_length")
        re = validate_coord_array(
            self, right_edge, "right_edge",
            self.domain_right_edge[2], "code_length")
        return self.box(le, re)

    @classmethod
    def _is_valid(self, *args, **kwargs):
        fn = args[0]
        valid = False
        for ext in self._valid_extensions:
            if fn.endswith(ext) or fn.endswith(ext.upper()):
                valid = True
                break
        if not valid:
            return False
     
        with rasterio.open(fn, "r") as f:
            driver_type = f.meta["driver"]
            if driver_type == "GTiff":
                return True
        return False
 
class LandSatGeoTiffHierarchy(GeoTiffHierarchy):
    def _detect_output_fields(self):
        self.field_list = []
        self.ds.field_units = self.ds.field_units or {}
        
        # get list of filekeys
        filekeys = [s for s in self.ds.parameters.keys() if 'FILE_NAME_BAND_' in s]
        files = [self.ds.data_dir + self.ds.parameters[filekey] for filekey in filekeys]
        
        group = 'bands'
        for file in files:
            band = file.split(os.path.sep)[-1].split('.')[0].split('B')[1]
            field_name = (group, band)
            self.field_list.append(field_name)
            self.ds.field_units[field_name] = ""     
            
class LandSatGeoTiffDataSet(GeoTiffDataset):
    """"""
    _index_class = LandSatGeoTiffHierarchy
    
    def _parse_parameter_file(self):
        self.current_time = 0.
        self.unique_identifier = \
            int(os.stat(self.parameter_filename)[stat.ST_CTIME])
            
        # self.parameter_filename is the dir str
        if self.parameter_filename[-1] == '/':
            self.data_dir = self.parameter_filename
            self.mtlfile = self.data_dir + self.parameter_filename[:-1].split(os.path.sep)[-1] + '_MTL.txt'
            self.angfile = self.data_dir + self.parameter_filename[:-1].split(os.path.sep)[-1] + '_ANG.txt'
        else:
            self.data_dir = self.parameter_filename + '/'
            self.mtlfile = self.data_dir + self.parameter_filename.split(os.path.sep)[-1] + '_MTL.txt'
            self.angfile = self.data_dir + self.parameter_filename .split(os.path.sep)[-1]+ '_ANG.txt'
        # load metadata files
        self.parameters.update(parse_awslandsat_metafile(self.angfile))
        self.parameters.update(parse_awslandsat_metafile(self.mtlfile))
        
        # get list of filekeys
        filekeys = [s for s in self.parameters.keys() if 'FILE_NAME_BAND_' in s]
        files = [self.data_dir + self.parameters[filekey] for filekey in filekeys]
        self.parameters['count'] = len(filekeys)
        # take the parameters displayed in the filename
        self._parse_landsat_filename_data(self.parameter_filename.split(os.path.sep)[-1])       
        
        for filename in files:
            band = filename.split(os.path.sep)[-1].split('.')[0].split('B')[1]
            # filename = self.parameters[band]
            with rasterio.open(filename, "r") as f:
                for key in f.meta.keys():
                    # skip key if already defined as a parameter
                    if key in self.parameters.keys(): continue
                    v = f.meta[key]
                    # if key == "con_args":
                    #     v = v.astype("str")
                    self.parameters[(band, key)] = v
                self._with_parameter_file_open(f)
                # self.parameters['transform'] = f.transform
                
            if band == '1':
                self.domain_dimensions = np.array([self.parameters[(band, 'height')],
                                                   self.parameters[(band, 'width')],
                                                   1], dtype=np.int32)
                self.dimensionality = 3
                rightedge_xy = left_aligned_coord_cal(self.domain_dimensions[0],
                                                  self.domain_dimensions[1],
                                                  self.parameters[(band, 'transform')])
                
                self.domain_left_edge = self.arr(np.zeros(self.dimensionality,
                                                           dtype=np.float64), 'm')
                self.domain_right_edge = self.arr([rightedge_xy[0],
                                                  rightedge_xy[1],
                                                  1], 'm', dtype=np.float64)
    
    def _parse_landsat_filename_data(self, filename):
        """
        "LXSS_LLLL_PPPRRR_YYYYMMDD_yyyymmdd_CC_TX"
        L = Landsat
        X = Sensor ("C"=OLI/TIRS combined,
                    "O"=OLI-only, "T"=TIRS-only, 
                    E"=ETM+, "T"="TM, "M"=MSS)
        SS = Satellite ("07"=Landsat 7, "08"=Landsat 8)
        LLLL = Processing correction level (L1TP/L1GT/L1GS)
        PPP = WRS path
        RRR = WRS row
        YYYYMMDD = Acquisition year, month, day
        yyyymmdd - Processing year, month, day
        CC = Collection number (01, 02, …)
        TX = Collection category ("RT"=Real-Time, "T1"=Tier 1,
                                  "T2"=Tier 2)
        """
        sensor = {"C": "OLI&TIRS combined",
                  "O": "OLI-only",
                  # "T": "TIRS-only", commenting out to fix flake8 error
                  "E": "ETM+", "T": "TM", "M": "MSS"}
        satellite = {"07": "Landsat 7",
                     "08": "Landsat 8"}
        category = {"RT": "Real-Time", "T1": "Tier 1",
                    "T2": "Tier 2"}
        
        self.parameters['sensor'] = sensor[filename[1]]
        self.parameters['satellite'] = satellite[filename[2:4]]
        self.parameters['level'] = filename[5:9]        
        
        self.parameters['wrs'] = {'path': filename[10:13],
                                  'row': filename[13:16]}
        
        self.parameters['acquisition_time'] = {'year': filename[17:21],
                                               'month': filename[21:23],
                                               'day': filename[23:25]}
        self.parameters['processing_time'] = {'year': filename[26:30],
                                              'month': filename[30:32],
                                              'day': filename[32:34]}
        self.parameters['collection'] = {
                                'number': filename[35:37],
                                'category': category[filename[38:40]]}
    
    @classmethod
    def _is_valid(self, *args, **kwargs):
        if not os.path.isdir(args[0]): return False
        if len(glob.glob(args[0]+'/L*_ANG.txt')) != 1 and\
           len(glob.glob(args[0]+'/L*_MTL.txt')) != 1: return False
        try:
            file = glob.glob(args[0]+'/*.TIF')[0] # open the first file
            with rasterio.open(file, "r") as f:
                # data_type = parse_gtif_attr(f, "dtype")
                driver_type = f.meta["driver"]
                # if data_type == "uint16":
                #     return True
                if driver_type == "GTiff":
                    return True
        except:
            pass
        return False
