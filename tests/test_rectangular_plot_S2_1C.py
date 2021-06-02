import yt
import yt.extensions.geotiff

from yt_geotiff.testing import requires_file

s2_data = "Sentinel-2_sample_L1C/T33UXP_20170501T100031_B02.jp2"

@requires_file(s2_data)
def test_plot():
    ds = yt.load(s2_data)
    width = ds.quan(5., 'km')
    height = ds.quan(5.,'km')
    rectangle_centre = ds.arr([453725,9974362],'m')
    p = ds.plot(('bands', 'S2_B02_10m'), height=height, width=width, center=rectangle_centre)
    p.set_log(('bands', 'S2_B02_10m'), False)
    p.set_cmap(('bands', 'S2_B02_10m'), 'B-W LINEAR')