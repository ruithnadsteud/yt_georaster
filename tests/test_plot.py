import glob
import os

import yt
from yt.config import ytcfg
import yt.extensions.georaster

from yt_georaster.testing import requires_file, TempDirTest

test_data_dir = ytcfg.get("yt", "test_data_dir")
S2_dir = "M2_Sentinel-2_test_data"
LS_dir = "Landsat-8_sample_L2"
poly_multi = "example_multi-feature_polygon/multi_feature_polygon.shp"


class GeoRasterPlotTest(TempDirTest):
    @requires_file(os.path.join(S2_dir, "T36MVE_20210315T075701_B01.jp2"))
    @requires_file(
        os.path.join(LS_dir, "LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF")
    )
    def test_plot_default(self):
        fns = glob.glob(os.path.join(test_data_dir, S2_dir, "*.jp2")) + glob.glob(
            os.path.join(test_data_dir, LS_dir, "*.TIF")
        )

        ds = yt.load(*fns)

        fields = [
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B1_30m"),
            ("T36MVE_20210315T075701", "S2_B06_20m"),
            ("T36MVE_20210315T075701", "NDWI"),
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "LS_temperature"),
        ]

        for field in fields:
            p = ds.plot(field)
            p.save()

    @requires_file(os.path.join(S2_dir, "T36MVE_20210315T075701_B01.jp2"))
    @requires_file(
        os.path.join(LS_dir, "LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF")
    )
    def test_plot_circle(self):
        fns = glob.glob(os.path.join(test_data_dir, S2_dir, "*.jp2")) + glob.glob(
            os.path.join(test_data_dir, LS_dir, "*.TIF")
        )

        ds = yt.load(*fns)

        fields = [
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B1_30m"),
            ("T36MVE_20210315T075701", "S2_B06_20m"),
            ("T36MVE_20210315T075701", "NDWI"),
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "LS_temperature"),
        ]

        circle = ds.circle(ds.domain_center, 0.25 * ds.domain_width[:2].min())
        for field in fields:
            p = ds.plot(field, data_source=circle)
            p.save()

    @requires_file(poly_multi)
    @requires_file(os.path.join(S2_dir, "T36MVE_20210315T075701_B01.jp2"))
    @requires_file(
        os.path.join(LS_dir, "LC08_L2SP_171060_20210227_20210304_02_T1_SR_B1.TIF")
    )
    def test_plot_polygon(self):
        fns = glob.glob(os.path.join(test_data_dir, LS_dir, "*.TIF")) + glob.glob(
            os.path.join(test_data_dir, S2_dir, "*.jp2")
        )

        ds = yt.load(*fns)

        fields = [
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "L8_B1_30m"),
            ("LC08_L2SP_171060_20210227_20210304_02_T1", "LS_temperature"),
        ]

        polygon = ds.polygon(os.path.join(test_data_dir, poly_multi))
        for field in fields:
            p = ds.plot(field, data_source=polygon)
            p.save()
