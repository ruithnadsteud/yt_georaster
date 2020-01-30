
import yt
import yt.extensions.geotiff


# using example from AWS Landsat:
# http://landsat-pds.s3.amazonaws.com/c1/L8/042/034/..
# ..LC08_L1TP_042034_20170616_20170629_01_T1/..
# ..LC08_L1TP_042034_20170616_20170629_01_T1_B4.TIF
filename = 'example.tif'
# filename = '~/Downloads/F182013.v4/F182013.v4c_web.stable_lights.avg_vis.tif'

ds = yt.load(filename)
print ds.field_list
print ds.parameters
ds.print_stats()

# print ds.unit_registry

slc = yt.SlicePlot(ds, 'z', '1')
slc.save()