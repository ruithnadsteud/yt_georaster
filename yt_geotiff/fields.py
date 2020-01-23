"""
geotiff-specific fields



"""


from yt.fields.field_info_container import \
    FieldInfoContainer


class YTGTiffFieldInfo(FieldInfoContainer):
    known_other_fields = [("1", ("", ["band_1"], "Band 1 (Arbitrary Units)"))
    ]

    known_particle_fields = (
    )