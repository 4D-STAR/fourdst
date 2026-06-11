#!/usr/bin/env bash
set -euo pipefail

# Must be run on an aarch64 Linux host (uses docker so arm macos is fine so long as as the daemon is running)

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <git-repo-url>"
  echo "Example: $0 https://github.com/4D-STAR/fourdst"
  exit 1
fi

REPO_URL="$1"
WORK_DIR="$(pwd)"
WHEEL_DIR="${WORK_DIR}/wheels_linux_aarch64"

echo "➤ Creating wheel output directory at ${WHEEL_DIR}"
mkdir -p "${WHEEL_DIR}"

TMPDIR="$(mktemp -d)"
echo "➤ Cloning ${REPO_URL} → ${TMPDIR}/project"
git clone --depth 1 "${REPO_URL}" "${TMPDIR}/project"

IMAGE="tboudreaux/manylinux_2_28_aarch64_boost_1_88_0:latest"

docker run --rm \
  -v "${WHEEL_DIR}":/io/wheels \
  -v "${TMPDIR}/project":/io/project \
  "${IMAGE}" \
  /bin/bash -eux -c '
    cd /io/project
    RAW=/tmp/raw_wheels

    for PY in /opt/python/*/bin/python; do
      "$PY" -m pip install --upgrade pip

      rm -rf "$RAW"; mkdir -p "$RAW"

       CC=clang CXX=clang++ "$PY" -m pip wheel . \
        --no-deps \
        -w "$RAW" -vv

      for whl in "$RAW"/*.whl; do
        auditwheel repair "$whl" -w /io/wheels
      done
    done

    echo "Linux aarch64 wheels ready in /io/wheels"
  '

echo "Done. Repaired wheels in ${WHEEL_DIR}"
rm -rf "${TMPDIR}"
