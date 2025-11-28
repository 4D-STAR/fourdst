project('fourdst', 'cpp', version: 'v0.9.9', default_options: ['cpp_std=c++23'], meson_version: '>=1.5.0')

add_project_arguments('-fvisibility=default', language: 'cpp')

pkg_config_bool_str = 'false'
if get_option('pkg-config')
    pkg_config_bool_str = 'true'
endif


# Configure vendor libraries
subdir('build-config')

# Configure python bindings
if get_option('build-python')
    subdir('build-python')

    subdir('src-pybind')
endif

