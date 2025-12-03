plugin_p = subproject('libplugin', default_options: [
                          'pkg-config=' + get_option('pkg_config').to_string(),
                          'build-tests=' + get_option('build_tests').to_string(),
                          'python-wheel=' + get_option('build_python').to_string(),
                      ])
libplugin = plugin_p.get_variable('libplugin')

plugin_dep  = plugin_p.get_variable('plugin_dep')

alias_target('build-libplugin', libplugin)
