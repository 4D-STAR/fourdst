# Define the library
bindings_sources = files('bindings.cpp')
bindings_headers = files('bindings.h')

dependencies = [
    config_dep,
    python3_dep,
    pybind11_dep,
]

shared_module('py_config',
              bindings_sources,
              include_directories: include_directories('.'),
              cpp_args: ['-fvisibility=default'],
              install : true,
              dependencies: dependencies,
)