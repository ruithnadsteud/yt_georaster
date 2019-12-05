"""
Utility functions for yt_geotiff.



"""

def coord_cal(xcell, ycell, transform):


    # note dy is -ve
    dx, rotx, xmin, roty, dy, ymax = transform
    xp = xmin + dx/2 + dx*xcell + rotx*ycell
    yp = ymax + dy/2 + dy*ycell + roty*xcell

    return xp, yp

