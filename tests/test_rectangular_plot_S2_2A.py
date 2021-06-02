import yt
import yt.extensions.geotiff

from yt_geotiff.testing import requires_file

s2_data = "Sentinel-2_sample_L2A/T30UVG_20200601T113331_B02_20m.jp2"

@requires_file(s2_data)
def test_plot():
    ds = yt.load(s2_data)
    width = ds.quan(500., 'm')
    height = ds.quan(500.,'m')
    rectangle_centre = ds.arr([488012,6199162],'m')
    p = ds.plot(('bands','S2_B02_10m'), height=height, width=width, center=rectangle_centre)
    p.set_log(('bands','S2_B02_10m'), False)
    p.set_cmap(('bands','S2_B02_10m'), 'B-W LINEAR')