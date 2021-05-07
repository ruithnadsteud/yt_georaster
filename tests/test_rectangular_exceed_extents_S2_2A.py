import yt
import yt.extensions.geotiff

from yt.data_objects.selection_objects.region import YTRegion

from yt_geotiff.testing import requires_file

s2_data = "Sentinel-2_sample_L2A/T30UVG_20200601T113331_B02_20m.jp2"

@requires_file(s2_data)
def test_rectangular_exceed_extents():
    ds = yt.load(s2_data)
    width = ds.quan(2000., 'm')
    height = ds.quan(2000.,'m')
    rectangle_centre = ds.arr([487885,6199791],'m')
    rectangular_yt_container = ds.rectangle_from_center(rectangle_centre, width, height)
    rectangular_yt_container[('bands','B02_20m')]
    assert isinstance(rectangular_yt_container, YTRegion)
