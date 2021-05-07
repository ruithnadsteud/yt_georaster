import yt
import yt.extensions.geotiff

from yt_geotiff.data_structures import GeoTiffDataset
from yt_geotiff.testing import requires_file

s2_data = "Sentinel-2_sample_L2A/T30UVG_20200601T113331_B02_20m.jp2"

@requires_file(s2_data)
def test_load():
    ds = yt.load(s2_data)
    assert isinstance(ds, GeoTiffDataset)
