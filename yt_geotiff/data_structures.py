"""
Data structures for yt_geotiff.



"""

from .fields import \
    YTGTiffFieldInfo
from .utilities import \
    parse_gtif_attr


from yt.data_objects.static_output import \
    Dataset
from yt.frontends.ytdata.data_structures import \
    YTGridHierarchy

import numpy as np
import rasterio


class YTGTiffDataset(Dataset):
    """Dataset for saved covering grids, arbitrary grids, and FRBs."""
    _index_class = YTGridHierarchy
    _field_info_class = YTGTiffFieldInfo
    _dataset_type = 'ytgeotiff'
    geometry = "cartesian"
    default_fluid_type = "grid"
    # fluid_types = ("grid", "gas", "deposit", "index")
    fluid_types = ("grid", "index")

    _con_attrs = ()

    def __init__(self, filename):
        print 
        super(YTGTiffDataset, self).__init__(filename, self._dataset_type)
        # self.data = self.index.grids[0]

    def set_units(self):
        """Overide the set_units function of Dataset: we don't have units in our GeoTiff"""
        print "set_units overide"
        self._override_code_units()

    def _parse_parameter_file(self):
        self.refine_by = 2
        with rasterio.open(self.parameter_filename, "r") as f:
            for key in f.meta.keys():
                v = f.meta[key]
                # if key == "con_args":
                #     v = v.astype("str")
                self.parameters[key] = v
            self._with_parameter_file_open(f)
        # # No time steps/snapshots
        self.current_time = 0.
        self.unique_identifier = 0
        self.parameters["cosmological_simulation"] = False

        # if saved, restore unit registry from the json string
        # if "unit_registry_json" in self.parameters:
        #     self.unit_registry = UnitRegistry.from_json(
        #         self.parameters["unit_registry_json"])
        #     # reset self.arr and self.quan to use new unit_registry
        #     self._arr = None
        #     self._quan = None
        #     for dim in ["length", "mass", "pressure",
        #                 "temperature", "time", "velocity"]:
        #         cu = "code_" + dim
        #         if cu not in self.unit_registry:
        #             self.unit_registry.add(
        #                 cu, 1.0, getattr(dimensions, dim))
        #     if "code_magnetic" not in self.unit_registry:
        #         self.unit_registry.add("code_magnetic", 1.0,
        #                                dimensions.magnetic_field)

        # if saved, set unit system
        if "unit_system_name" in self.parameters:
            unit_system = self.parameters["unit_system_name"]
            del self.parameters["unit_system_name"]
        else:
            unit_system = 'cgs'
        # # reset unit system since we may have a new unit registry
        # self._assign_unit_system(unit_system)
        # Overide the code units as no units are provided
        self._override_code_units()

        # assign units to parameters that have associated unit string
        # del_pars = []
        # for par in self.parameters:
        #     ustr = "%s_units" % par
        #     if ustr in self.parameters:
        #         if isinstance(self.parameters[par], np.ndarray):
        #             to_u = self.arr
        #         else:
        #             to_u = self.quan
        #         self.parameters[par] = to_u(
        #             self.parameters[par], self.parameters[ustr])
        #         del_pars.append(ustr)
        # for par in del_pars:
        #     del self.parameters[par]

        # for attr in self._con_attrs:
        #     setattr(self, attr, self.parameters.get(attr))
        # self.unique_identifier = \
        #   int(os.stat(self.parameter_filename)[stat.ST_CTIME])

    # def set_units(self):
    #     if "unit_registry_json" in self.parameters:
    #         self._set_code_unit_attributes()
    #         del self.parameters["unit_registry_json"]
    #     else:
    #         super(Dataset, self).set_units()

    def _set_code_unit_attributes(self):
        attrs = ('length_unit', 'mass_unit', 'time_unit',
                 'velocity_unit', 'magnetic_unit')
        cgs_units = ('cm', 'g', 's', 'cm/s', 'gauss')
        base_units = np.ones(len(attrs))
        for unit, attr, cgs_unit in zip(base_units, attrs, cgs_units):
            uq = None
            # if attr in self.parameters and \
            #   isinstance(self.parameters[attr], YTQuantity):
            #     uq = self.parameters[attr]
            # elif attr in self.parameters and \
            #   "%s_units" % attr in self.parameters:
            #     uq = self.quan(self.parameters[attr],
            #                    self.parameters["%s_units" % attr])
            #     del self.parameters[attr]
            #     del self.parameters["%s_units" % attr]
            # elif isinstance(unit, string_types):
            #     uq = self.quan(1.0, unit)
            # elif isinstance(unit, numeric_type):
            #     uq = self.quan(unit, cgs_unit)
            # elif isinstance(unit, YTQuantity):
            #     uq = unit
            # elif isinstance(unit, tuple):
            #     uq = self.quan(unit[0], unit[1])
            # else:
            #     raise RuntimeError("%s (%s) is invalid." % (attr, unit))
            setattr(self, attr, uq)

    def create_field_info(self):
        self.field_dependencies = {}
        self.derived_field_list = []
        self.filtered_particle_types = []
        self.field_info = self._field_info_class(self, self.field_list)
        self.coordinates.setup_fields(self.field_info)
        self.field_info.setup_fluid_fields()
        for ptype in self.particle_types:
            self.field_info.setup_particle_fields(ptype)

        self._setup_gas_alias()
        self.field_info.setup_fluid_index_fields()

        if "all" not in self.particle_types:
            mylog.debug("Creating Particle Union 'all'")
            pu = ParticleUnion("all", list(self.particle_types_raw))
            self.add_particle_union(pu)
        self.field_info.setup_extra_union_fields()
        mylog.debug("Loading field plugins.")
        self.field_info.load_all_plugins()
        deps, unloaded = self.field_info.check_derived_fields()
        self.field_dependencies.update(deps)

    def _setup_override_fields(self):
        pass

    def _with_parameter_file_open(self, f):
        pass

    def _setup_gas_alias(self):
        "Alias the grid type to gas with a field alias."

        for ftype, field in self.field_list:
            if ftype == "grid":
                self.field_info.alias(("gas", field), ("grid", field))

    @classmethod
    def _is_valid(self, *args, **kwargs):
        if not (args[0].endswith(".tif") or args[0].endswith(".tiff")): return False
        with rasterio.open(args[0], "r") as f:
            # data_type = parse_gtif_attr(f, "dtype")
            driver_type = parse_gtif_attr(f, "driver")
            # if data_type == "uint16":
            #     return True
            if driver_type == "GTiff":
                return True
        return False

# class ChomboGrid(AMRGridPatch):
#     _id_offset = 0
#     __slots__ = ["_level_id"]
#     def __init__(self, id, index, level=-1):
#         AMRGridPatch.__init__(self, id, filename=index.index_filename,
#                               index=index)
#         self.Parent = None
#         self.Children = []
#         self.Level = level
