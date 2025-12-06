#pragma once

#include <pybind11/pybind11.h>
#include "fourdst/config/config.h"

#include <string>
#include <format>

void register_config_enums(const pybind11::module_& m);

template <typename ConfigType>
pybind11::class_<ConfigType> bind_config_specialization(pybind11::module_& m , const std::string& name) {
    return pybind11::class_<ConfigType>(m, name.c_str())
        .def(pybind11::init<>())
        .def("load", &ConfigType::load, pybind11::arg("file_path"), "Load configuration from a file.")
        .def("save", &ConfigType::save, pybind11::arg("file_path") = "config_output.toml", "Save configuration to a file.")
        .def("save_schema", &ConfigType::save_schema, pybind11::arg("directory") = ".", "Save the configuration schema to a directory.")
        .def("get_state", &ConfigType::get_state, "Get the current state of the configuration.")
        .def("describe_state", &ConfigType::describe_state, "Get the current state of the configuration.")
        .def("__repr__",
             [](const ConfigType &cfg) -> std::string {
                return std::format("{}", cfg);
             }
        );

}