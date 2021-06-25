from collections import defaultdict
import re

from yt.fields.field_info_container import \
    FieldInfoContainer

class GeoRasterFieldInfo(FieldInfoContainer):
    known_other_fields = ()
    known_particle_fields = ()

    def __init__(self, ds, field_list):
        super().__init__(ds, field_list)
        self._create_highres_aliases()
        self._create_satellite_aliases()
        self._setup_geo_fields()

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
                ftype = field.name[0]
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
                ftype = field.name[0]
                red = data[ftype, "red"]
                red_edge_1 = data[ftype, "red_edge_1"]
                red_edge_2 = data[ftype, "red_edge_2"]
                return (red_edge_1  - red) - \
                  0.53 * (red_edge_2 - red)

            self.add_field(
                (ftype, "MCI"),
                function=_mci,
                sampling_type="local",
                take_log=False,
                units="")

            # Colored Dissolved Organic Matter (CDOM)
            def _cdom(field, data):
                ftype = field.name[0]
                blue = data[ftype, "blue"]
                green = data[ftype, "green"]
                return 8 * (green / blue)**(-1.4)

            self.add_field(
                (ftype, "CDOM"),
                function=_cdom,
                sampling_type="local",
                take_log=False,
                units="")

            # Enhanced Vegetation Index (EVI)
            def _evi(field, data):
                ftype = field.name[0]
                blue = data[ftype, "blue"]
                red = data[ftype, "red"]
                nir = data[ftype, "nir"]
                return 2.5 * (nir - red) / \
                  ((nir + 6.0 * red - 7.5 * blue) + 1.0)

            self.add_field(
                (ftype, "EVI"),
                function=_evi,
                sampling_type="local",
                take_log=False,
                units="")

            # Normalised Difference Vegetation Index (NDVI)
            def _ndvi(field, data):
                ftype = field.name[0]
                red = data[ftype, "red"]
                nir = data[ftype, "nir"]
                return (nir - red) / (nir + red)

            self.add_field(
                (ftype, "NDVI"),
                function=_ndvi,
                sampling_type="local",
                take_log=False,
                units="")

            # Landsat Temperature
            def _LS_temperature(field, data):
                ftype = field.name[0]
                thermal_infrared_1 = data[ftype, "tirs_1"]
                return data.ds.arr((thermal_infrared_1 * 0.00341802 + 149), 'K')

            self.add_field(
                (ftype, "LS_temperature"),
                function=_LS_temperature,
                sampling_type="local",
                take_log=False,
                units="degC")
