composition_p = subproject('libcomposition', default_options: ['pkg-config=' + pkg_config_bool_str])
comp_dep  = composition_p.get_variable('composition_dep')
libcomposition = composition_p.get_variable('libcomposition')
spw_dep = composition_p.get_variable('species_weight_dep')
composition_dep = [
    comp_dep,
    spw_dep,
]
