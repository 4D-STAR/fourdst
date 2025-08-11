# --- Python Extension Setup ---
py_installation = import('python').find_installation('python3')

py_mod = py_installation.extension_module(
    'fourdst', # Name of the generated .so/.pyd file (without extension)
    sources: [
        meson.project_source_root() + '/src-pybind/bindings.cpp',
        meson.project_source_root() + '/src-pybind/composition/bindings.cpp',
        meson.project_source_root() + '/src-pybind/constants/bindings.cpp',
        meson.project_source_root() + '/src-pybind/config/bindings.cpp',
    ],
    dependencies : [
        pybind11_dep,
        const_dep,
        config_dep,
        composition_dep,
    ],
    cpp_args : ['-UNDEBUG'],
    install : true,
)

py_installation.install_sources(
    meson.project_source_root() + '/fourdst/__init__.py',
    subdir: 'fourdst',
)
py_installation.install_sources(
    files(
        meson.project_source_root() + '/fourdst/cli/__init__.py',
        meson.project_source_root() + '/fourdst/cli/main.py',
    ),
    subdir: 'fourdst/cli',
)
py_installation.install_sources(
    files(
        meson.project_source_root() + '/fourdst/cli/templates/meson.build.in',
        meson.project_source_root() + '/fourdst/cli/templates/plugin.cpp.in',
    ),
    subdir: 'fourdst/cli/templates',
)
py_installation.install_sources(
    files(
        meson.project_source_root() + '/fourdst/cli/bundle/__init__.py',
        meson.project_source_root() + '/fourdst/cli/bundle/create.py',
        meson.project_source_root() + '/fourdst/cli/bundle/fill.py',
        meson.project_source_root() + '/fourdst/cli/bundle/inspect.py',
        meson.project_source_root() + '/fourdst/cli/bundle/sign.py',
        meson.project_source_root() + '/fourdst/cli/bundle/clear.py',
        meson.project_source_root() + '/fourdst/cli/bundle/diff.py',
        meson.project_source_root() + '/fourdst/cli/bundle/validate.py',
    ),
    subdir: 'fourdst/cli/bundle'
)
py_installation.install_sources(
    files(
        meson.project_source_root() + '/fourdst/cli/cache/__init__.py',
        meson.project_source_root() + '/fourdst/cli/cache/clear.py'
    ),
    subdir: 'fourdst/cli/cache'
)
py_installation.install_sources(
    files(
        meson.project_source_root() + '/fourdst/cli/common/__init__.py',
        meson.project_source_root() + '/fourdst/cli/common/config.py',
        meson.project_source_root() + '/fourdst/cli/common/templates.py',
        meson.project_source_root() + '/fourdst/cli/common/utils.py',
    ),
    subdir: 'fourdst/cli/common'
)
py_installation.install_sources(
    files(
        meson.project_source_root() + '/fourdst/cli/keys/__init__.py',
        meson.project_source_root() + '/fourdst/cli/keys/generate.py',
        meson.project_source_root() + '/fourdst/cli/keys/sync.py',
        meson.project_source_root() + '/fourdst/cli/keys/add.py',
        meson.project_source_root() + '/fourdst/cli/keys/list.py',
        meson.project_source_root() + '/fourdst/cli/keys/remove.py',
    ),
    subdir: 'fourdst/cli/keys'
)
py_installation.install_sources(
    files(
        meson.project_source_root() + '/fourdst/cli/keys/remote/__init__.py',
        meson.project_source_root() + '/fourdst/cli/keys/remote/add.py',
        meson.project_source_root() + '/fourdst/cli/keys/remote/list.py',
        meson.project_source_root() + '/fourdst/cli/keys/remote/remove.py',
    ),
    subdir: 'fourdst/cli/keys/remote'
)
py_installation.install_sources(
    files(
        meson.project_source_root() + '/fourdst/cli/plugin/__init__.py',
        meson.project_source_root() + '/fourdst/cli/plugin/init.py',
        meson.project_source_root() + '/fourdst/cli/plugin/pack.py',
        meson.project_source_root() + '/fourdst/cli/plugin/extract.py',
        meson.project_source_root() + '/fourdst/cli/plugin/diff.py',
        meson.project_source_root() + '/fourdst/cli/plugin/validate.py',
    ),
    subdir: 'fourdst/cli/plugin'
)

py_installation.install_sources(
    files(
        meson.project_source_root() + '/fourdst/core/__init__.py',
        meson.project_source_root() + '/fourdst/core/build.py',
        meson.project_source_root() + '/fourdst/core/bundle.py',
        meson.project_source_root() + '/fourdst/core/config.py',
        meson.project_source_root() + '/fourdst/core/platform.py',
        meson.project_source_root() + '/fourdst/core/utils.py',
        meson.project_source_root() + '/fourdst/core/keys.py',
    ),
    subdir: 'fourdst/core'
)

py_installation.install_sources(
    files(
        meson.project_source_root() + '/electron/bridge.py',
    ),
    subdir: 'fourdst/electron'
)
