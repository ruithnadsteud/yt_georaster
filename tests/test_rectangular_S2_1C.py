import yt
import yt.extensions.geotiff

from yt.data_objects.selection_objects.region import YTRegion

from yt_geotiff.testing import requires_file

s2_data = "Sentinel-2_sample_L1C/T33UXP_20170501T100031_B02.jp2"

@requires_file(s2_data)
def test_rectangular():
    ds = yt.load(s2_data)
    width = ds.quan(5., 'km')
    height = ds.quan(5.,'km')
    rectangle_centre = ds.arr([453725,9974362],'m')
    rectangular_yt_container = ds.rectangle_from_center(rectangle_centre,width,height)
    rectangular_yt_container[('bands', 'B02')]
    assert isinstance(rectangular_yt_container, YTRegion)
