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

class GeoRasterFieldInfo(FieldInfoContainer):
    known_other_fields = ()
    known_particle_fields = ()

    def __init__(self, ds, field_list):
        super().__init__(ds, field_list)
        self._create_field_map_aliases()
        self._create_highres_aliases()
        self._create_satellite_aliases()
        self._setup_geo_fields()

    def _create_field_map_aliases(self):
        """
        Read the field map file and create aliases.
        """

        if self.ds.field_map is None:
            return

        with open(self.ds.field_map, 'r') as f:
            field_map = yaml.load(f, Loader=yaml.FullLoader)

        for filename, fmap in field_map.items():
            for dfield, afield in fmap.items():
                my_field = f"{filename}_{dfield}"
                self._add_field_map_band_alias(my_field, afield)

    def _add_field_map_band_alias(self, band, afield):
        """
        Add an alias entry from the field map file.
        """
        units = afield.get("units", "")
        def my_field(field, data):
            return data.ds.arr(data["bands", band], units)
        self.add_field(
            (afield['field_type'], afield['field_name']),
            function=my_field, sampling_type="local",
            force_override=True,
            take_log=afield.get("take_log", True),
            units=units)

    def _create_highres_aliases(self):
        """
        Create band aliases using the highest resolution version.
        """

        fres = defaultdict(list)
        reg = re.compile(r"(.+)_(\d+)m$")
        for field in self:
            ftype, fname = field
            match = reg.search(fname)
            if match is None:
                continue
            band, res = match.groups()
            fres[(ftype, band)].append(int(res))

        for (ftype, band), bres in fres.items():
            fname = f"{band}_{min(bres)}m"
            self.alias((ftype, band), (ftype, fname))

    def _create_satellite_aliases(self):
        """
        Use the geo manager to create band aliases.
        """

        band_aliases = self.ds.index.geo_manager.band_aliases
        new_aliases = []

        for field in self:
            ftype, fname = field
            for alias in band_aliases.get(fname, ()):
                new_aliases.append(((ftype, alias), field))

        for new_alias in new_aliases:
            self.alias(*new_alias)

    def _setup_geo_fields(self):
        """
        Add geo-sciences derived fields.
        """

        # Area coverage of field
        def _area(field, data):
            return data["index", "dx"] *\
            data["index", "dy"]

        self.add_field(("index", "area"), function=_area,
            sampling_type="local",
            units="km**2")

        for ftype in self.ds.index.geo_manager.ftypes:

            # Normalised difference water index (NDWI)
            def _ndwi(field, data):
                green = data[ftype, "green"]
                nir = data[ftype, "nir"]
                return (green - nir) / (green + nir)

            self.add_field(
                (ftype, "NDWI"),
                function=_ndwi,
                sampling_type="local",
                take_log=False,
                units="")

            # Maximum chlorophyll index (MCI)
            def _mci(field, data):
                visible_red = data[ftype, "red"]
                red_edge_1 = data[ftype, "red_edge1"]
                red_edge_2 = data[ftype, "red_edge2"]
                return (red_edge_1  - visible_red) - \
                  0.53 * (red_edge_2 - visible_red)

            self.add_field(
                (ftype, "MCI"),
                function=_mci,
                sampling_type="local",
                take_log=False,
                units="")

            # Colored Dissolved Organic Matter (CDOM)
            def _cdom(field, data):
                visible_blue = data[ftype, "blue"]
                visible_green = data[ftype, "green"]
                return 8 * (visible_green / visible_blue)**(-1.4)

            self.add_field(
                (ftype, "CDOM"),
                function=_cdom,
                sampling_type="local",
                take_log=False,
                units="")

            # Enhanced Vegetation Index (EVI)
            def _evi(field, data):
                visible_blue = data[ftype, "blue"]
                visible_red = data[ftype, "red"]
                nir = data[ftype, "nir"]
                return 2.5 * (nir - visible_red) / \
                  ((nir + 6.0 * visible_red - 7.5 * visible_blue) + 1.0)

            self.add_field(
                (ftype, "EVI"),
                function=_evi,
                sampling_type="local",
                take_log=False,
                units="")

            # Normalised Difference Vegetation Index (NDVI)
            def _ndvi(field, data):
                visible_red = data[ftype, "red"]
                nir = data[ftype, "nir"]
                return (nir - visible_red) / (nir + visible_red)

            self.add_field(
                (ftype, "NDVI"),
                function=_ndvi,
                sampling_type="local",
                take_log=False,
                units="")

            # Landsat Temperature
            def _LS_temperature(field, data):
                thermal_infrared_1 = data[ftype, "tirs1"]
                return data.ds.arr((thermal_infrared_1 * 0.00341802 + 149), 'K')

            self.add_field(
                (ftype, "LS_temperature"),
                function=_LS_temperature,
                sampling_type="local",
                take_log=False,
                units="degC")
