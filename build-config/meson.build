if get_option('build-lib-comp') or get_option('build-lib-all') or get_option('build-python')
    subdir('libcomposition')
endif
if get_option('build-lib-config') or get_option('build-lib-all') or get_option('build-python')
    subdir('libconfig')
endif
if get_option('build-lib-const') or get_option('build-lib-all') or get_option('build-python')
    subdir('libconstants')
endif
if get_option('build-lib-log') or get_option('build-lib-all')
    subdir('liblogging')
endif
if get_option('build-lib-plugin') or get_option('build-lib-all')
    subdir('libplugin')
endif

if get_option('build-python')
    subdir('pybind')
endif
