#include <pybind11/pybind11.h>

#include <string>

#include "constants/bindings.h"
#include "composition/bindings.h"
#include "config/bindings.h"

PYBIND11_MODULE(_phys, m) {
    m.doc() = "Python bindings for the fourdst utility modules which are a part of the 4D-STAR project.";

    auto atomicMod = m.def_submodule("atomic", "Species bindings");
    register_species_bindings(atomicMod);

    auto compMod  = m.def_submodule("composition", "Composition-module bindings");
    register_comp_bindings(compMod);

    auto constMod = m.def_submodule("constants", "Constants-module bindings");
    register_const_bindings(constMod);

    auto configMod = m.def_submodule("config", "Configuration-module bindings");
    register_config_bindings(configMod);
}
