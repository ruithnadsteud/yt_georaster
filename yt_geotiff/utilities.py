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


def parse_awslandsat_metafile(filename):
    """Function to read in metadata/parameter file and output it as a dict.
    """

    f = open(filename, 'r') 
    groupkeys = []

    data = {}
    flatdata = {}

    while True: 

        # Get next line from file 
        line = f.readline().strip().replace('"', '').replace('\n', '')

        # if line is empty 
        # end of file is reached 
        if not line or line == 'END': 
            break
        # print line.split('=')
        key, value = line.split(' = ')

        # make sure we have all of value if it is an array
        while value.count('(') != value.count(')'):
            line = f.readline().strip().replace('"', '').replace('\n', '')
            value += line

        # save to data dictionary
        if key == 'GROUP':
            groupkeys.append(value)
        elif key == 'END_GROUP':
            groupkeys.pop()
        else:
            data[tuple(groupkeys + [key])] = value
            flatdata[key] = value

    f.close() 

    return data, flatdata

