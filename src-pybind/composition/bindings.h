#pragma once

#include <pybind11/pybind11.h>

void register_comp_bindings(const pybind11::module &m);
void register_species_bindings(const pybind11::module &m);
