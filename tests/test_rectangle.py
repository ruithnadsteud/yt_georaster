import glob
from numpy.testing import assert_almost_equal, assert_equal
import os
import yt
import yt.extensions.geotiff

from yt.config import ytcfg

from yt_geotiff.testing import requires_file

test_data_dir = ytcfg.get("yt", "test_data_dir")
landsat = "Landsat-8_sample_L2/LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF"
s2 = "M2_Sentinel-2_test_data/T36MVE_20210315T075701_B01.jp2"

landsat_fns = glob.glob(os.path.join(test_data_dir, os.path.dirname(landsat), "*.TIF"))
s2_fns = glob.glob(os.path.join(test_data_dir, os.path.dirname(s2), "*.jp2"))

@requires_file(landsat)
@requires_file(s2)
def test_rectangle_ls():
    fns = landsat_fns + s2_fns
    ds = yt.load(*fns)
    # make center, radius not even number of pixels
    res = ds.resolution[0]
    center = ds.domain_center
    center[:2] += res / 3

    width = 1234.56 * res
    height = 2345.67 * res

    rectangle = ds.rectangle_from_center(center, width, height)

    rw = rectangle.right_edge - rectangle.left_edge
    a1 = rw[:2].prod()
    a2 = rectangle.quantities.total_quantity(("index", "area"))
    assert_almost_equal(a1/a2, 1, decimal=3)

    n1 = a1 / ds.resolution.prod()
    n2 = rectangle[('bands', 'LS_B1')].size
    assert_almost_equal(n1/n2, 1, decimal=3)

    n3 = rectangle[('bands', 'S2_B01')].size
    assert_almost_equal(n1/n3, 1, decimal=3)

    assert_equal(n2, n3)

@requires_file(landsat)
@requires_file(s2)
def test_rectangle_s2():
    fns = s2_fns + landsat_fns
    ds = yt.load(*fns)
    # make center, radius not even number of pixels
    res = ds.resolution[0]
    center = ds.domain_center
    center[:2] += res / 3

    width = 1234.56 * res
    height = 234.567 * res

    rectangle = ds.rectangle_from_center(center, width, height)

    rw = rectangle.right_edge - rectangle.left_edge
    a1 = rw[:2].prod()
    a2 = rectangle.quantities.total_quantity(("index", "area"))
    assert_almost_equal(a1/a2, 1, decimal=2)

    n1 = a1 / ds.resolution.prod()
    n2 = rectangle[('bands', 'LS_B1')].size
    assert_almost_equal(n1/n2, 1, decimal=2)

    n3 = rectangle[('bands', 'S2_B01')].size
    assert_almost_equal(n1/n3, 1, decimal=2)

    assert_equal(n2, n3)
