if get_option('build_lib_comp') or get_option('build_lib_all') or get_option('build_python')
    subdir('libcomposition')
endif
if get_option('build_lib_config') or get_option('build_lib_all') or get_option('build_python')
    subdir('libconfig')
endif
if get_option('build_lib_const') or get_option('build_lib_all') or get_option('build_python')
    subdir('libconstants')
endif
if get_option('build_lib_log') or get_option('build_lib_all')
    subdir('liblogging')
endif
if get_option('build_lib_plugin') or get_option('build_lib_all')
    subdir('libplugin')
endif

if get_option('build_python')
    subdir('pybind')
endif
