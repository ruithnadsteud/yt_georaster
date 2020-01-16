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

def coord_arc_dist_cal(xcell, ycell, transform, height):
    """Function to calculate the position of cell (xcell, ycell) in terms of
    distance from the bottom left corner using the longitude and latitude of
    the cell and the Earth radius to calculate an arc distance. Need the total
    number cells in the y direction to calculate the adjusted ymax.

    This is required for yt as it needs to work with the distances rather than
    degrees.
    """

    rEarth = 6.371e6 # metres
    print transform[0:6]

    dx, rotx, xmin, roty, dy, ymax = transform[0:6]
    ymin = ymax + height * dy # remember dy is negative
    xp, yp = coord_cal(xcell, ycell, transform)
    # convert to meters
    x_arc_dist = (xp - xmin)* np.pi/180. * rEarth
    y_arc_dist = (yp - ymin)* np.pi/180. * rEarth

    return x_arc_dist, y_arc_dist

