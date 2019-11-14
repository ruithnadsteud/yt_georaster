"""
geotiff-specific fields



"""


from yt.fields.field_info_container import \
    FieldInfoContainer


class YTGTiffFieldInfo(FieldInfoContainer):
    known_other_fields = (("intensity", ("", ["intensity", "counts", "value"], None))
    )

    known_particle_fields = (
    )