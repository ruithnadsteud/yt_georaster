from yt.data_objects.selection_objects.data_selection_objects import (
    YTSelectionContainer3D,
)
from yt.data_objects.static_output import Dataset
from yt.funcs import validate_object, mylog

import fiona
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from rasterio.crs import CRS
from rasterio.warp import transform_geom

from yt_georaster.polygon_selector import PolygonSelector


class YTPolygon(YTSelectionContainer3D):
    """
    Create a data container for a polygon described by a set of coordinates.

    Parameters
    ----------
    filename : string
        Path to a Shapefile

    Examples
    --------
    >>> import glob
    >>> import yt
    >>> import yt.extensions.georaster
    >>> fns = glob.glob("Landsat-8_sample_L2/*.TIF")
    >>> ds = yt.load(*fns)
    >>> poly = ds.polygon("example_polygon_mabira_forest/mabira_forest.shp")
    >>> print (poly["LC08_L2SP_171060_20210227_20210304_02_T1", "red"])
    """

    _type_name = "polygon"
    _skip_add = True

    # What parameters are used to define a polygon?
    # For example, a sphere is center and radius.
    _con_args = ("filename",)

    # add more arguments, like path to a shape file or a shapely Polygon object
    def __init__(self, filename, ds=None, field_parameters=None, crs=None):
        validate_object(ds, Dataset)
        validate_object(field_parameters, dict)
        self.src_crs = crs
        if isinstance(filename, str):
            self.filename = filename

            # read shapefile with fiona
            with fiona.open(filename, "r") as shapefile:
                shapes_from_file = [feature["geometry"] for feature in shapefile]
                self.src_crs = CRS.from_dict(**shapefile.crs)  # shapefile crs

            # save number of polygons
            self._number_features = len(shapes_from_file)

            # reproject to datasets crs
            for i in range(self._number_features):
                shapes_from_file[i] = transform_geom(
                    f'EPSG:{self.src_crs.to_epsg()}',
                    f'EPSG:{ds.parameters["crs"].to_epsg()}',
                    shapes_from_file[i]
                )
            # convert all polygon features in shapefile to list of shapely polygons
            polygons = [
                Polygon(shapes_from_file[i]["coordinates"][0])
                for i in range(self._number_features)
            ]
            # fix invalid MultiPolygons
            m = MultiPolygon(polygons)
            # join all shapely polygons to a single layer
            self.polygon = unary_union(m)

        elif isinstance(filename, Polygon):
            # only one polygon
            self._number_features = 1
            self.polygon = filename
            if not (self.src_crs is None):
                self._reproject_polygon(ds.parameters['crs'])

        elif isinstance(filename, MultiPolygon):
            # only one polygon
            self._number_features = len(filename.geoms)
            self.polygon = unary_union(filename)
            if not (self.src_crs is None):
                self._reproject_polygon(ds.parameters['crs'])

        elif isinstance(filename, list):
            # assume list of shapely polygons
            self._number_features = len(filename)
            # fix invalid MultiPolygons
            m = MultiPolygon(filename)
            # join all shapely polygons to a single layer
            self.polygon = unary_union(m)
            if not (self.src_crs is None):
                self._reproject_polygon(ds.parameters['crs'])

        mylog.info(
            f"Number of features in poly object: {self._number_features}"
        )

        # define coordinates of center
        self.center = [
            self.polygon.centroid.coords.xy[0][0],
            self.polygon.centroid.coords.xy[1][0],
        ]

        data_source = None
        super().__init__(self.center, ds, field_parameters, data_source)

    def _reproject_polygon(self, dst_crs):
        """
        Reproject polygon objects to destination projection.

        fiona transform geom object does not handle shapely objects but
        "GeoJSON-like" dictionaries instead.
        """
        # get epsg
        src_crs = self.src_crs
        if isinstance(src_crs, int):
            # assume epsg number
            epsg = src_crs
        elif isinstance(src_crs, dict):
            src_crs = CRS.from_dict(**src_crs)
            epsg = src_crs.to_epsg()
        elif isinstance(src_crs, CRS):
            epsg = src_crs.to_epsg()
        else:
            src_crs = CRS.from_string(src_crs)
            epsg = src_crs.to_epsg()

        if dst_crs.to_epsg() != epsg:
            if isinstance(self.polygon, MultiPolygon):
                coords = [list(geom.exterior.coords) for geom in self.polygon.geoms]
                type_str = 'MultiPolygon'
                transformed_poly = transform_geom(
                    f'EPSG:{epsg}',
                    f'EPSG:{dst_crs.to_epsg()}',
                    {
                        'type': type_str,
                        'coordinates': coords
                    }
                )
                # convert all polygon features back to shapely polygons
                polygons = [
                    Polygon(transformed_poly[i]["coordinates"][0])
                    for i in range(len(transformed_poly))
                ]
                # join all shapely polygons to a single layer
                self.polygon = unary_union(MultiPolygon(polygons))
            else:
                coords = list(self.polygon.exterior.coords)
                type_str = 'Polygon'
                transformed_poly = transform_geom(
                    f'EPSG:{epsg}',
                    f'EPSG:{dst_crs.to_epsg()}',
                    {
                        'type': type_str,
                        'coordinates': coords
                    }
                )
                self.polygon = Polygon(transformed_poly['coordinates'][0])

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
