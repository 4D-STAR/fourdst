logging_p = subproject('liblogging', default_options: ['pkg-config=false'])
liblogging = logging_p.get_variable('liblogging')

logging_dep  = logging_p.get_variable('logging_dep')
quill_dep = logging_p.get_variable('quill_dep')

log_dep = [logging_dep, quill_dep]
