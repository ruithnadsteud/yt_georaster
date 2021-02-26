import yt
import yt.extensions.geotiff
import yt.geometry.selection_routines as selector_shape

from yt_geotiff.data_structures import GeoTiffDataset
from yt_geotiff.testing import requires_file

land_use_data = "200km_2p5m_N38E34/200km_2p5m_N38E34.TIF"

@requires_file(land_use_data)
def test_rectangular():
    ds = yt.load(land_use_data)
    width = ds.arr(2000., 'm')
    height = ds.arr(2000.,'m') 
    rectangle_centre = ds.arr([3501279,3725080],'m')

    rectangular_yt_container = ds.rectangle_from_center(rectangle_centre,width,height)
    rectangular_yt_container[('bands','1')]
    
    assert isinstance(rectangular_yt_container.selector,selector_shape.rectangle)