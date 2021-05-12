from yt.data_objects.selection_objects.data_selection_objects import \
    YTSelectionContainer3D
from yt.data_objects.static_output import Dataset
from yt.funcs import validate_object
from yt.geometry.selection_routines import SelectorObject

import fiona
from shapely.geometry import Polygon

class YTPolygon(YTSelectionContainer3D):
    """
    Data container for a polygon described by a set of coordinates.
    """

    _type_name = "polygon"
    _skip_add = True
    
    # What parameters are used to define a polygon?
    # For example, a sphere is center and radius.
    _con_args = ()

    # add more arguments, like path to a shape file or a shapely Polygon object
    def __init__(self, shpfile_path, ds=None, field_parameters=None):
        validate_object(ds, Dataset)
        validate_object(field_parameters, dict)

        # read shapefile with fiona
        with fiona.open(shpfile_path, "r") as shapefile:
            shapes_from_file = [feature["geometry"] for feature in shapefile]

        # define a polygon with shapely using the list of coordinates
        self.shape = Polygon(shapes_from_file[0]["coordinates"][0])

        # define coordinates of center
        self.center = [self.shape.centroid.coords.xy[0][0],
                       self.shape.centroid.coords.xy[1][0]]

        data_source = None
        super().__init__(center, ds, field_parameters, data_source)

    def _get_bbox(self):
        """
        Return the minimum bounding box for the polygon.
        """

        left_edge = [self.shape.bounds[0], self.shape.bounds[1]]
        right_edge = [self.shape.bounds[2], self.shape.bounds[3]]
        return left_edge, right_edge

    _selector = None
    @property
    def selector(self):
        if self._selector is None:
            self._selector = PolygonSelector(self)
        return self._selector

class PolygonSelector(SelectorObject):
    def __init__(self, dobj):
        # set a bounding box, do any initialization
        pass

    def select_cell(self, pos, dx):
        # this routine accepts a position and a width, and returns either
        # zero or one for whether or not that cell is included in the selector.
        pass

    def select_point(self, pos):
        # this identifies whether or not a point is included in the selector.
        # It should be identical to selecting a cell or a sphere with zero extent.
        pass

    def select_bbox(self, left_edge, right_edge):
        # this returns whether or not a bounding box (i.e., grid) is included
        # in the selector.
        pass

    def select_sphere(self, center, radius):
        # this routine accepts a position and a width, and returns either zero
        # or one for whether or not that cell is included in the selector.
        pass

    def fill_mask(self, grid):
        # this takes a grid object and fills a mask of which zones should be
        # included. It must take into account the child mask of the grid.
        pass

    def _hash_vals(self):
        # this must return some combination of parameters that semi-uniquely
        # identifies the selector.

        ### Maybe return the list of x,y points?
        pass
