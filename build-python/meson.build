# --- Python Extension Setup ---
py_installation = import('python').find_installation('python3')

py_mod = py_installation.extension_module(
    'fourdst', # Name of the generated .so/.pyd file (without extension)
    sources: [
        meson.project_source_root() + '/src-pybind/bindings.cpp',
        meson.project_source_root() + '/src-pybind/composition/bindings.cpp',
        meson.project_source_root() + '/src-pybind/constants/bindings.cpp',
        meson.project_source_root() + '/src-pybind/config/bindings.cpp',
    ],
    dependencies : [
        pybind11_dep,
        const_dep,
        config_dep,
        composition_dep,
    ],
    cpp_args : ['-UNDEBUG'],
    install : true,
)
