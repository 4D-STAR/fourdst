composition_p = subproject('libcomposition',
  default_options: [
    'pkg_config=' + get_option('pkg_config').to_string(),
    'build_tests=' + get_option('build_tests').to_string(),
    'build_examples=false'
])
comp_dep  = composition_p.get_variable('composition_dep')
libcomposition = composition_p.get_variable('libcomposition')
spw_dep = composition_p.get_variable('species_weight_dep')
composition_dep = [
    comp_dep,
    spw_dep,
]

alias_target('build-libcomposition', libcomposition)
