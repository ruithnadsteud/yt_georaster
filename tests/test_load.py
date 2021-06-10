import os
import yt
import yt.extensions.geotiff

from yt.config import ytcfg

from yt_geotiff.data_structures import GeoRasterDataset
from yt_geotiff.testing import requires_file

test_data_dir = ytcfg.get("yt", "test_data_dir")
land_use_data = os.path.join(
    test_data_dir, "200km_2p5m_N38E34/200km_2p5m_N38E34.TIF")
s2l1c_data = os.path.join(
    test_data_dir, "Sentinel-2_sample_L1C/T33UXP_20170501T100031_B02.jp2")
s2l2a_data = os.path.join(
    test_data_dir, "Sentinel-2_sample_L2A/T30UVG_20200601T113331_B02_20m.jp2")

@requires_file(land_use_data)
def test_load_geotiff():
    ds = yt.load(land_use_data)
    assert isinstance(ds, GeoRasterDataset)

@requires_file(s2l1c_data)
def test_load_S2_L1C():
    ds = yt.load(s2l1c_data)
    assert isinstance(ds, GeoRasterDataset)

@requires_file(s2l2a_data)
def test_load_S2_L2A():
    ds = yt.load(s2l2a_data)
    assert isinstance(ds, GeoRasterDataset)

@requires_file(land_use_data)
@requires_file(s2l1c_data)
@requires_file(s2l2a_data)
def test_load_group():
    fns = [land_use_data, s2l1c_data, s2l2a_data]
    ds = yt.load(*fns)
    assert isinstance(ds, GeoRasterDataset)
