from collections import defaultdict
import re
import yaml

from yt.fields.field_info_container import \
    FieldInfoContainer

_sentinel2_fields = {
    "blue": "S2_B02",
    "green": "S2_B03",
    "red" : "S2_B04",
    "nir": "S2_B8A",
    "red_edge_1" : "S2_B05",
    "red_edge_2" : "S2_B06"
}

_landsat_fields = {
    "TIRS_1": "LS_B10"
}


class GeoTiffFieldInfo(FieldInfoContainer):
    known_other_fields = ()
    known_particle_fields = ()

    def __init__(self, ds, field_list):
        super().__init__(ds, field_list)

        if self.ds.field_map is not None:
            with open(self.ds.field_map, 'r') as f:
                fmap = yaml.load(f, Loader=yaml.FullLoader)

            for dfield, afield in fmap['field_map'].items():
                self.alias((fmap['field_type'], afield), ('bands', dfield))


class JPEG2000FieldInfo(FieldInfoContainer): # Now also used in RasterioGroupDataset(GeoTiffDataset)
    known_other_fields = ()
    known_particle_fields = ()

    def __init__(self, ds, field_list):
        super().__init__(ds, field_list)
        self._create_band_aliases()
        self._create_sentinel2_aliases()
        self._create_landsat_aliases()
        self._setup_geo_fields()

    def _create_band_aliases(self):
        """
        Create band aliases using the highest resolution version.
        """

        fres = defaultdict(list)
        reg = re.compile("(.+)_(\d+)m$")
        for field in self.field_list:
            ftype, fname = field
            match = reg.search(fname)
            if match is None:
                continue
            band, res = match.groups()
            fres[(ftype, band)].append(int(res))

        for (ftype, band), bres in fres.items():
            fname = f"{band}_{min(bres)}m"
            self.alias(("bands", band), (ftype, fname))

    def _create_sentinel2_aliases(self):
        """
        Create aliases of sentinel-2 bands to wavelength-based names.
        """

        # Note, we use "bands" as the alias field type because we
        # want to be able to define color fields for multiple satellites.
        for fname, band in _sentinel2_fields.items():
            self.alias(("bands", fname), ("bands", band))

    def _create_landsat_aliases(self):
        """
        Create aliases of sentinel-2 bands to wavelength-based names.
        """

        # Note, we use "bands" as the alias field type because we
        # want to be able to define color fields for multiple satellites.
        for fname, band in _landsat_fields.items():
            self.alias(("bands", fname), ("bands", band))

    def _setup_geo_fields(self):
        """
        Add geo-sciences derived fields.
        """
        # Normalised difference water index (NDWI)
        def _ndwi(field, data):
            green = data["bands", "green"]
            nir = data["bands", "nir"]
            return (green - nir) / (green + nir)

        self.add_field(
            ("bands", "NDWI"),
            function=_ndwi,
            sampling_type="local",
            units="")

        # Maximum chlorophyll index (MCI)
        def _mci(field, data):
            visible_red = data["bands", "red"]
            red_edge_1 = data["bands", "red_edge_1"]
            red_edge_2 = data["bands", "red_edge_2"]
            return (red_edge_1  - visible_red) - 0.53*(red_edge_2 - visible_red)

        self.add_field(
            ("bands", "MCI"),
            function=_mci,
            sampling_type="local",
            units="")

        # Colored Dissolved Organic Matter (CDOM)
        def _cdom(field, data):
            visible_blue = data["bands", "blue"]
            visible_green = data["bands", "green"]
            return 8* (visible_green/visible_blue)^(-1.4)

        self.add_field(
            ("bands", "CDOM"),
            function=_cdom,
            sampling_type="local",
            units="")

        # Landsat Temperature
        def _LS_temperature(field, data):
            thermal_infrared_1 = data["bands", "TIRS_1"]
            return data.ds.arr((thermal_infrared_1*0.00341802 + 149),'K')

        self.add_field(
            ("bands", "LS_temperature"),
            function=_LS_temperature,
            sampling_type="local",
            units="K")

        # Area coverage of field
        def _area(field, data):
            return data["index", "dx"] *\
            data["index", "dy"]

        self.add_field(("index", "area"), function=_area,
            sampling_type="local", units="km**2")

