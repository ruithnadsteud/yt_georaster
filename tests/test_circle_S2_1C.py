import yt
import yt.extensions.geotiff
import yt.geometry.selection_routines as selector_shape

from yt.data_objects.selection_objects.spheroids import YTSphere

from yt_geotiff.testing import requires_file

s2_data = "Sentinel-2_sample_L1C/T33UXP_20170501T100031_B02.jp2"

@requires_file(s2_data)
def test_circle():
    ds = yt.load(s2_data)
    radius = ds.quan(5.,'km')
    circle_centre = ds.arr([453725,9974362],'m')
    circular_yt_container = ds.circle(circle_centre, radius)
    circular_yt_container[('bands', 'S2_B02_10m')]
    assert isinstance(circular_yt_container, YTSphere)