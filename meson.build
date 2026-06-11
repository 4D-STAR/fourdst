project('fourdst', 'cpp', version: 'v0.10.4', default_options: ['cpp_std=c++23'], meson_version: '>=1.5.0')

add_project_arguments('-fvisibility=default', language: 'cpp')

if get_option('build_python')
    py_installation = import('python').find_installation('python3', pure: false)
    fourdst_wheel_libdir    = 'fourdst/lib'        # relative to the python platlib
    fourdst_wheel_headerdir = 'fourdst/include'
else
    fourdst_wheel_libdir    = ''
    fourdst_wheel_headerdir = ''
endif
# Configure vendor libraries
subdir('build-config')

# Configure python bindings
if get_option('build_python')
    subdir('build-python')
endif

