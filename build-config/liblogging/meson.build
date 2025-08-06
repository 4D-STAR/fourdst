logging_p = subproject('liblogging', default_options: ['pkg-config=' + pkg_config_bool_str])
liblogging = logging_p.get_variable('liblogging')

logging_dep  = logging_p.get_variable('logging_dep')
quill_dep = logging_p.get_variable('quill_dep')

log_dep = [logging_dep, quill_dep]

alias_target('build-liblogging', liblogging)