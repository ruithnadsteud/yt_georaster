GDAL_DATA= 'C:/Users/arevi/anaconda3/envs/yt-git/Library/share/gdal/gcs.csv'
import yt
import yt.extensions.geotiff
#import gdal
import numpy as np
from matplotlib.pyplot import imshow, show, colorbar
import pdb # debugging library



filename = (r'C:\Users\arevi\OneDrive\yt_project\yt_geotiff-master\example_notebooks\sample_s2\S2A_MSIL2A_20200601T113331_N0214_R080_T30UVG_20200601T123416_20m.tif')

yaml_file = ('C:/Users/arevi/OneDrive/yt_project/yt_geotiff-master/yt_geotiff/data.yaml')

# Load 
ds = yt.load(filename, field_map=yaml_file)

txt = 2 #input("Read image into cache: yes (1) or no (2)")


#-----------------------------------------------------------------------------
#pdb.set_trace()

if txt == str(1):
       # Convert to grid and read to cache-------------------------------------------
       grid_area = ds.index.grids[0]
       grid_area[('sentinel2', 'B03')]

txt_plot1 = input("Selector type: sphere (1), box (2) or region (3)")



if txt_plot1 == str(1):
       
       ### -------------------- define by sphere -------------------------------- ###
       radius = (10., 'km')
       center = [35000., 47000.]
       
       aoi_centroid = yt.YTArray([center[0], center[1], ds.domain_width[2]/2], 'm')
       
       aoi = ds.sphere(aoi_centroid, radius)
       
       aoi['sentinel2', 'B03']
       ### ---------------------------------------------------------------------- ###

elif txt_plot1 == str(2):

       ### -------------------- define by box ----------------------------------- ###
       left = ds.arr([25000, 25000, ds.domain_left_edge[2].to('m')], 'm')
       right = ds.arr([45000, 45000, ds.domain_right_edge[2].to('m')], 'm')
       
       aoi = ds.box(left, right)

       aoi['sentinel2', 'B03']
       ### ---------------------------------------------------------------------- ###

elif txt_plot1 == str(3):
       ### -------------------- define by region------------------------------ ###
       center = [35000., 47000.]
       left = ds.arr([25000, 25000, ds.domain_left_edge[2].to('m')], 'm')
       right = ds.arr([45000, 45000, ds.domain_right_edge[2].to('m')], 'm')

       aoi = ds.region(center, left, right)
       
       aoi['sentinel2', 'B03']
       ### -------------------------------------------------------------------- ###

