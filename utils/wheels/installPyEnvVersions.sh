#!/bin/bash
# Install every interpreter the macOS arm64 build matrix iterates over.
# Run once before build-wheels-macos_aarch64.sh.

pyenv install -s 3.9.23
pyenv install -s 3.10.18
pyenv install -s 3.11.13
pyenv install -s 3.12.11
pyenv install -s 3.13.5
pyenv install -s 3.13.5t
pyenv install -s 3.14.0rc1
pyenv install -s 3.14.0rc1t
pyenv install -s 3.14-dev
pyenv install -s 3.14t-dev
pyenv install -s 3.15-dev
pyenv install -s 3.15t-dev
