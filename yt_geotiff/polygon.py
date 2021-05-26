from yt.data_objects.selection_objects.data_selection_objects import \
    YTSelectionContainer3D
from yt.data_objects.static_output import Dataset
from yt.funcs import validate_object
from yt.geometry.selection_routines import SelectorObject

import fiona
import rasterio
import numpy as np
from rasterio.features import rasterize
from shapely.geometry import Polygon, Point, box, MultiPolygon
from shapely.ops import unary_union


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

        print(f"Number of features in file: {len(shapes_from_file)}")       

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
        left_edge = [self.polygon.bounds[0], self.polygon.bounds[1]]
        right_edge = [self.polygon.bounds[2], self.polygon.bounds[3]]
        
        return left_edge, right_edge

    _selector = None
    @property
    def selector(self):
        if self._selector is None:
            self._selector = PolygonSelector(self)
        return self._selector

class PolygonSelector:
    def __init__(self, dobj):
        self.dobj = dobj

        min_level = getattr(dobj, "min_level", None)
        max_level = getattr(dobj, "max_level", None)
        if min_level is None:
            min_level = 0
        if max_level is None:
            max_level = 99
        self.min_level = min_level
        self.max_level = max_level

    def select_grids(self, left_edges, right_edges, levels):
        ng = left_edges.shape[0]
        gridi = np.zeros(ng, dtype=bool)
        for i in range(ng):
            gridi[i] = self.select_grid(
                left_edges[i], right_edges[i], levels[i, 0])
        return gridi

    def select_grid(self, left_edge, right_edge, level):
        if level < self.min_level or level > self.max_level:
            return False
        return self.select_bbox(left_edge, right_edge)

    def select_cell(self, pos, dx):
        # this routine accepts a position and a width, and returns either
        # zero or one for whether or not that cell is included in the selector.

        # Get location of corners
        min_x = pos[0] - (dx/2.)
        min_y = pos[1] - (dx/2.)
        max_x = pos[0] + (dx/2.)
        max_y = pos[1] + (dx/2.)        

        # tuple of bounds
        bbox = (min_x, min_y, max_x,max_y)

        # convert bbox to shapely polygon
        cell_polygon = box(*bbox, ccw=True)

        # Determine if grid cell polygon is within polygon
        if cell_polygon.intersects(self.dobj.polygon):
            binary = 1
        else:
            binary = 0
        
        return binary

    def select_point(self, pos):
        # this identifies whether or not a point is included in the selector.
        # It should be identical to selecting a cell or a sphere with zero extent.
        
        # Determine if point within polygon 
        if Point(pos).within(self.dobj.polygon):
            binary = 1
        else:
            binary = 0

        return binary

    def select_bbox(self, left_edge, right_edge):
        # this returns whether or not a bounding box (i.e., grid) is included
        # in the selector.

        # tuple of bounds
        bbox = (left_edge[0], left_edge[1], right_edge[0], right_edge[1])

        # convert bbox to shapely polygon
        bbox_polygon = box(*bbox, ccw=True)

        # Determine if bbox polygon is within polygon
        if (self.dobj.polygon).intersects(bbox_polygon):
            binary = 1
        else:
            binary = 0
        
        return binary

    def select_sphere(self, center, radius):
        # this routine accepts a position and a width, and returns either zero
        # or one for whether or not that cell is included in the selector.

        # construct sphere/circle using a point buffer operation
        sphere_polygon = Point(center).buffer(radius)

        # Determine if bbox polygon is within polygon
        if sphere_polygon.intersects(self.dobj.polygon):
            binary = 1
        else:
            binary = 0
        
        return binary

    def fill_mask(self, grid):
        # this takes a grid object and fills a mask of which zones should be
        # included. It must take into account the child mask of the grid.

        #Generate polygon
        def poly_from_utm(polygon, transform):
            poly_pts = []
    
            poly = unary_union(polygon)
            for i in np.array(poly.exterior.coords):
        
                # Convert polygons to the image CRS
                poly_pts.append(~transform * tuple(i))
        
            # Generate a polygon object
            new_poly = Polygon(poly_pts)
            return new_poly

        # Shapely polygon dataset 
        shape_file = self.dobj.polygon 

        poly_shp = []

        # Generate Binary maks
        im_size = (grid.ds.parameters['height'], grid.ds.parameters['width'])

        for x in range(self.dobj._number_features):
            poly = poly_from_utm(shape_file[x], grid.ds.parameters['transform'])               
            poly_shp.append(poly)

        fill_mask = rasterize(shapes=poly_shp,
                 out_shape=im_size)
        fill_mask = fill_mask.astype(bool)
        fill_mask = fill_mask.T
        fill_mask = np.expand_dims(fill_mask, 2)

        return fill_mask

    def _hash_vals(self):
        # this must return some combination of parameters that semi-uniquely
        # identifies the selector.

        coords_list = [(self.dobj.polygon[x]).exterior.coords for x in \
        range(self.dobj._number_features)]

        return coords_list
