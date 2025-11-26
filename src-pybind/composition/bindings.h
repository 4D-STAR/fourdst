#pragma once

#include <pybind11/pybind11.h>

void register_comp_exceptions(pybind11::module &m);
void register_species_bindings(pybind11::module &m);
void register_comp_bindings(pybind11::module &m);

