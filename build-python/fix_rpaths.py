#!/usr/bin/env python3

import os
import sys
import glob
import subprocess
from collections import OrderedDict

def get_rpaths(binary_path):
    """Uses otool to extract a list of all LC_RPATH entries."""
    print(f"--- Checking rpaths for: {binary_path}")
    rpaths = []
    try:
        proc = subprocess.run(
            ['otool', '-l', binary_path],
            capture_output=True,
            text=True,
            check=True
        )

        lines = proc.stdout.splitlines()
        for i, line in enumerate(lines):
            if "cmd LC_RPATH" in line.strip():
                if i + 2 < len(lines):
                    path_line = lines[i + 2].strip()
                    if path_line.startswith("path "):
                        # Extract the path, e.g., "path /foo/bar (offset 12)"
                        rpath = path_line.split(" ")[1]
                        rpaths.append(rpath)

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error running otool: {e}")
        return []

    return rpaths

def fix_rpaths(binary_path):
    all_rpaths = get_rpaths(binary_path)
    if not all_rpaths:
        print("--- No rpaths found or otool failed.")
        return

    unique_rpaths = list(OrderedDict.fromkeys(all_rpaths))
    for rpath in unique_rpaths:
        print(f" - RPATH: {rpath}")

    if len(all_rpaths) == len(unique_rpaths):
        print("--- No duplicate rpaths found. Nothing to do.")
        return

    print(f"--- Found {len(all_rpaths)} rpaths; {len(unique_rpaths)} are unique.")
    print(f"--- Fixing duplicates in: {binary_path}")

    try:
        for rpath in all_rpaths:
            subprocess.run(
                ['install_name_tool', '-delete_rpath', rpath, binary_path],
                check=True,
                capture_output=True
            )

        for rpath in unique_rpaths:
            subprocess.run(
                ['install_name_tool', '-add_rpath', rpath, binary_path],
                check=True,
                capture_output=True
            )

        print("--- Successfully fixed rpaths.")

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"--- Error running install_name_tool: {e}")
        if e.stderr:
            print(f"STDERR: {e.stderr.decode()}")
        if e.stdout:
            print(f"STDOUT: {e.stdout.decode()}")
        sys.exit(1) # Fail the install if we can't fix it

def main():
    if len(sys.argv) != 2:
        print(f"--- Error: Expected one argument (path to .so file), got {sys.argv}", file=sys.stderr)
        sys.exit(1)

    # Get the file path directly from the command line argument
    so_file_path = sys.argv[1]

    if not os.path.exists(so_file_path):
        print(f"--- Error: File not found at {so_file_path}", file=sys.stderr)
        sys.exit(1)

    print(f"--- Fixing rpaths for built file: {so_file_path}")
    fix_rpaths(so_file_path)

if __name__ == "__main__":
    main()