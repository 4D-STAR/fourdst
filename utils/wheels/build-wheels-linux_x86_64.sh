#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <git-repo-url>"
  echo "Example: $0 https://github.com/4D-STAR/fourdst"
  exit 1
fi

REPO_URL="$1"
WORK_DIR="$(pwd)"
WHEEL_DIR="${WORK_DIR}/wheels_linux_x86_64"

echo "➤ Creating wheel output directory at ${WHEEL_DIR}"
mkdir -p "${WHEEL_DIR}"

TMPDIR="$(mktemp -d)"
echo "➤ Cloning ${REPO_URL} → ${TMPDIR}/project"
git clone --depth 1 "${REPO_URL}" "${TMPDIR}/project"

IMAGE="tboudreaux/manylinux_2_28_x86_64_boost_1_88_0:latest"

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
        --config-settings=setup-args=-Dunity=on \
        -w "$RAW" -vv

      # Repair only the freshly built wheel into the shared output dir.
      for whl in "$RAW"/*.whl; do
        auditwheel repair "$whl" -w /io/wheels
      done
    done

    echo "Linux x86_64 wheels ready in /io/wheels"
  '

echo "Done. Repaired wheels in ${WHEEL_DIR}"
rm -rf "${TMPDIR}"
