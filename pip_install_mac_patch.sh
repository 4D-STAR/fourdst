#!/bin/bash
# pip_install_mac.sh - Temporary workaround for meson-python duplicate RPATH bug on macOS

set -e

# Color codes for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${YELLOW}"
echo "========================================================================="
echo "                    TEMPORARY INSTALLATION WORKAROUND"
echo "========================================================================="
echo -e "${NC}"
echo ""
echo -e "${YELLOW}WARNING:${NC} This script applies a temporary patch to fix a known issue with"
echo "meson-python that causes duplicate RPATH entries in built Python extensions"
echo "on macOS, preventing module imports."
echo ""
echo "This workaround will:"
echo "  1. Install fourdst using pip"
echo "  2. Locate the installed extension module"
echo "  3. Remove duplicate RPATH entries using install_name_tool"
echo ""
echo "This is a temporary solution while the meson-python team resolves the"
echo "duplicate RPATH bug. For more information, see:"
echo "  https://github.com/mesonbuild/meson-python/issues/813"
echo ""
echo -e "${YELLOW}Do you understand and wish to continue? [y/N]${NC} "
read -r response

if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo -e "${RED}Installation cancelled.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Step 1: Finding current Python environment...${NC}"

# Get the current Python executable
PYTHON_BIN=$(which python3)
if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}Error: python3 not found in PATH${NC}"
    exit 1
fi

echo "Using Python: $PYTHON_BIN"
PYTHON_VERSION=$($PYTHON_BIN --version)
echo "Python version: $PYTHON_VERSION"

# Get site-packages directory
SITE_PACKAGES=$($PYTHON_BIN -c "import site; print(site.getsitepackages()[0])")
echo "Site packages: $SITE_PACKAGES"
echo ""

echo -e "${GREEN}Step 2: Installing fourdst with pip...${NC}"
$PYTHON_BIN -m pip install . -v

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: pip install failed${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}Step 3: Locating installed extension module...${NC}"

# Find the .so file
SO_FILE=$(find "$SITE_PACKAGES/fourdst" -name "_phys.cpython-*-darwin.so" 2>/dev/null | head -n 1)

if [ -z "$SO_FILE" ]; then
    echo -e "${RED}Error: Could not find _phys.cpython-*-darwin.so in $SITE_PACKAGES/fourdst${NC}"
    echo "Installation may have failed or the file is in an unexpected location."
    exit 1
fi

echo "Found extension module: $SO_FILE"
echo ""

echo -e "${GREEN}Step 4: Running RPATH fix script...${NC}"

# Check if fix_rpath.py exists
FIX_SCRIPT="build-python/fix_rpaths.py"
if [ ! -f "$FIX_SCRIPT" ]; then
    echo -e "${RED}Error: $FIX_SCRIPT not found${NC}"
    echo "Please ensure you're running this script from the project root directory."
    exit 1
fi

# Run the fix script
$PYTHON_BIN "$FIX_SCRIPT" "$SO_FILE"

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: RPATH fix script failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=========================================================================${NC}"
echo -e "${GREEN}                    Installation Complete!${NC}"
echo -e "${GREEN}=========================================================================${NC}"
echo ""
echo "You can now use fourdst in your Python environment."
echo ""
echo "Test the installation with:"
echo "  $PYTHON_BIN -c 'import fourdst; print(fourdst.__version__)'"
echo ""
echo -e "${YELLOW}Note:${NC} If you reinstall or upgrade fourdst, you will need to run this"
echo "script again to apply the RPATH fix."
echo ""