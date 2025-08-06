plugin_p = subproject('libplugin', default_options: ['pkg-config=' + pkg_config_bool_str, 'tests=' + get_option('tests').to_string()])
libplugin = plugin_p.get_variable('libplugin')

plugin_dep  = plugin_p.get_variable('plugin_dep')
