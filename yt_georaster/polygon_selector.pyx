cimport numpy as np
import numpy as np

from yt.geometry.selection_routines cimport SelectorObject

import rasterio
from rasterio.features import rasterize
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

cdef class PolygonSelector(SelectorObject):
    cdef public object dobj

    def __init__(self, dobj):
        self.dobj = dobj

    cdef int select_cell(self, np.float64_t pos[3], np.float64_t dds[3]) nogil:
        # this routine accepts a position and a width, and returns either
        # zero or one for whether or not that cell is included in the selector.

        with gil:

            dx = dds[0]

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

    cdef int select_point(self, np.float64_t pos[3]) nogil:
        # this identifies whether or not a point is included in the selector.
        # It should be identical to selecting a cell or a sphere with zero extent.

        with gil:
            my_pos = np.empty(3, dtype=np.float64)
            for i in range(3):
                my_pos[i] = pos[i]

            # Determine if point within polygon 
            if Point(my_pos).within(self.dobj.polygon):
                binary = 1
            else:
                binary = 0

        return binary

    cdef int select_bbox(self, np.float64_t left_edge[3],
                               np.float64_t right_edge[3]) nogil:
        # this returns whether or not a bounding box (i.e., grid) is included
        # in the selector.

        # tuple of bounds
        with gil:
        
            bbox = (left_edge[0], left_edge[1], right_edge[0], right_edge[1])

            # convert bbox to shapely polygon
            bbox_polygon = box(*bbox, ccw=True)

            # Determine if bbox polygon is within polygon
            if (self.dobj.polygon).intersects(bbox_polygon):
                binary = 1
            else:
                binary = 0
        
        return binary

    cdef int select_sphere(self, np.float64_t pos[3], np.float64_t radius) nogil:
        # this routine accepts a position and a width, and returns either zero
        # or one for whether or not that cell is included in the selector.

        with gil:
            my_pos = np.empty(3, dtype=np.float64)
            for i in range(3):
                my_pos[i] = pos[i]

            # construct sphere/circle using a point buffer operation
            sphere_polygon = Point(my_pos).buffer(radius)

            # Determine if bbox polygon is within polygon
            if sphere_polygon.intersects(self.dobj.polygon):
                binary = 1
            else:
                binary = 0
        
        return binary

    def fill_mask(self, grid):
        # this takes a grid object and fills a mask of which zones should be
        # included. It must take into account the child mask of the grid.

        # Shapely polygon dataset
        shape_file = self.dobj.polygon
        ds = grid.ds

        new_transform, _, _ = grid._get_rasterio_window_transform(self, None)

        dims = np.flip(grid.ActiveDimensions[:2])
        if self.dobj._number_features > 1:
            my_shapes = self.dobj.polygon
        else:
            my_shapes = [self.dobj.polygon]
        fill_mask = rasterize(shapes=my_shapes,
                              transform=new_transform,
                              out_shape=dims, all_touched=True)
        fill_mask = fill_mask.T
        if ds._flip_axes:
            fill_mask = np.flip(fill_mask, axis=ds._flip_axes)
        fill_mask = fill_mask.astype(bool)
        fill_mask = np.expand_dims(fill_mask, 2)

        return fill_mask

    def _hash_vals(self):
        # this must return some combination of parameters that semi-uniquely
        # identifies the selector.

        if self.dobj._number_features > 1:
            return tuple([self.dobj.polygon[x].exterior.coords for x in \
                          range(self.dobj._number_features)])
        else:
            return tuple([self.dobj.polygon.exterior.coords])
