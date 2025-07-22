project('fourdst', 'cpp', version: 'v0.5.0', default_options: ['cpp_std=c++23'], meson_version: '>=1.5.0')

add_project_arguments('-fvisibility=default', language: 'cpp')

# Configure vendor libraries
subdir('build-config')

# Configure python bindings
subdir('build-python')

# Build python bindings
subdir('src-pybind')
