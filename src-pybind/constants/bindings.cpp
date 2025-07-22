#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // Needed for vectors, maps, sets, strings
#include <pybind11/stl_bind.h> // Needed for binding std::vector, std::map etc if needed directly

#include <string>
#include "fourdst/constants/const.h"
#include "bindings.h"

namespace py = pybind11;


void register_const_bindings(pybind11::module &const_submodule) {
    py::class_<fourdst::constant::Constant>(const_submodule, "Constant")
        .def_readonly("name", &fourdst::constant::Constant::name)
        .def_readonly("value", &fourdst::constant::Constant::value)
        .def_readonly("uncertainty", &fourdst::constant::Constant::uncertainty)
        .def_readonly("unit", &fourdst::constant::Constant::unit)
        .def_readonly("reference", &fourdst::constant::Constant::reference)
        .def("__repr__", [](const fourdst::constant::Constant &c) {
            return "<Constant(name='" + c.name + "', value=" + std::to_string(c.value) +
                   ", uncertainty=" + std::to_string(c.uncertainty) +
                   ", unit='" + c.unit + "')>";
        });

    py::class_<fourdst::constant::Constants>(const_submodule, "Constants")
        .def_property_readonly("loaded", &fourdst::constant::Constants::isLoaded)
        .def_static("get",
            [](const std::string &name) {
                return py::cast(
                    fourdst::constant::Constants::getInstance().get(name)
                );
            },
            "Get a constant by name. Returns None if not found."
        )
        .def_static("has",
            [](const std::string &name) {
                return fourdst::constant::Constants::getInstance().has(name);
            },
            "Check if a constant exists by name.")
        .def_static("keys",
            []() {
                return py::cast(
                    fourdst::constant::Constants::getInstance().keys()
                );
            },
            "Get a list of all constant names.")
        .def_static("__class_getitem__",
         [](const std::string &name) {
             return py::cast(
                 fourdst::constant::Constants::getInstance().get(name)
             );
         });

}
