import glob
from numpy.testing import assert_equal
import os
import yt
import yt.extensions.georaster

from yt.config import ytcfg

from yt_georaster.testing import requires_file

test_data_dir = ytcfg.get("yt", "test_data_dir")
landsat = "Landsat-8_sample_L2/LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF"
s2 = "M2_Sentinel-2_test_data/S2A_MSIL1C_20210315T075701_N0209_R035_T36MVE_20210315T092856_B01.jp2"
poly_multi = "example_multi-feature_polygon/multi_feature_polygon.shp"
poly_single = "example_polygon_mabira_forest/mabira_forest.shp"

landsat_fns = glob.glob(os.path.join(test_data_dir, os.path.dirname(landsat), "*.TIF"))
s2_fns = glob.glob(os.path.join(test_data_dir, os.path.dirname(s2), "*.jp2"))


@requires_file(landsat)
@requires_file(s2)
@requires_file(poly_single)
def test_polygon_single():
    fns = landsat_fns + s2_fns
    ds = yt.load(*fns)

    polygon = ds.polygon(os.path.join(test_data_dir, poly_single))
    assert_equal(
        polygon["LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B10"].size, 368007
    )
    assert_equal(polygon["S2A_MSIL1C_20210315T075701_N0209_R035_T36MVE", "S2_B10"].size, 368007)


@requires_file(landsat)
@requires_file(s2)
@requires_file(poly_multi)
def test_polygon_multi():
    fns = landsat_fns + s2_fns
    ds = yt.load(*fns)

    polygon = ds.polygon(os.path.join(test_data_dir, poly_multi))
    assert_equal(
        polygon["LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B10"].size, 551609
    )
    assert_equal(polygon["S2A_MSIL1C_20210315T075701_N0209_R035_T36MVE", "S2_B10"].size, 551609)
