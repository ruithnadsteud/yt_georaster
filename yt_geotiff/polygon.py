from yt.data_objects.selection_objects.data_selection_objects import \
    YTSelectionContainer3D
from yt.data_objects.static_output import Dataset
from yt.funcs import validate_object, mylog

import fiona
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

from yt_geotiff.polygon_selector import PolygonSelector

class YTPolygon(YTSelectionContainer3D):
    """
    Data container for a polygon described by a set of coordinates.
    """

    _type_name = "polygon"
    _skip_add = True
    
    # What parameters are used to define a polygon?
    # For example, a sphere is center and radius.
    _con_args = ("shpfile_path",)

    # add more arguments, like path to a shape file or a shapely Polygon object
    def __init__(self, shpfile_path, ds=None, field_parameters=None):
        validate_object(ds, Dataset)
        validate_object(field_parameters, dict)

        self.shpfile_path = shpfile_path

        # read shapefile with fiona
        with fiona.open(shpfile_path, "r") as shapefile:
            shapes_from_file = [feature["geometry"] for feature in shapefile]

        mylog.info(f"Number of features in file: {len(shapes_from_file)}")

        # save number of polygons
        self._number_features = len(shapes_from_file)

        # convert all polyogn features in shapefile to list of shapely polygons
        polygons = [Polygon(shapes_from_file[i]["coordinates"][0]) for i in range(len(shapes_from_file))]

        #  fix invalid MultiPolygons
        m = MultiPolygon(polygons)

        # join all shapely polygons to a single layer
        self.polygon = unary_union(m)
        
        # define coordinates of center
        self.center = [self.polygon.centroid.coords.xy[0][0],
                       self.polygon.centroid.coords.xy[1][0]]

        data_source = None
        super().__init__(self.center, ds, field_parameters, data_source)

    def _get_bbox(self):
        """
        Return the minimum bounding box for the polygon.
        """

        left_edge = self.ds.domain_left_edge.copy()
        left_edge[:2] = self.polygon.bounds[:2]
        right_edge = self.ds.domain_right_edge.copy()
        right_edge[:2] = self.polygon.bounds[2:]
        return left_edge, right_edge

    _selector = None
    @property
    def selector(self):
        if self._selector is None:
            self._selector = PolygonSelector(self)
        return self._selector


def poly_from_utm(polygon, transform):
    poly_pts = []

    poly = unary_union(polygon)
    for i in np.array(poly.exterior.coords):

        # Convert polygons to the image CRS
        poly_pts.append(~transform * tuple(i))

    # Generate a polygon object
    new_poly = Polygon(poly_pts)
    return new_poly
