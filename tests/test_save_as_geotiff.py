import glob
from numpy.testing import assert_array_equal
import os

import yt
from yt.config import ytcfg
from yt.extensions.georaster import save_as_geotiff

from yt_georaster.testing import requires_file, TempDirTest

test_data_dir = ytcfg.get("yt", "test_data_dir")
S2_dir = "M2_Sentinel-2_test_data"
LS_dir = "Landsat-8_sample_L2"
poly_multi = "example_multi-feature_polygon/multi_feature_polygon.shp"


class GeoRasterSaveTest(TempDirTest):
    @requires_file(os.path.join(S2_dir, "S2A_MSIL1C_20210315T075701_N0209_R035_T36MVE_20210315T092856_B01.jp2"))
    @requires_file(
        os.path.join(LS_dir, "LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF")
    )
    def test_save_default(self):
        fns = glob.glob(os.path.join(test_data_dir, S2_dir, "*.jp2")) + glob.glob(
            os.path.join(test_data_dir, LS_dir, "*.TIF")
        )

        ds = yt.load(*fns)

        fields = [
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B1"),
            ("S2A_MSIL1C_20210315T075701_N0209_R035_T36MVE", "S2_B06"),
            ("S2A_MSIL1C_20210315T075701_N0209_R035_T36MVE", "NDWI"),
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "LS_temperature"),
        ]

        ds_fn, fm_fn = save_as_geotiff(
            ds, "my_data.tiff", fields=fields, dtype='float64'
        )
        ds_new = yt.load(ds_fn, field_map=fm_fn)

        for field in fields:
            ad = ds.all_data()
            ad_new = ds_new.all_data()
            assert_array_equal(
                ad[field],
                ad_new[field],
                err_msg=f"Saved data mismatch for field {field}.",
            )

    @requires_file(os.path.join(S2_dir, "S2A_MSIL1C_20210315T075701_N0209_R035_T36MVE_20210315T092856_B01.jp2"))
    @requires_file(
        os.path.join(LS_dir, "LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF")
    )
    def test_save_circle(self):
        fns = glob.glob(os.path.join(test_data_dir, S2_dir, "*.jp2")) + glob.glob(
            os.path.join(test_data_dir, LS_dir, "*.TIF")
        )

        ds = yt.load(*fns)

        circle = ds.circle(ds.domain_center, (10, "km"))
        fields = [
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B1"),
            ("S2A_MSIL1C_20210315T075701_N0209_R035_T36MVE", "S2_B06"),
            ("S2A_MSIL1C_20210315T075701_N0209_R035_T36MVE", "NDWI"),
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "LS_temperature"),
        ]
        ds_fn, fm_fn = save_as_geotiff(
            ds, "my_data.tiff", fields=fields, data_source=circle, dtype='float64'
        )
        ds_new = yt.load(ds_fn, field_map=fm_fn)

        circle_new = ds_new.circle(circle.center, circle.radius)

        for field in fields:
            assert_array_equal(
                circle[field],
                circle_new[field],
                err_msg=f"Saved data mismatch for field {field}.",
            )

    @requires_file(poly_multi)
    @requires_file(os.path.join(S2_dir, "S2A_MSIL1C_20210315T075701_N0209_R035_T36MVE_20210315T092856_B01.jp2"))
    @requires_file(
        os.path.join(LS_dir, "LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF")
    )
    def test_save_polygon(self):
        fns = glob.glob(os.path.join(test_data_dir, LS_dir, "*.TIF")) + glob.glob(
            os.path.join(test_data_dir, S2_dir, "*.jp2")
        )

        ds = yt.load(*fns)

        polygon = ds.polygon(os.path.join(test_data_dir, poly_multi))
        fields = [
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B1"),
            ("S2A_MSIL1C_20210315T075701_N0209_R035_T36MVE", "S2_B06"),
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "LS_temperature"),
        ]
        ds_fn, fm_fn = save_as_geotiff(
            ds, "my_data.tiff", fields=fields, data_source=polygon, dtype='float64'
        )
        ds_new = yt.load(ds_fn, field_map=fm_fn)

        polygon_new = ds_new.polygon(os.path.join(test_data_dir, poly_multi))

        for field in fields:
            assert_array_equal(
                polygon[field],
                polygon_new[field],
                err_msg=f"Saved data mismatch for field {field}.",
            )
