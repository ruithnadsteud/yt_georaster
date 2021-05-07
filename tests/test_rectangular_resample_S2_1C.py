import yt
import yt.extensions.geotiff

from yt.data_objects.selection_objects.region import YTRegion

from yt_geotiff.testing import get_path, requires_file

s2_data_1 = "M2_Sentinel-2_test_data/T36MVE_20210315T075701_B02.jp2"
s2_data_2 = "M2_Sentinel-2_test_data/T36MVE_20210315T075701_B01.jp2"
@requires_file(s2_data_1)
@requires_file(s2_data_2)
def test_rectangular():
    fns = get_path([s2_data_1, s2_data_2])
    ds = yt.load(*fns)
    width = ds.quan(20., 'km')
    height = ds.quan(10.,'km')
    rectangle_centre = ds.arr([471696,9989860],'m')
    rectangular_yt_container = ds.rectangle_from_center(rectangle_centre,width,height)
    rectangular_yt_container[('bands', 'S2_B01')]
    assert isinstance(rectangular_yt_container, YTRegion)
