import glob
from numpy.testing import assert_array_equal
import os

import yt
from yt.config import ytcfg
from yt.extensions.geotiff import save_as_geotiff

from yt_geotiff.testing import \
    requires_file, \
    TempDirTest

test_data_dir = ytcfg.get("yt", "test_data_dir")
S2_dir = "M2_Sentinel-2_test_data"
LS_dir = "Landsat-8_sample_L2"

class GeoTiffSaveTest(TempDirTest):
    @requires_file(os.path.join(S2_dir, "T36MVE_20210315T075701_B01.jp2"))
    @requires_file(os.path.join(LS_dir, "LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF"))
    def test_save_default(self):
        fns = glob.glob(os.path.join(test_data_dir, S2_dir, "*.jp2")) + \
          glob.glob(os.path.join(test_data_dir, LS_dir, "*.TIF"))

        ds = yt.load(*fns)

        ds_fn, fm_fn = save_as_geotiff(ds, "my_data.tif")
        ds_new = yt.load(ds_fn, field_map=fm_fn)

        for field in ds.field_list:
            ad = ds.all_data()
            ad_new = ds_new.all_data()
            assert_array_equal(
                ad[field], ad_new[field],
                err_msg=f"Saved data mismatch for field {field}.")

    @requires_file(os.path.join(S2_dir, "T36MVE_20210315T075701_B01.jp2"))
    @requires_file(os.path.join(LS_dir, "LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF"))
    def test_save_sphere(self):
        fns = glob.glob(os.path.join(test_data_dir, S2_dir, "*.jp2")) + \
          glob.glob(os.path.join(test_data_dir, LS_dir, "*.TIF"))

        ds = yt.load(*fns)

        circle = ds.circle(ds.domain_center, (10, 'km'))
        fields = [("bands", "LS_B1_30m"),
                  ("bands", "S2_B06_20m"),
                  ("band_ratios", "S2_NDWI"),
                  ("variables", "LS_temperature")]
        ds_fn, fm_fn = save_as_geotiff(
            ds, "my_data.tiff",
            fields=fields, data_source=circle)
        ds_new = yt.load(ds_fn, field_map=fm_fn)

        left_edge, right_edge = circle.get_bbox()
        dle = ds.domain_left_edge.to("code_length")
        dre = ds.domain_right_edge.to("code_length")
        left_edge.clip(dle, dre, out=left_edge)
        right_edge.clip(dle, dre, out=right_edge)
        bbox = ds.box(left_edge, right_edge)

        for field in fields:
            ad_new = ds_new.all_data()
            assert_array_equal(
                bbox[field], ad_new[field],
                err_msg=f"Saved data mismatch for field {field}.")
