# Define the library
bindings_sources = files('bindings.cpp')
bindings_headers = files('bindings.h')

dependencies = [
    const_dep,
    python3_dep,
    pybind11_dep,
]

shared_module('py_const',
    bindings_sources,
    include_directories: include_directories('.'),
    cpp_args: ['-fvisibility=default'],
    install : true,
    dependencies: dependencies,
)
