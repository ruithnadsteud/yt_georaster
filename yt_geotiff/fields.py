from collections import defaultdict
import re
import yaml

from yt.fields.field_info_container import \
    FieldInfoContainer

_sentinel2_fields = {
    "green": "B03",
    "nir": "B8A"
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


class JPEG2000FieldInfo(FieldInfoContainer):
    known_other_fields = ()
    known_particle_fields = ()

    def __init__(self, ds, field_list):
        super().__init__(ds, field_list)
        self._create_band_aliases()
        self._create_sentinel2_aliases()
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

    def _setup_geo_fields(self):
        """
        Add geo-sciences derived fields.
        """

        def _ndwi(field, data):
            green = data["bands", "green"]
            nir = data["bands", "nir"]
            return (green - nir) / (green + nir)

        self.add_field(
            ("bands", "ndwi"),
            function=_ndwi,
            sampling_type="local",
            units="")
