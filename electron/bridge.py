#!/usr/bin/env python3
"""
Electron Bridge Script for 4DSTAR Bundle Management

UPDATED ARCHITECTURE (2025-08-09):
=====================================

This bridge script has been simplified to work with the refactored core functions
that now return JSON directly. No more complex stdout mixing or data wrapping.

Key Changes:
- Core functions return JSON-serializable dictionaries directly
- Progress messages go to stderr only (never mixed with JSON output)
"""

import sys
import os
import json
import inspect
import traceback
from pathlib import Path
import datetime

# Custom JSON encoder to handle Path and datetime objects
class FourdstEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Path):
            return str(o)
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        return super().default(o)

# Add the project root to the Python path to allow importing 'fourdst'
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from fourdst.core import bundle, keys, plugin

def main():
    # Use stderr for all logging to avoid interfering with JSON output on stdout
    log_file = sys.stderr
    print("--- Python backend bridge started ---", file=log_file, flush=True)

    if len(sys.argv) < 3:
        print(f"FATAL: Not enough arguments provided. Got {len(sys.argv)}. Exiting.", file=log_file, flush=True)
        # Return JSON error even for argument errors
        error_response = {
            'success': False,
            'error': f'Invalid arguments. Expected: <command> <json_args>. Got {len(sys.argv)} args.'
        }
        print(json.dumps(error_response), flush=True)
        sys.exit(1)

    command = sys.argv[1]
    args_json = sys.argv[2]
    print(f"[BRIDGE_INFO] Received command: {command}", file=log_file, flush=True)
    print(f"[BRIDGE_INFO] Received raw args: {args_json}", file=log_file, flush=True)

    try:
        kwargs = json.loads(args_json)
        print(f"[BRIDGE_INFO] Parsed kwargs: {kwargs}", file=log_file, flush=True)

        # Convert path strings to Path objects where needed
        path_params = ['outputDir', 'output_dir', 'keyPath', 'key_path', 'bundlePath', 'bundle_path', 'path']
        for key, value in kwargs.items():
            if isinstance(value, str) and key in path_params:
                kwargs[key] = Path(value)
            elif isinstance(value, list) and 'dirs' in key.lower():
                kwargs[key] = [Path(p) for p in value]

        # Route commands to appropriate modules
        key_commands = [
            'list_keys', 'generate_key', 'add_key', 'remove_key', 
            'sync_remotes', 'get_remote_sources', 'add_remote_source', 'remove_remote_source'
        ]
        
        plugin_commands = [
            'parse_cpp_interface', 'generate_plugin_project', 'validate_bundle_directory',
            'pack_bundle_directory', 'extract_plugin_from_bundle', 'compare_plugin_sources',
            'validate_plugin_project'
        ]
        
        if command in key_commands:
            func = getattr(keys, command)
            module_name = "keys"
        elif command in plugin_commands:
            func = getattr(plugin, command)
            module_name = "plugin"
        else:
            func = getattr(bundle, command)
            module_name = "bundle"

        # Create progress callback that sends structured progress to stderr
        # This keeps progress separate from the final JSON result on stdout
        def progress_callback(message):
            # Progress goes to stderr to avoid mixing with JSON output
            if isinstance(message, dict):
                # Structured progress message (e.g., from fill_bundle)
                progress_msg = f"[PROGRESS] {json.dumps(message)}"
            else:
                # Simple string message
                progress_msg = f"[PROGRESS] {message}"
            print(progress_msg, file=log_file, flush=True)

        # Inspect the function signature to see if it accepts 'progress_callback'.
        sig = inspect.signature(func)
        if 'progress_callback' in sig.parameters:
            kwargs['progress_callback'] = progress_callback

        print(f"[BRIDGE_INFO] Calling function `{module_name}.{command}`...", file=log_file, flush=True)
        print(f"[BRIDGE_DEBUG] Function signature: {func.__name__}{inspect.signature(func)}", file=log_file, flush=True)
        print(f"[BRIDGE_DEBUG] Kwargs being passed: {kwargs}", file=log_file, flush=True)
        result = func(**kwargs)
        print(f"[BRIDGE_INFO] Function returned successfully.", file=log_file, flush=True)

        # Core functions now return JSON-serializable dictionaries directly
        # No need for wrapping or complex data transformation
        if result is None:
            # Fallback for functions that might still return None
            result = {
                'success': True,
                'message': f'{command} completed successfully.'
            }
        
        # Send the result directly as JSON to stdout
        print("[BRIDGE_INFO] Sending JSON response to stdout.", file=log_file, flush=True)
        json_response = json.dumps(result, cls=FourdstEncoder)
        print(json_response, flush=True)
        print("--- Python backend bridge finished successfully ---", file=log_file, flush=True)

    except Exception as e:
        # Get the full traceback for detailed debugging
        tb_str = traceback.format_exc()
        # Print the traceback to stderr so it appears in the terminal
        print(f"[BRIDGE_ERROR] Exception occurred: {tb_str}", file=sys.stderr, flush=True)
        
        # Send consistent JSON error response to stdout
        error_response = {
            'success': False,
            'error': f'Bridge error in {command}: {str(e)}',
            'traceback': tb_str  # Include traceback for debugging
        }
        json_response = json.dumps(error_response, cls=FourdstEncoder)
        print(json_response, flush=True)
        print("--- Python backend bridge finished with error ---", file=sys.stderr, flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
