"""
Unused classes and functions.
"""

import glob
import numpy as np
import os
import rasterio
import stat

from yt_georaster.data_structures import GeoRasterDataset, GeoRasterHierarchy


def s1_geocode(path, filename):
    """
    A quick example of handling transforms from gcps with rasterio.
    """

    """Main function."""
    # open the file
    with rasterio.open(os.path.join(path, filename)) as src:
        # meta = src.meta
        # array = src.read(1)
        gcps, crs = src.get_gcps()  # get crs and gcps
        transform = rasterio.transform.from_gcps(gcps)  # get transform

    # temp_file = "s1_"+polarisation+"_temp.tiff"
    # output_path = path_to_sen1_tiff.parent / temp_file

    return crs, transform
    # with rasterio.Env():
    #     # update the metadata
    #     new_meta = meta.copy()
    #     new_meta.update(
    #         crs=crs,
    #         transform=transform
    #     )
    #     #print("old: ", meta)
    #     #print("new: ", new_meta)
    #     # save to file
    #     with rasterio.open(output_path, "w", **new_meta) as dst:
    #         dst.write(array, 1)
    # reload that data to double check
    # with rasterio.open(output_path) as src:
    #    reloaded_meta = src.meta
    #    new_array = src.read(1)
    # does this change the data in anyway?
    # print("meta the same? ", reloaded_meta == new_meta)
    # print("data the same? ", (new_array == array).all())


def s1_polarisation(filename):
    if "vv" in filename:
        pol = "VV"
    elif "vh" in filename:
        pol = "VH"
    return pol


def s1_data_manager(path, filename):
    # Geocode S1 image
    s1_crs, s1_transform = s1_geocode(path, filename)
    field_label = ("bands", ("S1_" + s1_polarisation(filename)))
    # self.ds.parameters['crs'] = s1_crs
    # self.ds.parameters['crs'] = s1_transform
    return field_label


def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def coord_cal(xcell, ycell, transform):
    """Function to calculate the position of cell (xcell, ycell) in terms of
    longitude and latitude"""

    # note dy is -ve
    dx, rotx, xmin, roty, dy, ymax = transform[0:6]
    xp = xmin + dx / 2 + dx * xcell + rotx * ycell
    yp = ymax + dy / 2 + dy * ycell + roty * xcell

    return xp, yp


def left_aligned_coord_cal(xcell, ycell, transform):
    """Function to calculate the position of cell (xcell, ycell) in terms of
    distance from the top left corner using the longitude and latitude of
    the cell and the Earth radius to calculate an arc distance.
    This is required for yt as it needs to work with the distances rather than
    degrees.
    """

    dx, rotx, xmin, roty, dy, ymax = transform[0:6]
    xp, yp = coord_cal(xcell, ycell, transform)
    # convert to meters
    x_arc_dist = xp - xmin
    y_arc_dist = ymax - yp
    return x_arc_dist, y_arc_dist


def parse_awslandsat_metafile(filename, flatdict=True):
    """Function to read in metadata/parameter file and output it as a dict."""

    f = open(filename, "r")
    groupkeys = []

    data = {}

    while True:

        # Get next line from file
        line = f.readline().strip().replace('"', "").replace("\n", "")

        # if line is empty
        # end of file is reached
        if not line or line == "END":
            break
        key, value = line.split(" = ")

        # make sure we have all of value if it is an array
        while value.count("(") != value.count(")"):
            line = f.readline().strip().replace('"', "").replace("\n", "")
            value += line

        # save to data dictionary
        if key == "GROUP":
            groupkeys.append(value)
        elif key == "END_GROUP":
            groupkeys.pop()
        else:
            if flatdict:
                data[key] = value
            else:
                data[tuple(groupkeys + [key])] = value

    f.close()

    return data


class LandSatGeoTiffHierarchy(GeoRasterHierarchy):
    def _detect_output_fields(self):
        self.field_list = []
        self.ds.field_units = self.ds.field_units or {}

        # get list of filekeys
        filekeys = [s for s in self.ds.parameters.keys() if "FILE_NAME_BAND_" in s]
        files = [self.ds.data_dir + self.ds.parameters[filekey] for filekey in filekeys]

        group = "bands"
        for file in files:
            band = file.split(os.path.sep)[-1].split(".")[0].split("B")[1]
            field_name = (group, band)
            self.field_list.append(field_name)
            self.ds.field_units[field_name] = ""


class LandSatGeoTiffDataSet(GeoRasterDataset):
    _index_class = LandSatGeoTiffHierarchy

    def _parse_parameter_file(self):
        self.current_time = 0.0
        self.unique_identifier = int(os.stat(self.parameter_filename)[stat.ST_CTIME])

        # self.parameter_filename is the dir str
        if self.parameter_filename[-1] == "/":
            self.data_dir = self.parameter_filename
            self.mtlfile = (
                self.data_dir
                + self.parameter_filename[:-1].split(os.path.sep)[-1]
                + "_MTL.txt"
            )
            self.angfile = (
                self.data_dir
                + self.parameter_filename[:-1].split(os.path.sep)[-1]
                + "_ANG.txt"
            )
        else:
            self.data_dir = self.parameter_filename + "/"
            self.mtlfile = (
                self.data_dir
                + self.parameter_filename.split(os.path.sep)[-1]
                + "_MTL.txt"
            )
            self.angfile = (
                self.data_dir
                + self.parameter_filename.split(os.path.sep)[-1]
                + "_ANG.txt"
            )
        # load metadata files
        self.parameters.update(parse_awslandsat_metafile(self.angfile))
        self.parameters.update(parse_awslandsat_metafile(self.mtlfile))

        # get list of filekeys
        filekeys = [s for s in self.parameters.keys() if "FILE_NAME_BAND_" in s]
        files = [self.data_dir + self.parameters[filekey] for filekey in filekeys]
        self.parameters["count"] = len(filekeys)
        # take the parameters displayed in the filename
        self._parse_landsat_filename_data(
            self.parameter_filename.split(os.path.sep)[-1]
        )

        for filename in files:
            band = filename.split(os.path.sep)[-1].split(".")[0].split("B")[1]
            # filename = self.parameters[band]
            with rasterio.open(filename, "r") as f:
                for key in f.meta.keys():
                    # skip key if already defined as a parameter
                    if key in self.parameters.keys():
                        continue
                    v = f.meta[key]
                    # if key == "con_args":
                    #     v = v.astype("str")
                    self.parameters[(band, key)] = v
                self._with_parameter_file_open(f)
                # self.parameters['transform'] = f.transform

            if band == "1":
                self.domain_dimensions = np.array(
                    [
                        self.parameters[(band, "height")],
                        self.parameters[(band, "width")],
                        1,
                    ],
                    dtype=np.int32,
                )
                self.dimensionality = 3
                rightedge_xy = left_aligned_coord_cal(
                    self.domain_dimensions[0],
                    self.domain_dimensions[1],
                    self.parameters[(band, "transform")],
                )

                self.domain_left_edge = self.arr(
                    np.zeros(self.dimensionality, dtype=np.float64), "m"
                )
                self.domain_right_edge = self.arr(
                    [rightedge_xy[0], rightedge_xy[1], 1], "m", dtype=np.float64
                )

    def _parse_landsat_filename_data(self, filename):
        """
        "LXSS_LLLL_PPPRRR_YYYYMMDD_yyyymmdd_CC_TX"
        L = Landsat
        X = Sensor ("C"=OLI/TIRS combined,
                    "O"=OLI-only, "T"=TIRS-only,
                    E"=ETM+, "T"="TM, "M"=MSS)
        SS = Satellite ("07"=Landsat 7, "08"=Landsat 8)
        LLLL = Processing correction level (L1TP/L1GT/L1GS)
        PPP = WRS path
        RRR = WRS row
        YYYYMMDD = Acquisition year, month, day
        yyyymmdd - Processing year, month, day
        CC = Collection number (01, 02, …)
        TX = Collection category ("RT"=Real-Time, "T1"=Tier 1,
                                  "T2"=Tier 2)
        """
        sensor = {
            "C": "OLI&TIRS combined",
            "O": "OLI-only",
            # "T": "TIRS-only", commenting out to fix flake8 error
            "E": "ETM+",
            "T": "TM",
            "M": "MSS",
        }
        satellite = {"07": "Landsat 7", "08": "Landsat 8"}
        category = {"RT": "Real-Time", "T1": "Tier 1", "T2": "Tier 2"}

        self.parameters["sensor"] = sensor[filename[1]]
        self.parameters["satellite"] = satellite[filename[2:4]]
        self.parameters["level"] = filename[5:9]
        self.parameters["wrs"] = {"path": filename[10:13], "row": filename[13:16]}
        self.parameters["acquisition_time"] = {
            "year": filename[17:21],
            "month": filename[21:23],
            "day": filename[23:25],
        }
        self.parameters["processing_time"] = {
            "year": filename[26:30],
            "month": filename[30:32],
            "day": filename[32:34],
        }
        self.parameters["collection"] = {
            "number": filename[35:37],
            "category": category[filename[38:40]],
        }

    @classmethod
    def _is_valid(self, *args, **kwargs):
        if not os.path.isdir(args[0]):
            return False
        if (
            len(glob.glob(args[0] + "/L*_ANG.txt")) != 1
            and len(glob.glob(args[0] + "/L*_MTL.txt")) != 1
        ):
            return False
        try:
            file = glob.glob(args[0] + "/*.TIF")[0]  # open the first file
            with rasterio.open(file, "r") as f:
                # data_type = parse_gtif_attr(f, "dtype")
                driver_type = f.meta["driver"]
                # if data_type == "uint16":
                #     return True
                if driver_type == "GTiff":
                    return True
        except:
            pass
        return False
