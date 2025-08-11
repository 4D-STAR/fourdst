project('fourdst', 'cpp', version: 'v0.6.1', default_options: ['cpp_std=c++23'], meson_version: '>=1.5.0')

add_project_arguments('-fvisibility=default', language: 'cpp')

pkg_config_bool_str = 'false'
if get_option('pkg-config')
    pkg_config_bool_str = 'true'
endif


# Configure vendor libraries
subdir('build-config')

# Configure python bindings
subdir('build-python')

# Build python bindings
subdir('src-pybind')

# Bundle the Python backend for the Electron app

if get_option('build-py-backend')
  pyinstaller_exe = find_program('pyinstaller', required : true)
  electron_src_dir = meson.current_source_dir() / 'electron'

  custom_target('fourdst-backend',
    input : electron_src_dir / 'fourdst-backend.spec',
    # The output is the directory that PyInstaller creates.
    # We are interested in the executable inside it.
    output : 'fourdst-backend',
    # The command to run. We tell PyInstaller where to put the final executable.
    command : [pyinstaller_exe, '--distpath', meson.current_build_dir() / 'electron/dist', '--workpath', meson.current_build_dir() / 'electron/build', '--noconfirm', '@INPUT@'],
    # This ensures the backend is built whenever you run 'meson compile'.
    build_by_default : true
  )
endif

