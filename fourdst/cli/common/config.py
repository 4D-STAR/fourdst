# fourdst/cli/common/config.py

from pathlib import Path

FOURDST_CONFIG_DIR = Path.home() / ".config" / "fourdst"
LOCAL_TRUST_STORE_PATH = FOURDST_CONFIG_DIR / "keys"
CROSS_FILES_PATH = FOURDST_CONFIG_DIR / "cross"
CACHE_PATH = FOURDST_CONFIG_DIR / "cache"
ABI_CACHE_FILE = CACHE_PATH / "abi_identifier.json"
DOCKER_BUILD_IMAGES = {
    "x86_64 (manylinux_2_28)": "quay.io/pypa/manylinux_2_28_x86_64",
    "aarch64 (manylinux_2_28)": "quay.io/pypa/manylinux_2_28_aarch64",
    "i686 (manylinux_2_28)" : "quay.io/pypa/manylinux_2_28_i686",
    "ppc64le (manylinux_2_28)" : "quay.io/pypa/manylinux_2_28_ppc64le",
    "s390x (manylinux_2_28)" : "quay.io/pypa/manylinux_2_28_s390x"
}
