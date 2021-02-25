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

    p = ds.plot(('bands', '1'), height=height, width=width, center=rectangle_centre)
    p.set_log(('bands', '1'), False)
    p.set_cmap(('bands', '1'), 'B-W LINEAR')
    p.show()