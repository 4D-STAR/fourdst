# Define the library
bindings_sources = files('bindings.cpp')
bindings_headers = files('bindings.h')

dependencies = [
    composition_dep,
    python3_dep,
    pybind11_dep,
]

shared_module('py_composition',
    bindings_sources,
    cpp_args: ['-fvisibility=default'],
    install : true,
    dependencies: dependencies,
    include_directories: include_directories('.')
)
