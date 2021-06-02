import yt
from yt.config import ytcfg
import yt.extensions.geotiff

from yt_geotiff.testing import requires_file

landsat_data = "Landsat-8_sample_L2/LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF"
shapefile_dir = ytcfg.get("yt", "example_multi-feature_polygon")

@requires_file(landsat_data)

def test_poly_multi():
    ds = yt.load(landsat_data)
    fns = (os.path.join(shapefile_dir, "multi_feature_polygon.shp"))
    polygon_data = ds.polygon(multi_shapefile)
    data = (polygon_data[('bands', '1')])
    assert (data.size == 544829)