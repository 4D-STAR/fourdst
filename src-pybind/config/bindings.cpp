#include "bindings.h"

#include <pybind11/pybind11.h>
#include "fourdst/config/config.h"

void register_config_enums(const pybind11::module_& m) {
    using namespace fourdst::config;
    pybind11::enum_<ConfigState>(m, "ConfigState")
        .value("DEFAULT", ConfigState::DEFAULT)
        .value("LOADED_FROM_FILE", ConfigState::LOADED_FROM_FILE)
        .export_values();

    pybind11::enum_<RootNameLoadPolicy>(m, "RootNameLoadPolicy")
        .value("FROM_FILE", RootNameLoadPolicy::FROM_FILE)
        .value("KEEP_CURRENT", RootNameLoadPolicy::KEEP_CURRENT)
        .export_values();
}
