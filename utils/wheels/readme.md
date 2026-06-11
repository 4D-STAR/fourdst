# Wheel Generation

This directory contains scripts to generate precompiled Python wheels for **fourdst**.

## Notes

- macOS wheels can only be generated on macOS.
- aarch64 wheels can only be generated on an aarch64 machine.
- x86_64 wheels can only be generated on an x86_64 machine.
- Linux wheels can be generated on any Linux machine, but the target architecture must match the host architecture (Docker runs natively, there is no emulation here).
- Running each script takes **a very long time** (potentially most of a day, depending on the machine) and needs roughly 2 GB of disk space.
- For the macOS build you must have all the listed Python versions installed via `pyenv`. Run `installPyEnvVersions.sh` first to install them.
- The old duplicate-RPATH workaround (`repair_wheel_macos.sh` + `fix_rpaths.py`) is **no longer needed** — the meson-python bug that caused it has been fixed, so the macOS script repairs with a plain `delocate-wheel` pass. Those two files can be deleted.

## Usage

Once you are on the correct machine, run the script for your target platform, passing the repository URL. For example, to build the macOS arm64 wheels:

```bash
./build-wheels-macos_aarch64.sh https://github.com/4D-STAR/fourdst
```

For Linux:

```bash
./build-wheels-linux_x86_64.sh  https://github.com/4D-STAR/fourdst   # on an x86_64 host
./build-wheels-linux_aarch64.sh https://github.com/4D-STAR/fourdst   # on an aarch64 host
```

Each script writes its repaired, redistributable wheels to a per-platform directory (e.g. `wheels_macos_aarch64/`, `wheels_linux_x86_64/`).

## Publishing

Once every platform's wheels are generated (which generally requires multiple machines), copy them all into a single directory — assume it is called `wheels/` at the repository root — then, from the repository root:

```bash
python -m pip install --upgrade build twine
python -m build --sdist --outdir wheels   # adds the source distribution
twine upload wheels/*
```

This uploads every wheel plus the sdist to PyPI (also slow, since it has to upload all of them).
