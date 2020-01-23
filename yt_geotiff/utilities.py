"""
Utility functions for yt_geotiff.



"""
import numpy as np

def coord_cal(xcell, ycell, transform):
    """Function to calculate the position of cell (xcell, ycell) in terms of
    longitude and latitude"""


    # note dy is -ve
    dx, rotx, xmin, roty, dy, ymax = transform[0:6]
    xp = xmin + dx/2 + dx*xcell + rotx*ycell
    yp = ymax + dy/2 + dy*ycell + roty*xcell

    return xp, yp

def left_aligned_coord_cal(xcell, ycell, transform):
    """Function to calculate the position of cell (xcell, ycell) in terms of
    distance from the top left corner using the longitude and latitude of
    the cell and the Earth radius to calculate an arc distance.
    This is required for yt as it needs to work with the distances rather than
    degrees.
    """

    # rEarth = 6.371e6 # metres
    # print transform[0:6]

    dx, rotx, xmin, roty, dy, ymax = transform[0:6]
    xp, yp = coord_cal(xcell, ycell, transform)
    # convert to meters
    x_arc_dist = (xp - xmin)# * np.pi/180. * rEarth
    y_arc_dist = (ymax - yp)# * np.pi/180. * rEarth # (0, 0) corresponds to
                                                  # (xmin, ymax)
    return x_arc_dist, y_arc_dist

