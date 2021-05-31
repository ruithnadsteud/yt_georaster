import yt
import yt.extensions.geotiff

from yt_geotiff.testing import requires_file

landsat_data = "Landsat-8_sample_L2/LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF"
single_shapefile = "example_polygon_mabira_forest/mabira_forest.shp"

@requires_file(landsat_data)
@requires_file(single_shapefile)

def test_poly_single():
    ds = yt.load(landsat_data)
    polygon_data = ds.polygon(single_shapefile)
    data = (polygon_data[('bands', '1')])
    assert (data.size == 364687)