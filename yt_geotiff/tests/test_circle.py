import yt
import yt.extensions.geotiff
import yt.geometry.selection_routines as selector_shape

from yt_geotiff.data_structures import GeoTiffDataset
from yt_geotiff.testing import requires_file

land_use_data = "200km_2p5m_N38E34/200km_2p5m_N38E34.TIF"

@requires_file(land_use_data)
def test_circle():
    ds = yt.load(land_use_data)
    radius = ds.arr(1000.,'m')
    circle_centre = ds.arr([3501279,3725080],'m')
    circular_yt_container = ds.circle(circle_centre, radius)
    circular_yt_container[('bands','1')]
    assert isinstance(circular_yt_container.selector,selector_shape.SphereSelector)
