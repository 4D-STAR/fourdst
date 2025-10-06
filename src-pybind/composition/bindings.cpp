#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // Needed for vectors, maps, sets, strings
#include <pybind11/stl_bind.h> // Needed for binding std::vector, std::map etc. if needed directly

#include <string>

#include "fourdst/composition/composition.h"
#include "fourdst/composition/atomicSpecies.h"

#include "bindings.h"

#include "fourdst/composition/species.h"

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

    // --- Bindings for composition and species module ---
    py::class_<fourdst::composition::GlobalComposition>(comp_submodule, "GlobalComposition")
        .def_readonly("specificNumberDensity", &fourdst::composition::GlobalComposition::specificNumberDensity)
        .def_readonly("meanParticleMass", &fourdst::composition::GlobalComposition::meanParticleMass)
        .def("__repr__", // Add a string representation for easy printing in Python
             [](const fourdst::composition::GlobalComposition &gc) {
                 return "<GlobalComposition(specNumDens=" + std::to_string(gc.specificNumberDensity) +
                        ", meanMass=" + std::to_string(gc.meanParticleMass) + ")>";
             });

    py::class_<fourdst::composition::CompositionEntry>(comp_submodule, "CompositionEntry")
        .def("symbol", &fourdst::composition::CompositionEntry::symbol)
        .def("mass_fraction",
             py::overload_cast<>(&fourdst::composition::CompositionEntry::mass_fraction, py::const_),
             "Gets the mass fraction of the species.")
        .def("number_fraction",
              py::overload_cast<>(&fourdst::composition::CompositionEntry::number_fraction, py::const_),
              "Gets the number fraction of the species.")
        .def("number_fraction",
              py::overload_cast<double>(&fourdst::composition::CompositionEntry::number_fraction, py::const_),
              py::arg("totalMoles"),
              "Gets the number fraction of the species given the total moles.")

        .def("rel_abundance", &fourdst::composition::CompositionEntry::rel_abundance)
        .def("isotope", &fourdst::composition::CompositionEntry::isotope) // Assuming Species is bound or convertible
        .def("getMassFracMode", &fourdst::composition::CompositionEntry::getMassFracMode)

        .def("__repr__", // Optional: nice string representation
            [](const fourdst::composition::CompositionEntry &ce) {
                // You might want to include more info here now
                return "<CompositionEntry(symbol='" + ce.symbol() + "', " +
                    "mass_frac=" + std::to_string(ce.mass_fraction()) + ", " +
                    "num_frac=" + std::to_string(ce.number_fraction()) + ")>";
            });

        // --- Binding for the main Composition class ---
    py::class_<fourdst::composition::Composition>(comp_submodule, "Composition")
        // Constructors
        .def(py::init<>(), "Default constructor")
        .def(py::init<const std::vector<std::string>&>(),
             py::arg("symbols"),
             "Constructor taking a list of symbols to register (defaults to mass fraction mode)")
        // .def(py::init<const std::set<std::string>&>(), py::arg("symbols")) // Binding std::set constructor is possible but often less convenient from Python
        .def(py::init<const std::vector<std::string>&, const std::vector<double>&, bool>(),
             py::arg("symbols"), py::arg("fractions"), py::arg("massFracMode") = true,
             "Constructor taking symbols, fractions, and mode (True=Mass, False=Number)")

        // Methods
        .def("finalize", &fourdst::composition::Composition::finalize, py::arg("norm") = false,
             "Finalize the composition, optionally normalizing fractions to sum to 1.")

        .def("registerSymbol", py::overload_cast<const std::string&, bool>(&fourdst::composition::Composition::registerSymbol),
             py::arg("symbol"), py::arg("massFracMode") = true, "Register a single symbol.")
        .def("registerSymbol", py::overload_cast<const std::vector<std::string>&, bool>(&fourdst::composition::Composition::registerSymbol),
             py::arg("symbols"), py::arg("massFracMode") = true, "Register multiple symbols.")

        .def("registerSpecies", py::overload_cast<const fourdst::atomic::Species&, bool>(&fourdst::composition::Composition::registerSpecies),
             py::arg("species"), py::arg("massFracMode") = true, "Register a single species.")
        .def("registerSpecies", py::overload_cast<const std::vector<fourdst::atomic::Species>&, bool>(&fourdst::composition::Composition::registerSpecies),
             py::arg("species"), py::arg("massFracMode") = true, "Register multiple species.")

        .def("getRegisteredSymbols", &fourdst::composition::Composition::getRegisteredSymbols,
             "Get the set of registered symbols.")
        .def("getRegisteredSpecies", &fourdst::composition::Composition::getRegisteredSpecies,
             "Get the set of registered species.")

        .def("setMassFraction", py::overload_cast<const std::string&, const double&>(&fourdst::composition::Composition::setMassFraction),
             py::arg("symbol"), py::arg("mass_fraction"), "Set mass fraction for a single symbol (requires massFracMode). Returns old value.")
        .def("setMassFraction", py::overload_cast<const std::vector<std::string>&, const std::vector<double>&>(&fourdst::composition::Composition::setMassFraction),
             py::arg("symbols"), py::arg("mass_fractions"), "Set mass fractions for multiple symbols (requires massFracMode). Returns list of old values.")
        .def("setMassFraction", py::overload_cast<const fourdst::atomic::Species&, const double&>(&fourdst::composition::Composition::setMassFraction),
             py::arg("species"), py::arg("mass_fraction"), "Set mass fraction for a single species (requires massFracMode). Returns old value.")
        .def("setMassFraction", py::overload_cast<const std::vector<fourdst::atomic::Species>&, const std::vector<double>&>(&fourdst::composition::Composition::setMassFraction),
             py::arg("species"), py::arg("mass_fractions"), "Set mass fractions for multiple species (requires massFracMode). Returns list of old values.")

        .def("setNumberFraction", py::overload_cast<const std::string&, const double&>(&fourdst::composition::Composition::setNumberFraction),
             py::arg("symbol"), py::arg("number_fraction"), "Set number fraction for a single symbol (requires !massFracMode). Returns old value.")
        .def("setNumberFraction", py::overload_cast<const std::vector<std::string>&, const std::vector<double>&>(&fourdst::composition::Composition::setNumberFraction),
             py::arg("symbols"), py::arg("number_fractions"), "Set number fractions for multiple symbols (requires !massFracMode). Returns list of old values.")
        .def("setNumberFraction", py::overload_cast<const fourdst::atomic::Species&, const double&>(&fourdst::composition::Composition::setNumberFraction),
             py::arg("species"), py::arg("number_fraction"), "Set number fraction for a single species (requires !massFracMode). Returns old value.")
        .def("setNumberFraction", py::overload_cast<const std::vector<fourdst::atomic::Species>&, const std::vector<double>&>(&fourdst::composition::Composition::setNumberFraction),
             py::arg("species"), py::arg("number_fractions"), "Set number fractions for multiple species (requires !massFracMode). Returns list of old values.")

        .def("mix", &fourdst::composition::Composition::mix, py::arg("other"), py::arg("fraction"),
             "Mix with another composition. Returns new Composition.")

        .def("getMassFraction", py::overload_cast<const std::string&>(&fourdst::composition::Composition::getMassFraction, py::const_),
             py::arg("symbol"), "Get mass fraction for a symbol (calculates if needed). Requires finalization.")
        .def("getMassFraction", py::overload_cast<const fourdst::atomic::Species&>(&fourdst::composition::Composition::getMassFraction, py::const_),
             py::arg("species"), "Get mass fraction for a species (calculates if needed). Requires finalization.")
        .def("getMassFraction", py::overload_cast<>(&fourdst::composition::Composition::getMassFraction, py::const_),
             "Get dictionary of all mass fractions. Requires finalization.")

        .def("getNumberFraction", py::overload_cast<const std::string&>(&fourdst::composition::Composition::getNumberFraction, py::const_),
             py::arg("symbol"), "Get number fraction for a symbol (calculates if needed). Requires finalization.")
        .def("getNumberFraction", py::overload_cast<const fourdst::atomic::Species&>(&fourdst::composition::Composition::getNumberFraction, py::const_),
             py::arg("species"), "Get number fraction for a species (calculates if needed). Requires finalization.")
        .def("getNumberFraction", py::overload_cast<>(&fourdst::composition::Composition::getNumberFraction, py::const_),
             "Get dictionary of all number fractions. Requires finalization.")

        .def("getMolarAbundance", py::overload_cast<const std::string&>(&fourdst::composition::Composition::getMolarAbundance, py::const_),
             py::arg("symbol"), "Get molar abundance for a symbol (calculates if needed). Requires finalization.")
        .def("getMolarAbundance", py::overload_cast<const fourdst::atomic::Species&>(&fourdst::composition::Composition::getMolarAbundance, py::const_),
             py::arg("species"), "Get molar abundance for a species (calculates if needed). Requires finalization.")

        .def("getComposition", py::overload_cast<const std::string&>(&fourdst::composition::Composition::getComposition, py::const_),
             py::arg("symbol"), "Returns a tuple (CompositionEntry, GlobalComposition) for the symbol. Requires finalization.")
        .def("getComposition", py::overload_cast<const fourdst::atomic::Species&>(&fourdst::composition::Composition::getComposition, py::const_),
             py::arg("species"), "Returns a tuple (CompositionEntry, GlobalComposition) for the species. Requires finalization.")
        .def("getComposition", py::overload_cast<>(&fourdst::composition::Composition::getComposition, py::const_),
            "Returns a tuple (dict[str, CompositionEntry], GlobalComposition) for all symbols. Requires finalization.")

        .def("getMeanParticleMass", &fourdst::composition::Composition::getMeanParticleMass,
             "Get the mean particle mass (amu). Requires finalization.")
        .def("getMeanAtomicNumber", &fourdst::composition::Composition::getMeanAtomicNumber,
             "Get the mean atomic number <Z>. Requires finalization.")


        .def("subset", &fourdst::composition::Composition::subset, py::arg("symbols"), py::arg("method") = "norm",
             "Create a new Composition containing only the specified symbols.")
        .def("hasSymbol", &fourdst::composition::Composition::hasSymbol, py::arg("symbol"),
             "Check if a symbol is registered.")
        .def("contains", &fourdst::composition::Composition::contains, py::arg("species"),
             "Check if a species is registered.")
        .def("setCompositionMode", &fourdst::composition::Composition::setCompositionMode, py::arg("massFracMode"),
             "Set the mode (True=Mass, False=Number). Requires finalization before switching.")

        .def("getMassFractionVector", &fourdst::composition::Composition::getMassFractionVector,
              "Get mass fractions as a vector (ordered by species mass). Requires finalization.")
        .def("getNumberFractionVector", &fourdst::composition::Composition::getNumberFractionVector,
             "Get number fractions as a vector (ordered by species mass). Requires finalization.")
        .def("getMolarAbundanceVector", &fourdst::composition::Composition::getMolarAbundanceVector,
             "Get molar abundances as a vector (ordered by species mass). Requires finalization.")
        .def("getSpeciesIndex", py::overload_cast<const std::string&>(&fourdst::composition::Composition::getSpeciesIndex, py::const_), py::arg("symbol"),
             "Get the index of a species in the internal ordering. Requires finalization.")
        .def("getSpeciesIndex", py::overload_cast<const fourdst::atomic::Species&>(&fourdst::composition::Composition::getSpeciesIndex, py::const_), py::arg("species"),
             "Get the index of a species in the internal ordering. Requires finalization.")
        .def("getSpeciesAtIndex", py::overload_cast<size_t>(&fourdst::composition::Composition::getSpeciesAtIndex, py::const_), py::arg("index"),
             "Get the species at a given index in the internal ordering. Requires finalization.")

        .def("getCanonicalComposition", &fourdst::composition::Composition::getCanonicalComposition, py::arg("harsh") = true,
             "Get a canonical composition (X, Y, Z). Requires finalization.")

        // Operator overload
        .def(py::self + py::self, "Mix equally with another composition.") // Binds operator+

        // Add __repr__ or __str__
         .def("__repr__", [](const fourdst::composition::Composition &comp) {
             return get_ostream_str(comp); // Use helper for C++ operator<<
         });

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
