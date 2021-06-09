import yt
import yt.extensions.geotiff
import yt.geometry.selection_routines as selector_shape

from yt.data_objects.selection_objects.spheroids import YTSphere

from yt_geotiff.testing import requires_file

land_use_data = "200km_2p5m_N38E34/200km_2p5m_N38E34.TIF"
s2l1c_data = "Sentinel-2_sample_L1C/T33UXP_20170501T100031_B02.jp2"
s2l2a_data = "Sentinel-2_sample_L2A/T30UVG_20200601T113331_B02_20m.jp2"

@requires_file(land_use_data)
def test_circle():
    ds = yt.load(land_use_data)
    radius = ds.quan(1000.,'m')
    circle_centre = ds.arr([3501279,3725080],'m')
    circular_yt_container = ds.circle(circle_centre, radius)
    circular_yt_container[('bands','200km_2p5m_N38E34_1')]
    assert isinstance(circular_yt_container, YTSphere)

@requires_file(s2l1c_data)
def test_circle_S2L1C():
    ds = yt.load(s2l1c_data)
    radius = ds.quan(5.,'km')
    circle_centre = ds.arr([453725,9974362],'m')
    circular_yt_container = ds.circle(circle_centre, radius)
    circular_yt_container[('bands', 'S2_B02')]
    assert isinstance(circular_yt_container, YTSphere)

@requires_file(s2l2a_data)
def test_circle_S2L2A():
    ds = yt.load(s2l2a_data)
    radius = ds.quan(500.,'m')
    circle_centre = ds.arr([488012,6199162],'m')
    circular_yt_container = ds.circle(circle_centre, radius)
    circular_yt_container[('bands', 'S2_B02')]
    assert isinstance(circular_yt_container, YTSphere)
