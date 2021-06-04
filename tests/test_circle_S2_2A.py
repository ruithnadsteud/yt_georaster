import yt
import yt.extensions.geotiff
import yt.geometry.selection_routines as selector_shape

from yt.data_objects.selection_objects.spheroids import YTSphere

from yt_geotiff.testing import requires_file

s2_data = "Sentinel-2_sample_L2A/T30UVG_20200601T113331_B02_20m.jp2"

@requires_file(s2_data)
def test_circle():
    ds = yt.load(s2_data)
    radius = ds.quan(500.,'m')
    circle_centre = ds.arr([488012,6199162],'m')
    circular_yt_container = ds.circle(circle_centre, radius)
    circular_yt_container[('bands', 'B02')]
    assert isinstance(circular_yt_container, YTSphere)