



def parse_gtif_attr(f, attr):
    """A Python3-safe function for getting geotiff attributes.
    If an attribute is supposed to be a string, this will return it as such.
    """
    val = f.meta.get(attr, None)
    if isinstance(val, bytes):
        return val.decode('utf8')
    else:
        return val