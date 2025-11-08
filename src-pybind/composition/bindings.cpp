#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // Needed for vectors, maps, sets, strings
#include <pybind11/stl_bind.h> // Needed for binding std::vector, std::map etc. if needed directly

#include <string>

#include "fourdst/composition/composition.h"
#include "fourdst/atomic/atomicSpecies.h"

#include "bindings.h"

#include "fourdst/atomic/species.h"

namespace py = pybind11;

std::string sv_to_string(std::string_view sv) {
    return std::string(sv);
}

std::string get_ostream_str(const fourdst::composition::Composition& comp) {
     std::ostringstream oss;
     oss << comp;
     return oss.str();
}


void register_comp_bindings(const pybind11::module &comp_submodule) {
     py::class_<fourdst::composition::CanonicalComposition>(comp_submodule, "CanonicalComposition")
          .def_readonly("X", &fourdst::composition::CanonicalComposition::X)
          .def_readonly("Y", &fourdst::composition::CanonicalComposition::Y)
          .def_readonly("Z", &fourdst::composition::CanonicalComposition::Z)
          .def("__repr__", // Add a string representation for easy printing in Python
               [](const fourdst::composition::CanonicalComposition &cc) {
                   return "<CanonicalComposition(X=" + std::to_string(cc.X) +
                          ", Y=" + std::to_string(cc.Y) +
                          ", Z=" + std::to_string(cc.Z) + ")>";
               });

     // --- Binding for the main Composition class ---
     py::class_<fourdst::composition::Composition>(comp_submodule, "Composition")
        // Constructors
     .def(
          py::init<>(),
          "Default constructor")
     .def(
          py::init<const std::vector<std::string>&>(),
          py::arg("symbols"),
          "Constructor taking a list of symbols to register")
     .def(
          py::init<const std::vector<fourdst::atomic::Species>&>(),
          py::arg("species"),
          "Constructor taking a list of species to register")
     .def(
          py::init<const std::vector<std::string>&, const std::vector<double>&>(),
          py::arg("symbols"),
          py::arg("molarAbundances"),
          "Constructor taking a list of symbols and molar abundances"
     )
     .def(
          py::init<const std::vector<fourdst::atomic::Species>&, const std::vector<double>&>(),
          py::arg("species"),
          py::arg("molarAbundances"),
          "Constructor taking a list of species and molar abundances"
     )
     .def(
          "registerSymbol",
          py::overload_cast<const std::string&>(&fourdst::composition::Composition::registerSymbol),
          py::arg("symbol"),
          "Register a single symbol. The molar abundance will be initialized to zero.")
     .def(
          "registerSymbol",
          py::overload_cast<const std::vector<std::string>&>(&fourdst::composition::Composition::registerSymbol),
          py::arg("symbols"),
          "Register multiple symbols. Each molar abundance will be initialized to zero.")
     .def(
          "registerSpecies",
          py::overload_cast<const fourdst::atomic::Species&>(&fourdst::composition::Composition::registerSpecies),
          py::arg("species"),
          "Register a single species. The molar abundance will be initialized to zero.")
     .def(
     "registerSpecies",
          py::overload_cast<const std::vector<fourdst::atomic::Species>&>(&fourdst::composition::Composition::registerSpecies),
          py::arg("species"),
          "Register multiple species. Each molar abundance will be initialized to zero.")
     .def(
          "contains",
          py::overload_cast<const std::string&>(&fourdst::composition::Composition::contains, py::const_),
          py::arg("symbol"),
          "Check if a symbol is in the composition.")
     .def(
          "contains",
          py::overload_cast<const fourdst::atomic::Species&>(&fourdst::composition::Composition::contains, py::const_),
          py::arg("species"),
          "Check if a species is in the composition.")
     .def(
          "size",
          &fourdst::composition::Composition::size,
          "Get the number of registered species in the composition.")
     .def(
          "setMolarAbundance",
          py::overload_cast<const std::string&, const double&>(&fourdst::composition::Composition::setMolarAbundance),
          py::arg("symbol"),
          py::arg("molarAbundance"),
          "Set the molar abundance for a symbol.")
     .def(
          "setMolarAbundance",
          py::overload_cast<const fourdst::atomic::Species&, const double&>(&fourdst::composition::Composition::setMolarAbundance),
          py::arg("species"),
          py::arg("molarAbundance"),
          "Set the molar abundance for a species.")
     .def(
          "setMolarAbundance",
          py::overload_cast<const std::vector<std::string>&, const std::vector<double>&>(&fourdst::composition::Composition::setMolarAbundance),
          py::arg("symbols"),
          py::arg("molarAbundances"),
          "Set the molar abundance for a list of symbols. The molar abundance vector must be parallel to the symbols vector.")
     .def(
          "setMolarAbundance",
          py::overload_cast<const std::vector<fourdst::atomic::Species>&, const std::vector<double>&>(&fourdst::composition::Composition::setMolarAbundance),
          py::arg("species"),
          py::arg("molarAbundances"),
          "Set the molar abundance for a list of species. The molar abundance vector must be parallel to the species vector.")

     .def(
          "getRegisteredSymbols",
          &fourdst::composition::Composition::getRegisteredSymbols,
          "Get the set of registered symbols.")
     .def(
          "getRegisteredSpecies",
          &fourdst::composition::Composition::getRegisteredSpecies,
          "Get the set of registered species.")


     .def(
          "getMassFraction",
          py::overload_cast<const std::string&>(&fourdst::composition::Composition::getMassFraction, py::const_),
          py::arg("symbol"),
          "Get mass fraction for a symbol.")
     .def(
          "getMassFraction",
          py::overload_cast<const fourdst::atomic::Species&>(&fourdst::composition::Composition::getMassFraction, py::const_),
          py::arg("species"),
          "Get mass fraction for a species.")
     .def(
          "getMassFraction",
          py::overload_cast<>(&fourdst::composition::Composition::getMassFraction, py::const_),
          "Get dictionary of all mass fractions. ")
     .def(
          "getNumberFraction",
          py::overload_cast<const std::string&>(&fourdst::composition::Composition::getNumberFraction, py::const_),
          py::arg("symbol"),
          "Get number fraction for a symbol.")
     .def(
          "getNumberFraction",
          py::overload_cast<const fourdst::atomic::Species&>(&fourdst::composition::Composition::getNumberFraction, py::const_),
          py::arg("species"),
          "Get number fraction for a species.")
     .def("getNumberFraction", py::overload_cast<>(&fourdst::composition::Composition::getNumberFraction, py::const_),
             "Get dictionary of all number fractions.")

     .def(
          "getMolarAbundance",
          py::overload_cast<const std::string&>(&fourdst::composition::Composition::getMolarAbundance, py::const_),
          py::arg("symbol"),
          "Get molar abundance for a symbol.")
     .def(
          "getMolarAbundance",
          py::overload_cast<const fourdst::atomic::Species&>(&fourdst::composition::Composition::getMolarAbundance, py::const_),
          py::arg("species"),
          "Get molar abundance for a species.")

     .def(
          "getMeanParticleMass",
          &fourdst::composition::Composition::getMeanParticleMass,
          "Get the mean particle mass (amu)")

     .def(
          "getMassFractionVector",
          &fourdst::composition::Composition::getMassFractionVector,
          "Get mass fractions as a vector (ordered by species mass).")
     .def(
          "getNumberFractionVector",
          &fourdst::composition::Composition::getNumberFractionVector,
          "Get number fractions as a vector (ordered by species mass)")
     .def(
          "getMolarAbundanceVector",
          &fourdst::composition::Composition::getMolarAbundanceVector,
          "Get molar abundances as a vector (ordered by species mass).")
     .def(
          "getSpeciesIndex",
          py::overload_cast<const std::string&>(&fourdst::composition::Composition::getSpeciesIndex, py::const_), py::arg("symbol"),
          "Get the index of a species in the internal ordering.")
     .def(
          "getSpeciesIndex",
          py::overload_cast<const fourdst::atomic::Species&>(&fourdst::composition::Composition::getSpeciesIndex, py::const_), py::arg("species"),
          "Get the index of a species in the internal ordering.")
     .def(
          "getSpeciesAtIndex",
          py::overload_cast<size_t>(&fourdst::composition::Composition::getSpeciesAtIndex, py::const_), py::arg("index"),
          "Get the species at a given index in the internal ordering.")

     .def(
          "getCanonicalComposition",
          &fourdst::composition::Composition::getCanonicalComposition,
          "Get a canonical composition (X, Y, Z). d")

        // Add __repr__ or __str__
     .def(
          "__repr__",
          [](const fourdst::composition::Composition &comp) {
             return get_ostream_str(comp); // Use helper for C++ operator<<
         })
     .def(
          "__iter__",
          [](const fourdst::composition::Composition& comp) {
               return py::make_iterator(comp.begin(), comp.end());
          },
          py::keep_alive<0, 1>());

}

void register_species_bindings(const pybind11::module &chem_submodule) {
     // --- Bindings for species module ---
     py::class_<fourdst::atomic::Species>(chem_submodule, "Species")
         .def("mass", &fourdst::atomic::Species::mass, "Get atomic mass (amu)")
         .def("massUnc", &fourdst::atomic::Species::massUnc, "Get atomic mass uncertainty (amu)")
         .def("bindingEnergy", &fourdst::atomic::Species::bindingEnergy, "Get binding energy (keV/nucleon?)") // Check units
         .def("betaDecayEnergy", &fourdst::atomic::Species::betaDecayEnergy, "Get beta decay energy (keV?)") // Check units
         .def("betaCode", [](const fourdst::atomic::Species& s){ return sv_to_string(s.betaCode()); }, "Get beta decay code") // Convert string_view
         .def("name", [](const fourdst::atomic::Species& s){ return sv_to_string(s.name()); }, "Get species name (e.g., 'H-1')") // Convert string_view
         .def("el", [](const fourdst::atomic::Species& s){ return sv_to_string(s.el()); }, "Get element symbol (e.g., 'H')") // Convert string_view
         .def("nz", &fourdst::atomic::Species::nz, "Get NZ value")
         .def("n", &fourdst::atomic::Species::n, "Get neutron number N")
         .def("z", &fourdst::atomic::Species::z, "Get proton number Z")
         .def("a", &fourdst::atomic::Species::a, "Get mass number A")

     .def("__repr__",
          [](const fourdst::atomic::Species &s) {
              std::ostringstream oss;
              oss << s;
              return oss.str();
          });

     chem_submodule.attr("species") = py::cast(fourdst::atomic::species); // Expose the species map
}
