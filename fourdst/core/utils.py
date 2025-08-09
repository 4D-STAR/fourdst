# fourdst/core/utils.py

import subprocess
from pathlib import Path
import hashlib

def run_command(command: list[str], cwd: Path = None, check=True, progress_callback=None, input: bytes = None, env: dict = None, binary_output: bool = False):
    """Runs a command, optionally reporting progress and using a custom environment."""
    command_str = ' '.join(command)
    if progress_callback:
        progress_callback(f"Running command: {command_str}")

    try:
        result = subprocess.run(
            command, 
            check=check, 
            capture_output=True, 
            text=not binary_output, 
            input=input,
            cwd=cwd, 
            env=env
        )
        
        if progress_callback and result.stdout:
            if binary_output:
                progress_callback(f"  - STDOUT: <binary data>")
            else:
                progress_callback(f"  - STDOUT: {result.stdout.strip()}")
        if progress_callback and result.stderr:
            progress_callback(f"  - STDERR: {result.stderr.strip()}")

        return result
    except subprocess.CalledProcessError as e:
        error_message = f"""Command '{command_str}' failed with exit code {e.returncode}.\n--- STDOUT ---\n{e.stdout.strip()}\n--- STDERR ---\n{e.stderr.strip()}\n"""
        if progress_callback:
            progress_callback(error_message)
        if check:
            raise Exception(error_message) from e
        return e

def calculate_sha256(file_path: Path) -> str:
    """Calculates the SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
