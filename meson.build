project('fourdst', 'cpp', version: 'v0.9.15', default_options: ['cpp_std=c++23'], meson_version: '>=1.5.0')

add_project_arguments('-fvisibility=default', language: 'cpp')


# Configure vendor libraries
subdir('build-config')

# Configure python bindings
if get_option('build_python')
    subdir('build-python')
endif

