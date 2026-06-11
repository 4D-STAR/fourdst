#!/usr/bin/env bash
set -euo pipefail

# Must be run on an Apple Silicon (arm64) Mac.

if [[ $(uname -m) != "arm64" ]]; then
  echo "Error: This script is intended to run on an Apple Silicon (arm64) Mac."
  exit 1
fi

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <git-repo-url>"
  echo "Example: $0 https://github.com/4D-STAR/fourdst"
  exit 1
fi

REPO_URL="$1"
WORK_DIR="$(pwd)"
WHEEL_DIR="${WORK_DIR}/wheels_macos_aarch64_tmp"
FINAL_WHEEL_DIR="${WORK_DIR}/wheels_macos_aarch64"

echo "➤ Creating wheel output directories"
mkdir -p "${WHEEL_DIR}"
mkdir -p "${FINAL_WHEEL_DIR}"

TMPDIR="$(mktemp -d)"
echo "➤ Cloning ${REPO_URL} → ${TMPDIR}/project"
git clone --depth 1 "${REPO_URL}" "${TMPDIR}/project"
cd "${TMPDIR}/project"

export MACOSX_DEPLOYMENT_TARGET=15.0

PYTHON_VERSIONS=("3.9.23" "3.10.18" "3.11.13" "3.12.11" "3.13.5" "3.13.5t" "3.14.0rc1" "3.14.0rc1t" 'pypy3.10-7.3.19' "pypy3.11-7.3.20")

if ! command -v pyenv &> /dev/null; then
    echo "Error: pyenv not found. Please install it to manage Python versions."
    echo "       Then run installPyEnvVersions.sh to install the interpreters above."
    exit 1
fi
eval "$(pyenv init -)"

for PY_VERSION in "${PYTHON_VERSIONS[@]}"; do
  (
    set -e

    pyenv shell "${PY_VERSION}"
    PY="$(pyenv which python)"

    echo "----------------------------------------------------------------"
    echo "➤ Building for $($PY --version) on macOS arm64"
    echo "----------------------------------------------------------------"

    "$PY" -m pip install --upgrade pip
    "$PY" -m pip install "meson>=1.9.1,<1.10" "meson-python>=0.19,<0.20" "pybind11>=2.10" delocate

    echo "➤ Building wheel with ccache enabled"
    echo "➤ Found meson version $(meson --version)"

    CC="ccache clang" CXX="ccache clang++" "$PY" -m pip wheel . \
      --no-deps --no-build-isolation -w "${WHEEL_DIR}" -v

    CURRENT_WHEEL=$(find "${WHEEL_DIR}" -name "*.whl" | head -n 1)

    echo "➤ Repairing wheel with delocate"
    delocate-wheel -w "${FINAL_WHEEL_DIR}" "$CURRENT_WHEEL"

    rm "$CURRENT_WHEEL"
  )
done

rm -rf "${TMPDIR}"
rm -rf "${WHEEL_DIR}"

echo "➤ All builds complete. Artifacts in ${FINAL_WHEEL_DIR}"
