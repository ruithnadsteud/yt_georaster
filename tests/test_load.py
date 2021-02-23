import yt
import yt.extensions.geotiff

from yt_geotiff.data_structures import GeoTiffDataset
from yt_geotiff.testing import requires_file

land_use_data = "200km_2p5m_N38E34/200km_2p5m_N38E34.TIF"

@requires_file(land_use_data)
def test_load():
    ds = yt.load(land_use_data)
    assert isinstance(ds, GeoTiffDataset)
