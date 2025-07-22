#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // Needed for vectors, maps, sets, strings
#include <pybind11/stl_bind.h> // Needed for binding std::vector, std::map etc if needed directly

#include <string>
#include "bindings.h"

#include "fourdst/config/config.h"

namespace py = pybind11;

// Helper function template for binding Config::get
template <typename T>
void def_config_get(py::module &m) {
    m.def("get",
          [](const std::string &key, T defaultValue) {
              return fourdst::config::Config::getInstance().get<T>(key, defaultValue);
          },
          py::arg("key"), py::arg("defaultValue"),
          "Get configuration value (type inferred from default)");
}

void register_config_bindings(pybind11::module &config_submodule) {
    def_config_get<int>(config_submodule);
    def_config_get<double>(config_submodule);
    def_config_get<std::string>(config_submodule);
    def_config_get<bool>(config_submodule);

    config_submodule.def("loadConfig",
        [](const std::string& configFilePath) {
            return fourdst::config::Config::getInstance().loadConfig(configFilePath);
        },
        py::arg("configFilePath"),
        "Load configuration from a YAML file.");

    config_submodule.def("has",
        [](const std::string &key) {
            return fourdst::config::Config::getInstance().has(key);
        },
        py::arg("key"),
        "Check if a key exists in the configuration.");

    config_submodule.def("keys",
        []() {
            return py::cast(fourdst::config::Config::getInstance().keys());
        },
        "Get a list of all configuration keys.");

    config_submodule.def("__repr__",
        []() {
            std::ostringstream oss;
            oss << fourdst::config::Config::getInstance(); // Use the existing operator<<
            return std::string("<fourdsse_bindings.config module accessing C++ Singleton>\n") + oss.str();
        });
}
