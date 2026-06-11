#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // Needed for vectors, maps, sets, strings
#include <pybind11/stl_bind.h> // Needed for binding std::vector, std::map etc. if needed directly

#include <string>
#include <ranges>

#include "fourdst/composition/composition.h"
#include "fourdst/atomic/atomicSpecies.h"

#include "bindings.h"

#include "fourdst/atomic/species.h"
#include "fourdst/composition/utils/utils.h"
#include "fourdst/composition/utils/composition_hash.h"
#include "fourdst/composition/exceptions/exceptions_composition.h"
#include "fourdst/composition/io/standard_compositions.h"

namespace py = pybind11;

std::string sv_to_string(std::string_view sv) {
    return std::string(sv);
}

std::string get_ostream_str(const fourdst::composition::Composition& comp) {
     std::ostringstream oss;
     oss << comp;
     return oss.str();
}


void register_comp_bindings(pybind11::module &m) {
     py::class_<fourdst::composition::CanonicalComposition>(m, "CanonicalComposition")
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
     py::class_<fourdst::composition::Composition>(m, "Composition")
        // Constructors
     .def(
          py::init<>(),
          "Default constructor")
     .def(
          py::init<const std::vector<std::string>&>(),
          py::arg("symbols"),
          "Constructor taking a list of symbols to register")
     .def(
          py::init<const std::set<std::string>&>(),
          py::arg("symbols"),
          "Constructor taking a set of symbols to register"
     )
     .def(
          py::init<const std::vector<fourdst::atomic::Species>&>(),
          py::arg("species"),
          "Constructor taking a list of species to register")
     .def(
          py::init<const std::set<fourdst::atomic::Species>&>(),
          py::arg("species"),
          "Constructor taking a set of species to register"
     )
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
          py::init<const std::set<std::string>&, const std::vector<double>&>(),
          py::arg("symbols"),
          py::arg("molarAbundances"),
          "Constructor taking a set of symbols and a list of molar abundances"
     )
     .def(
          py::init<const std::unordered_map<fourdst::atomic::Species, double>&>(),
          py::arg("speciesMolarAbundances"),
          "Constructor taking an unordered map of species to molar abundances"
     )
     .def (
          py::init<const std::map<fourdst::atomic::Species, double>&>(),
          py::arg("speciesMolarAbundances"),
          "Constructor taking a map of species to molar abundances"
     )
     .def(
          py::init<const std::unordered_map<std::string, double>&>(),
          py::arg("speciesMolarAbundances"),
          "Constructor taking an unordered map of species to molar abundances"
     )
     .def (
          py::init<const std::map<std::string, double>&>(),
          py::arg("speciesMolarAbundances"),
          "Constructor taking a map of species to molar abundances"
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
          py::keep_alive<0, 1>())
     .def(
          "__eq__",
          [](const fourdst::composition::Composition& self, const fourdst::composition::Composition& other) {
               return self == other;
          },
          py::is_operator()
     )
     .def(
          "__hash__",
          [](const fourdst::composition::Composition& comp) {
               return fourdst::composition::utils::CompositionHash::hash_exact<fourdst::composition::Composition>(comp);
          }
     );

     // register new utils module
     auto utils = m.def_submodule("utils", "Utility functions for Composition");
     py::class_<fourdst::composition::utils::CompositionHash>(utils, "CompositionHash")
          .def_static(
               "hash_exact",
               &fourdst::composition::utils::CompositionHash::hash_exact<fourdst::composition::Composition>,
               py::arg("composition"),
               "Compute a hash for a given Composition object."
          );

     utils.def(
          "buildCompositionFromMassFractions",
          [](const std::vector<std::string>& symbols, const std::vector<double>& massFractions) {
               return fourdst::composition::buildCompositionFromMassFractions(symbols, massFractions);
          },
          py::arg("symbols"),
          py::arg("massFractions"),
          "Build a Composition object from symbols and their corresponding mass fractions."
     );

     utils.def("buildCompositionFromMassFractions",
          [](const std::vector<fourdst::atomic::Species>& species, const std::vector<double>& massFractions) {
               return fourdst::composition::buildCompositionFromMassFractions(species, massFractions);
          },
          py::arg("species"),
          py::arg("massFractions"),
          "Build a Composition object from species and their corresponding mass fractions."
     );

     utils.def(
          "buildCompositionFromMassFractions",
          [](const std::set<fourdst::atomic::Species>& species, const std::vector<double>& massFractions) {
               return fourdst::composition::buildCompositionFromMassFractions(species, massFractions);
          },
          py::arg("species"),
          py::arg("massFractions"),
          "Build a Composition object from species in a set and their corresponding mass fractions."
     );

     utils.def(
          "buildCompositionFromMassFractions",
          [](const std::unordered_map<fourdst::atomic::Species, double>& massFractionsMap) {
               return fourdst::composition::buildCompositionFromMassFractions(massFractionsMap);
          },
          py::arg("massFractionsMap"),
          "Build a Composition object from a map of species to mass fractions."
     );

     utils.def(
          "buildCompositionFromMassFractions",
          [](const std::map<fourdst::atomic::Species, double>& massFractionsMap) {
               return fourdst::composition::buildCompositionFromMassFractions(massFractionsMap);
          },
          py::arg("massFractionsMap"),
          "Build a Composition object from a map of species to mass fractions."
     );

     auto io = m.def_submodule("io", "IO library for standard solar compositions");

     py::class_<fourdst::composition::io::CompositionData> (io, "CompositionData")
     .def(py::init<>())
     .def_readwrite("comment_str", &fourdst::composition::io::CompositionData::comment_str)
     .def_readwrite("he_abundance", &fourdst::composition::io::CompositionData::he_abundance)
     .def_readwrite("requires_atomic_weight", &fourdst::composition::io::CompositionData::requires_atomic_weight)
     .def_property("elements",
             [](fourdst::composition::io::CompositionData &self) -> const std::vector<std::string>& {
                 return self.elements;
             },
             [](fourdst::composition::io::CompositionData &self, const std::vector<std::string> &value) {
                 self.elements = value;
             },
             py::return_value_policy::reference_internal
     )
     .def_property("abundances",
             [](fourdst::composition::io::CompositionData &self) -> const std::vector<double>& {
                 return self.abundances;
             },
             [](fourdst::composition::io::CompositionData &self, const std::vector<double> &value) {
                 self.abundances = value;
             },
             py::return_value_policy::reference_internal
     );

     py::class_<fourdst::composition::io::IsotopicPercentage>(io, "IsotopicPercentage")
     .def(py::init<>())
     .def_readwrite("comment_str", &fourdst::composition::io::IsotopicPercentage::comment_str)
     .def_property("atomic_numbers",
          [](fourdst::composition::io::IsotopicPercentage &self) -> const std::vector<int>& {
               return self.atomic_numbers;
          },
          [](fourdst::composition::io::IsotopicPercentage &self, const std::vector<int> &value) {
               self.atomic_numbers = value;
          },
          py::return_value_policy::reference_internal
     )
     .def_property("elements",
          [](fourdst::composition::io::IsotopicPercentage &self) -> const std::vector<std::string>& {
               return self.elements;
          },
          [](fourdst::composition::io::IsotopicPercentage &self, const std::vector<std::string> &value) {
               self.elements = value;
          },
          py::return_value_policy::reference_internal
     )
     .def_property("mass_numbers",
          [](fourdst::composition::io::IsotopicPercentage &self) -> const std::vector<int>& {
               return self.mass_numbers;
          },
          [](fourdst::composition::io::IsotopicPercentage &self, const std::vector<int> &value) {
               self.mass_numbers = value;
          },
          py::return_value_policy::reference_internal
     )
     .def_property("percentages",
          [](fourdst::composition::io::IsotopicPercentage &self) -> const std::vector<double>& {
               return self.percentages;
          },
          [](fourdst::composition::io::IsotopicPercentage &self, const std::vector<double> &value) {
               self.percentages = value;
          },
          py::return_value_policy::reference_internal
     );

     py::enum_<fourdst::composition::io::SolarCompositions>(io,"SolarCompositions")
     .value("AG89", fourdst::composition::io::SolarCompositions::AG89)
     .value("GN93", fourdst::composition::io::SolarCompositions::GN93)
     .value("GS98", fourdst::composition::io::SolarCompositions::GS98)
     .value("L03", fourdst::composition::io::SolarCompositions::L03)
     .value("AGS05", fourdst::composition::io::SolarCompositions::AGS05)
     .value("AGSS09", fourdst::composition::io::SolarCompositions::AGSS09)
     .value("A09_Przybilla", fourdst::composition::io::SolarCompositions::A09_Przybilla)
     .value("MB22_photospheric", fourdst::composition::io::SolarCompositions::MB22_photospheric)
     .value("AAG21_photospheric", fourdst::composition::io::SolarCompositions::AAG21_photospheric)
     .value("L09", fourdst::composition::io::SolarCompositions::L09)
     .export_values();

     py::enum_<fourdst::composition::io::IsotopicPercentages>(io,"IsotopicPercentages")
     .value("L03", fourdst::composition::io::IsotopicPercentages::L03)
     .value("L09", fourdst::composition::io::IsotopicPercentages::L09);

     io.attr("SolarCompositions_to_string_map") = fourdst::composition::io::SolarCompositions_to_string_map;
     io.attr("IsotopicPercentages_to_string_map") = fourdst::composition::io::IsotopicPercentages_to_string_map;

     io.def("get_raw_standard_solar_composition_data",
          []() -> std::vector<unsigned char> {
               std::span<const unsigned char> raw = fourdst::composition::io::get_raw_standard_solar_composition_data();
               return std::ranges::to<std::vector<unsigned char>>(raw);
          }
     );

     py::class_<fourdst::composition::io::ChemicalFileParser>(io,"ChemicalFileParser")
     .def(py::init<>())
     .def_static("parse_composition_data",
          &fourdst::composition::io::ChemicalFileParser::parse_composition_data,
          py::arg("data"),
          py::arg("scheme")
     )
     .def_static("parse_isotopic_percentage",
          &fourdst::composition::io::ChemicalFileParser::parse_isotopic_percentage,
          py::arg("data"),
          py::arg("scheme")
     );

     m.def("get_composition_record",
          py::overload_cast<const std::string&, const std::string&, double, double>(&fourdst::composition::get_composition_record),
          py::arg("metal_fraction_scheme"),
          py::arg("isotopic_percentage_scheme"),
          py::arg("initial_z"),
          py::arg("initial_y")
     );

     m.def("get_composition_record",
          py::overload_cast<fourdst::composition::io::SolarCompositions, fourdst::composition::io::IsotopicPercentages, double, double>(&fourdst::composition::get_composition_record),
          py::arg("metal_fraction_scheme"),
          py::arg("isotopic_percentage_scheme"),
          py::arg("initial_z"),
          py::arg("initial_y")
     );
}

void register_species_bindings(pybind11::module &chem_submodule) {
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
               }
          )
          .def(
               "__eq__",
               [](const fourdst::atomic::Species& self, const fourdst::atomic::Species& other) {
                    return self == other;
               },
               py::is_operator()
          )
          .def(
               "__hash__",
               [](const fourdst::atomic::Species& s) {
                    return std::hash<fourdst::atomic::Species>()(s);
               }
          );


     chem_submodule.attr("species") = py::cast(fourdst::atomic::species); // Expose the species map

     auto replace_dash_with_underscore = [](const std::string& str) {
          std::string result = str;
          std::ranges::replace(result, '-', '_');
          return result;
     };

     for (const auto& [name, species] : fourdst::atomic::species) {
          chem_submodule.attr(replace_dash_with_underscore(name).c_str()) = py::cast(species);
     }

     chem_submodule.def("az_to_species",
          [](const int a, const int z) {
               const auto result = fourdst::atomic::az_to_species(a, z);
               if (!result) {
                    throw fourdst::composition::exceptions::SpeciesError(std::format("Species with A={} and Z={} not found.", a, z));
               }
               return result.value();
          },
          py::arg("a"),
          py::arg("z"),
          "Get Species object from proton number (Z) and mass number (A)."
     );
}

void register_comp_exceptions(pybind11::module &m) {
     py::register_exception<fourdst::composition::exceptions::CompositionError>(m, "CompositionError");
     py::register_exception<fourdst::composition::exceptions::InvalidCompositionError>(m, "InvalidCompositionError", m.attr("CompositionError"));
     py::register_exception<fourdst::composition::exceptions::SpeciesError>(m, "SpeciesError");
     py::register_exception<fourdst::composition::exceptions::UnknownSymbolError>(m, "UnknownSymbolError", m.attr("SpeciesError"));
     py::register_exception<fourdst::composition::exceptions::UnregisteredSymbolError>(m, "UnregisteredSymbolError", m.attr("SpeciesError"));
}
