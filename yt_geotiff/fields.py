import yaml

from yt.fields.field_info_container import \
    FieldInfoContainer

class GeoTiffFieldInfo(FieldInfoContainer):
    known_other_fields = ()

    known_particle_fields = ()

    def __init__(self, ds, field_list):
        super(GeoTiffFieldInfo, self).__init__(ds, field_list)

        if self.ds.field_map is not None:
            with open(self.ds.field_map, 'r') as f:
                fmap = yaml.load(f, Loader=yaml.FullLoader)

            for dfield, afield in fmap['field_map'].items():
                self.alias((fmap['field_type'], afield), ('bands', dfield))
