import yt
from yt.config import ytcfg
import yt.extensions.geotiff
import os
from yt_geotiff.testing import requires_file

landsat_data = "Landsat-8_sample_L2/LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF"
test_data_dir = ytcfg.get("yt", "test_data_dir")

@requires_file(landsat_data)
def test_poly_single():
    ds = yt.load(landsat_data)
    fns = os.path.join(test_data_dir, "example_polygon_mabira_forest/mabira_forest.shp")
    polygon_data = ds.polygon(fns)
    data = polygon_data[('bands', '1')]
    assert data.size == 364687