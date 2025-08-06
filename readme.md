# fourdst
A hub repository for 4D-STAR utility projects (such as libcomposition, libconfig, and liblogging)

The primary aims of this repository are two fold

1. Provide a unified location for 4D-STAR lib* repository versioning. That is to say that all projects which depend on lib* repositories in the 4D-STAR collaboration can depend on a specific version of fourdst which will itself depend on specific lib* repository versions.
2. Provide a set of unified python bindings for the lib* repositories. These are defined in `src-python` and can be installed with `pip install .` and then accessed as `from fourdst.composition import Composition`, etc...

# Installation
`fourdst` is intended to be installed using `pip` and `meson-python`

in order to install it you will need

- pip
- python3
- python3 development headers
- meson
- ninja
- cmake

If you have all of these dependencies 
