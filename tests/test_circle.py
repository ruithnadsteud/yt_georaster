import glob
import numpy as np
from numpy.testing import assert_almost_equal, assert_equal
import os
import yt
import yt.extensions.geotiff

from yt.config import ytcfg

from yt_geotiff.testing import requires_file

test_data_dir = ytcfg.get("yt", "test_data_dir")
landuse = "200km_2p5m_N38E34/200km_2p5m_N38E34.TIF"
landsat = "Landsat-8_sample_L2/LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF"
s2 = "M2_Sentinel-2_test_data/T36MVE_20210315T075701_B01.jp2"

landsat_fns = glob.glob(os.path.join(test_data_dir, os.path.dirname(landsat), "*.TIF"))
s2_fns = glob.glob(os.path.join(test_data_dir, os.path.dirname(s2), "*.jp2"))

@requires_file(landuse)
def test_circle_lu():
    ds = yt.load(landuse)
    # make center, radius not even number of pixels
    res = ds.resolution[0]
    center = ds.domain_center
    center[:2] += res / 3
    radius = res * 1234.567
    circle = ds.circle(center, radius)

    a1 = np.pi * circle.radius**2
    a2 = circle.quantities.total_quantity(("index", "area"))
    assert_almost_equal(a1/a2, 1, decimal=5)

    # check number of points in sufficiently large circle
    n1 = a1 / ds.resolution.prod()
    n2 = circle[('200km_2p5m_N38E34', 'band_1')].size
    assert_almost_equal(n1/n2, 1, decimal=5)

@requires_file(landsat)
@requires_file(s2)
def test_circle_ls():
    fns = landsat_fns + s2_fns
    ds = yt.load(*fns)
    # make center, radius not even number of pixels
    res = ds.resolution[0]
    center = ds.domain_center
    center[:2] += res / 3
    radius = ds.domain_width[:2].min() * 0.25 + res / 2
    circle = ds.circle(center, radius)

    # check number of points in sufficiently large circle
    n1 = np.pi * circle.radius**2 / ds.resolution.prod()
    n2 = circle[('LC08_L2SP_171060_20210227_20210304_02_T1', 'L8_B1')].size
    assert_almost_equal(n1/n2, 1, decimal=5)

    n3 = circle[('T36MVE_20210315T075701', 'S2_B01')].size
    assert_almost_equal(n1/n3, 1, decimal=5)

    assert_equal(n2, n3)

@requires_file(landsat)
@requires_file(s2)
def test_circle_s2():
    fns = s2_fns + landsat_fns
    ds = yt.load(*fns)
    # make center, radius not even number of pixels
    res = ds.resolution[0]
    center = ds.domain_center
    center[:2] += res / 3
    radius = ds.domain_width[:2].min() * 0.25 + res / 2
    circle = ds.circle(center, radius)

    # check number of points in sufficiently large circle
    n1 = np.pi * circle.radius**2 / ds.resolution.prod()
    n2 = circle[('LC08_L2SP_171060_20210227_20210304_02_T1', 'L8_B1')].size

    # lower decimal precision since this sphere is smaller
    assert_almost_equal(n1/n2, 1, decimal=3)

    n3 = circle[('T36MVE_20210315T075701', 'S2_B01')].size
    assert_almost_equal(n1/n3, 1, decimal=3)

    assert_equal(n2, n3)
