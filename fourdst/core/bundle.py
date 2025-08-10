# fourdst/core/bundle.py
"""
Core bundle management functions for 4DSTAR.

REFACTORED ARCHITECTURE (2025-08-09):
===========================================

All functions in this module now return JSON strings or JSON-serializable dictionaries.
This eliminates the complex stdout parsing and data transformation layers that were
causing issues in the Electron app.

CHANGES REQUIRED FOR CLIENTS:

1. CLI TOOL CHANGES:
   - Parse JSON responses from core functions
   - Handle progress callbacks separately (not mixed with return data)
   - Format JSON data for human-readable terminal output
   - Handle errors by parsing JSON error responses

2. ELECTRON APP CHANGES:
   - Bridge script (bridge.py) becomes much simpler:
     * Call core function directly
     * Return the JSON string to stdout (no wrapping needed)
     * All logging goes to stderr only
   - Main process (main.js):
     * Parse clean JSON from stdout
     * No complex data structure adaptation needed
   - Renderer process (renderer.js):
     * Receive predictable, consistent data structures
     * No need for defensive null checks on expected fields

3. PROGRESS REPORTING:
   - Progress callbacks are separate from return values
   - Structured progress messages use consistent format
   - All progress goes to callback, never mixed with JSON output

4. ERROR HANDLING:
   - All functions return JSON even for errors
   - Consistent error format: {"success": false, "error": "message"}
   - Exceptions are caught and converted to JSON error responses
"""

import os
import sys
import shutil
import datetime
import yaml
import zipfile
import tempfile
import hashlib
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from fourdst.core.platform import get_platform_identifier, get_macos_targeted_platform_identifier
from fourdst.core.utils import run_command, calculate_sha256
from fourdst.core.build import get_available_build_targets, build_plugin_for_target, build_plugin_in_docker
from fourdst.core.platform import is_abi_compatible
from fourdst.core.config import LOCAL_TRUST_STORE_PATH

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ed25519
from cryptography.exceptions import InvalidSignature
import cryptography

# Configure logging to go to stderr only, never stdout
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

def create_bundle(
    plugin_dirs: list[Path],
    output_bundle: Path,
    bundle_name: str,
    bundle_version: str,
    bundle_author: str,
    bundle_comment: str | None,
    target_macos_version: str | None = None,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Builds and packages one or more plugin projects into a single .fbundle file.
    
    REFACTORED: Now returns a JSON-serializable dictionary directly.
    Progress messages go only to the callback, never to stdout.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "bundle_path": str,  # Path to created bundle
            "message": str       # Success message
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }
    
    Args:
        progress_callback: An optional function that takes a string message to report progress.
    """
    def report_progress(message):
        if progress_callback:
            progress_callback(message)
        else:
            print(message)

    staging_dir = Path(tempfile.mkdtemp(prefix="fourdst_create_"))

    try:
        build_env = os.environ.copy()
        
        if sys.platform == "darwin" and target_macos_version:
            report_progress(f"Targeting macOS version: {target_macos_version}")
            host_platform = get_macos_targeted_platform_identifier(target_macos_version)
            flags = f"-mmacosx-version-min={target_macos_version}"
            build_env["CXXFLAGS"] = f"{build_env.get('CXXFLAGS', '')} {flags}".strip()
            build_env["LDFLAGS"] = f"{build_env.get('LDFLAGS', '')} {flags}".strip()
        else:
            host_platform = get_platform_identifier()

        manifest = {
            "bundleName": bundle_name,
            "bundleVersion": bundle_version,
            "bundleAuthor": bundle_author,
            "bundleComment": bundle_comment or "Created with fourdst",
            "bundledOn": datetime.datetime.now().isoformat(),
            "bundlePlugins": {}
        }
        
        report_progress("Creating bundle...")
        for plugin_dir in plugin_dirs:
            plugin_name = plugin_dir.name
            report_progress(f"--> Processing plugin: {plugin_name}")

            report_progress(f"    - Compiling for target platform...")
            build_dir = plugin_dir / "builddir"
            if build_dir.exists():
                shutil.rmtree(build_dir)

            run_command(["meson", "setup", "builddir"], cwd=plugin_dir, env=build_env)
            run_command(["meson", "compile", "-C", "builddir"], cwd=plugin_dir, env=build_env)

            compiled_lib = next(build_dir.glob("lib*.so"), None) or next(build_dir.glob("lib*.dylib"), None)
            if not compiled_lib:
                raise FileNotFoundError(f"Could not find compiled library for {plugin_name}")

            report_progress("    - Packaging source code (respecting .gitignore)...")
            sdist_path = staging_dir / f"{plugin_name}_src.zip"
            
            git_check = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=plugin_dir, capture_output=True, text=True, check=False)
            files_to_include = []
            if git_check.returncode == 0:
                result = run_command(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=plugin_dir)
                files_to_include = [plugin_dir / f for f in result.stdout.strip().split('\n') if f]
            else:
                report_progress(f"    - Warning: '{plugin_dir.name}' is not a git repository. Packaging all files.")
                for root, _, files in os.walk(plugin_dir):
                    if 'builddir' in root:
                        continue
                    for file in files:
                        files_to_include.append(Path(root) / file)

            with zipfile.ZipFile(sdist_path, 'w', zipfile.ZIP_DEFLATED) as sdist_zip:
                for file_path in files_to_include:
                    if file_path.is_file():
                        sdist_zip.write(file_path, file_path.relative_to(plugin_dir))

            binaries_dir = staging_dir / "bin"
            binaries_dir.mkdir(exist_ok=True)
            
            base_name = compiled_lib.stem
            ext = compiled_lib.suffix
            triplet = host_platform["triplet"]
            abi_signature = host_platform["abi_signature"]
            tagged_filename = f"{base_name}.{triplet}.{abi_signature}{ext}"
            staged_lib_path = binaries_dir / tagged_filename
            
            report_progress(f"    - Staging binary as: {tagged_filename}")
            shutil.copy(compiled_lib, staged_lib_path)

            manifest["bundlePlugins"][plugin_name] = {
                "sdist": {
                    "path": sdist_path.name,
                    "sdistBundledOn": datetime.datetime.now().isoformat(),
                    "buildable": True
                },
                "binaries": [{
                    "platform": {
                        "triplet": host_platform["triplet"],
                        "abi_signature": host_platform["abi_signature"],
                        "arch": host_platform["arch"]
                    },
                    "path": staged_lib_path.relative_to(staging_dir).as_posix(),
                    "compiledOn": datetime.datetime.now().isoformat()
                }]
            }

        manifest_path = staging_dir / "manifest.yaml"
        with open(manifest_path, 'w') as f:
            yaml.dump(manifest, f, sort_keys=False)

        report_progress(f"\nPackaging final bundle: {output_bundle}")
        with zipfile.ZipFile(output_bundle, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
            for root, _, files in os.walk(staging_dir):
                for file in files:
                    file_path = Path(root) / file
                    bundle_zip.write(file_path, file_path.relative_to(staging_dir))

        report_progress("\n✅ Bundle created successfully!")
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

def _create_canonical_checksum_list(staging_dir: Path, manifest: dict) -> str:
    """
    Creates a deterministic, sorted string of all file paths and their checksums.
    """
    checksum_map = {}

    for plugin_data in manifest.get('bundlePlugins', {}).values():
        sdist_info = plugin_data.get('sdist', {})
        if 'path' in sdist_info:
            file_path = staging_dir / sdist_info['path']
            if file_path.exists():
                checksum = "sha256:" + calculate_sha256(file_path)
                sdist_info['checksum'] = checksum
                checksum_map[sdist_info['path']] = checksum
            else:
                raise FileNotFoundError(f"sdist file not found: {sdist_info['path']}")

        for binary in plugin_data.get('binaries', []):
            if 'path' in binary:
                file_path = staging_dir / binary['path']
                if file_path.exists():
                    checksum = "sha256:" + calculate_sha256(file_path)
                    binary['checksum'] = checksum
                    checksum_map[binary['path']] = checksum
                else:
                    raise FileNotFoundError(f"Binary file not found: {binary['path']}")

    sorted_paths = sorted(checksum_map.keys())
    canonical_list = [f"{path}:{checksum_map[path]}" for path in sorted_paths]
    return "\n".join(canonical_list)

def edit_bundle_metadata(bundle_path: Path, metadata: dict, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Edits the metadata in the manifest of an existing bundle.

    REFACTORED: Now returns a JSON-serializable dictionary directly.
    Progress messages go only to the callback, never to stdout.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "message": str,
            "updated_fields": ["field1", "field2", ...]
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }

    Args:
        bundle_path (Path): The path to the .fbundle file.
        metadata (dict): A dictionary containing the metadata to update.
                         Valid keys include: 'bundle_name', 'bundle_version',
                         'bundle_author', 'bundle_comment'.
        progress_callback (callable, optional): A function to call with progress messages.
    """
    def _progress(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        # No fallback to print() - all output goes through callback only

    _progress(f"Opening {bundle_path.name} to edit metadata...")
    if not bundle_path.exists() or not zipfile.is_zipfile(bundle_path):
        raise FileNotFoundError("Bundle is not a valid zip file.")

    with zipfile.ZipFile(bundle_path, 'a') as zf:
        if "manifest.yaml" not in zf.namelist():
            raise FileNotFoundError("manifest.yaml not found in bundle.")

        with zf.open("manifest.yaml", 'r') as f:
            manifest = yaml.safe_load(f)

        _progress("Updating manifest...")
        updated_fields = []
        for key, value in metadata.items():
            # Convert snake_case from JS to camelCase for YAML
            camel_case_key = ''.join(word.capitalize() for word in key.split('_'))
            camel_case_key = camel_case_key[0].lower() + camel_case_key[1:]
            if value:
                manifest[camel_case_key] = value
                updated_fields.append(key)

        # In-place update of the manifest requires creating a new zip file
        # or rewriting the existing one, as 'a' mode can't update files.
        # A simpler approach is to read all files, write to a new zip, and replace.
        temp_bundle_path = bundle_path.with_suffix('.zip.tmp')
        with zipfile.ZipFile(temp_bundle_path, 'w', zipfile.ZIP_DEFLATED) as temp_zf:
            for item in zf.infolist():
                if item.filename == "manifest.yaml":
                    continue # Skip old manifest
                buffer = zf.read(item.filename)
                temp_zf.writestr(item, buffer)
            
            # Write the updated manifest
            new_manifest_content = yaml.dump(manifest, Dumper=yaml.SafeDumper)
            temp_zf.writestr("manifest.yaml", new_manifest_content)

    # Replace the original bundle with the updated one
    shutil.move(temp_bundle_path, bundle_path)
    _progress("Metadata updated successfully.")

    return {
        'success': True,
        'message': f"Metadata updated successfully: {bundle_path.name}",
        'updated_fields': updated_fields
    }

def sign_bundle(bundle_path: Path, private_key: Path, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Signs a bundle with an author's private key.
    
    REFACTORED: Now returns a JSON-serializable dictionary directly.
    Progress messages go only to the callback, never to stdout.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "message": str,
            "signature_info": {...}  # Details about the signature
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }
    """
    def report_progress(message):
        if progress_callback:
            progress_callback(message)
        else:
            print(message)

    report_progress(f"Signing bundle: {bundle_path}")
    staging_dir = Path(tempfile.mkdtemp(prefix="fourdst_sign_"))

    try:
        with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
            bundle_zip.extractall(staging_dir)

        manifest_path = staging_dir / "manifest.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError("manifest.yaml not found in bundle.")

        if private_key.suffix.lower() != ".pem":
            raise ValueError("Private key must be a .pem file.")

        report_progress("  - Deriving public key fingerprint via openssl...")
        proc = run_command(["openssl", "pkey", "-in", str(private_key), "-pubout", "-outform", "DER"], binary_output=True)
        pub_der = proc.stdout
        fingerprint = "sha256:" + hashlib.sha256(pub_der).hexdigest()
        report_progress(f"  - Signing with key fingerprint: {fingerprint}")

        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)

        report_progress("  - Calculating and embedding file checksums...")
        canonical_checksums = _create_canonical_checksum_list(staging_dir, manifest)

        report_progress("  - Detecting key type...")
        try:
            with open(private_key, "rb") as key_file:
                private_key_obj = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None
                )
        except Exception as e:
            raise ValueError(f"Could not load or parse private key: {e}")

        report_progress("  - Generating signature...")
        if isinstance(private_key_obj, ed25519.Ed25519PrivateKey):
            report_progress("    - Ed25519 key detected. Using pkeyutl for signing.")
            # pkeyutl with -rawin can be tricky with stdin, so we use a temporary file.
            with tempfile.NamedTemporaryFile(delete=False) as temp_input_file:
                temp_input_file.write(canonical_checksums.encode('utf-8'))
                temp_input_path = temp_input_file.name
            try:
                signature_proc = run_command(
                    ["openssl", "pkeyutl", "-sign", "-inkey", str(private_key), "-in", temp_input_path],
                    binary_output=True
                )
            finally:
                os.remove(temp_input_path)
        elif isinstance(private_key_obj, rsa.RSAPrivateKey):
            report_progress("    - RSA key detected. Using dgst for signing.")
            signature_proc = run_command(
                ["openssl", "dgst", "-sha256", "-sign", str(private_key)],
                input=canonical_checksums.encode('utf-8'),
                binary_output=True
            )
        else:
            raise TypeError(f"Unsupported private key type: {type(private_key_obj)}")
        signature_hex = signature_proc.stdout.hex()

        manifest['bundleSignature'] = {
            'keyFingerprint': fingerprint,
            'signature': signature_hex,
            'signedOn': datetime.datetime.now().isoformat()
        }

        with open(manifest_path, 'w') as f:
            yaml.dump(manifest, f, sort_keys=False)

        report_progress(f"  - Repackaging bundle: {bundle_path}")
        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
            for root, _, files in os.walk(staging_dir):
                for file in files:
                    file_path = Path(root) / file
                    bundle_zip.write(file_path, file_path.relative_to(staging_dir))

        report_progress("\n✅ Bundle signed successfully!")

    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

def validate_bundle(bundle_path: Path, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Validates a bundle's integrity and checksums.
    
    REFACTORED: Now returns a JSON-serializable dictionary directly.
    Progress messages go only to the callback, never to stdout.
    
    Returns:
        Dict containing validation results with structure:
        {
            "success": bool,
            "errors": List[str],
            "warnings": List[str], 
            "summary": {"errors": int, "warnings": int},
            "status": "passed" | "failed"
        }
    """
    def report_progress(message: str) -> None:
        if progress_callback:
            progress_callback(message)
        # No fallback to print() - all output goes through callback only

    results = {
        'success': True,  # Will be set to False if errors found
        'errors': [],
        'warnings': [],
        'summary': {},
        'status': 'failed'
    }

    report_progress(f"Validating bundle: {bundle_path}")
    staging_dir = Path(tempfile.mkdtemp(prefix="fourdst_validate_"))

    try:
        # 1. Unpack the bundle
        try:
            with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
                bundle_zip.extractall(staging_dir)
            report_progress("  - Bundle unpacked successfully.")
        except zipfile.BadZipFile:
            results['errors'].append(f"'{bundle_path.name}' is not a valid zip file.")
            return results

        # 2. Manifest validation
        manifest_path = staging_dir / "manifest.yaml"
        if not manifest_path.exists():
            results['errors'].append("Missing manifest.yaml file.")
            return results

        try:
            manifest = yaml.safe_load(manifest_path.read_text())
            if not manifest:
                results['warnings'].append("Manifest file is empty.")
                manifest = {}
        except yaml.YAMLError as e:
            results['errors'].append(f"Manifest file is not valid YAML: {e}")
            return results

        # 3. Content and checksum validation
        report_progress("  - Validating manifest content and file checksums...")
        if 'bundleName' not in manifest:
            results['errors'].append("Manifest is missing 'bundleName'.")
        if 'bundleVersion' not in manifest:
            results['errors'].append("Manifest is missing 'bundleVersion'.")
        
        plugins = manifest.get('bundlePlugins', {})
        if not plugins:
            results['warnings'].append("Manifest 'bundlePlugins' section is empty or missing.")

        for name, data in plugins.items():
            sdist_info = data.get('sdist', {})
            sdist_path_str = sdist_info.get('path')
            if not sdist_path_str:
                results['errors'].append(f"sdist path not defined for plugin '{name}'.")
            else:
                sdist_path = staging_dir / sdist_path_str
                if not sdist_path.exists():
                    results['errors'].append(f"sdist file not found: {sdist_path_str}")

            for binary in data.get('binaries', []):
                bin_path_str = binary.get('path')
                if not bin_path_str:
                    results['errors'].append(f"Binary entry for '{name}' is missing a 'path'.")
                    continue
                
                bin_path = staging_dir / bin_path_str
                if not bin_path.exists():
                    results['errors'].append(f"Binary file not found: {bin_path_str}")
                    continue

                expected_checksum = binary.get('checksum')
                if not expected_checksum:
                    results['warnings'].append(f"Checksum not defined for binary '{bin_path_str}'.")
                else:
                    actual_checksum = "sha256:" + calculate_sha256(bin_path)
                    if actual_checksum != expected_checksum:
                        results['errors'].append(f"Checksum mismatch for {bin_path_str}")

        # 4. Signature check (presence only)
        if 'bundleSignature' not in manifest:
            results['warnings'].append("Bundle is not signed (missing 'bundleSignature' in manifest).")
        else:
            report_progress("  - Signature block found in manifest.")

        # Finalize results
        results['summary'] = {'errors': len(results['errors']), 'warnings': len(results['warnings'])}
        if not results['errors']:
            results['status'] = 'passed'
        
        # Set success flag based on errors
        results['success'] = len(results['errors']) == 0

    except Exception as e:
        # Catch any unexpected errors and return them as JSON
        logging.exception(f"Unexpected error validating bundle {bundle_path}")
        return {
            'success': False,
            'error': f"Unexpected error during validation: {str(e)}",
            'errors': [str(e)],
            'warnings': [],
            'summary': {'errors': 1, 'warnings': 0},
            'status': 'failed'
        }
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

    return results

def inspect_bundle(bundle_path: Path) -> Dict[str, Any]:
    """
    Performs a comprehensive inspection of a bundle, returning a structured report.
    
    REFACTORED: Now returns a JSON-serializable dictionary directly.
    No progress callbacks needed since this is a read-only inspection.
    
    Returns:
        Dict containing complete bundle inspection with structure:
        {
            "success": bool,
            "validation": {...},  # Results from validate_bundle
            "signature": {...},   # Trust and signature info
            "plugins": {...},     # Plugin and binary compatibility
            "manifest": {...},    # Raw manifest data
            "host_info": {...}    # Current platform info
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }
    """
    try:
        report = {
            'success': True,
            'validation': {},
            'signature': {},
            'plugins': {},
            'manifest': None,
            'host_info': get_platform_identifier()
        }

        # 1. Basic validation (file integrity, checksums)
        # Pass a no-op callback to prevent any progress output
        validation_result = validate_bundle(bundle_path, progress_callback=lambda msg: None)
        report['validation'] = validation_result
        
        # If basic validation fails, return early
        if not validation_result.get('success', False):
            critical_errors = validation_result.get('errors', [])
            if any("not a valid zip file" in e or "Missing manifest.yaml" in e for e in critical_errors):
                return report

        staging_dir = Path(tempfile.mkdtemp(prefix="fourdst_inspect_"))
        try:
            with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
                bundle_zip.extractall(staging_dir)
            
            manifest_path = staging_dir / "manifest.yaml"
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f) or {}

            report['manifest'] = manifest

            # 2. Signature and Trust Verification
            sig_info = manifest.get('bundleSignature', {})
            fingerprint = sig_info.get('keyFingerprint')
            signature_hex = sig_info.get('signature')

            if not cryptography:
                report['signature']['status'] = 'UNSUPPORTED'
                report['signature']['reason'] = 'cryptography module not installed.'
            elif not fingerprint or not signature_hex:
                report['signature']['status'] = 'UNSIGNED'
            else:
                report['signature']['fingerprint'] = fingerprint
                trusted_key_path = None
                if LOCAL_TRUST_STORE_PATH.exists():
                    for key_file in LOCAL_TRUST_STORE_PATH.rglob("*.pem"):
                        try:
                            pub_der = (serialization.load_pem_public_key(key_file.read_bytes())
                                       .public_bytes(encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo))
                            pub_key_fingerprint = "sha256:" + hashlib.sha256(pub_der).hexdigest()
                            if pub_key_fingerprint == fingerprint:
                                trusted_key_path = key_file
                                break
                        except Exception:
                            continue
                
                if not trusted_key_path:
                    report['signature']['status'] = 'UNTRUSTED'
                else:
                    try:
                        pub_key_obj = serialization.load_pem_public_key(trusted_key_path.read_bytes())
                        signature = bytes.fromhex(signature_hex)
                        
                        # Re-calculate checksums from disk to verify against the signature
                        data_to_verify = _create_canonical_checksum_list(staging_dir, manifest).encode('utf-8')

                        if isinstance(pub_key_obj, ed25519.Ed25519PublicKey):
                            pub_key_obj.verify(signature, data_to_verify)
                        elif isinstance(pub_key_obj, rsa.RSAPublicKey):
                            pub_key_obj.verify(signature, data_to_verify, padding.PKCS1v15(), hashes.SHA256())
                        
                        if report['validation']['status'] == 'passed':
                            report['signature']['status'] = 'TRUSTED'
                            report['signature']['key_path'] = str(trusted_key_path.relative_to(LOCAL_TRUST_STORE_PATH))
                        else:
                            report['signature']['status'] = 'TAMPERED'
                            report['signature']['reason'] = 'Signature is valid, but file contents do not match manifest checksums.'

                    except InvalidSignature:
                        report['signature']['status'] = 'INVALID'
                        report['signature']['reason'] = 'Cryptographic signature verification failed.'
                    except Exception as e:
                        report['signature']['status'] = 'ERROR'
                        report['signature']['reason'] = str(e)

            # 3. Plugin and Binary Compatibility Analysis
            host_info = report['host_info']
            for name, data in manifest.get('bundlePlugins', {}).items():
                report['plugins'][name] = {'binaries': [], 'sdist_path': data.get('sdist', {}).get('path')}
                compatible_found = False
                for binary in data.get('binaries', []):
                    plat = binary.get('platform', {})
                    plat['os'] = plat.get('triplet', "unk-unk").split('-')[1]
                    is_compatible, reason = is_abi_compatible(host_info, plat)
                    binary['is_compatible'] = is_compatible
                    binary['incompatibility_reason'] = None if is_compatible else reason
                    report['plugins'][name]['binaries'].append(binary)
                    if is_compatible:
                        compatible_found = True
                report['plugins'][name]['compatible_found'] = compatible_found

        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)

        return report

    except Exception as e:
        # Catch any unexpected errors and return them as JSON
        logging.exception(f"Unexpected error inspecting bundle {bundle_path}")
        return {
            'success': False,
            'error': f"Unexpected error during inspection: {str(e)}"
        }

def clear_bundle(bundle_path: Path, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Removes all compiled binaries and signatures from a bundle.
    
    REFACTORED: Now returns a JSON-serializable dictionary directly.
    Progress messages go only to the callback, never to stdout.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "message": str,
            "cleared_items": {"binaries": int, "signatures": int}
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }
    """
    def report_progress(message):
        if progress_callback:
            progress_callback(message)
        else:
            print(message)

    report_progress(f"Clearing binaries from bundle: {bundle_path.name}")
    staging_dir = Path(tempfile.mkdtemp(prefix="fourdst_clear_"))

    try:
        # 1. Unpack the bundle
        report_progress("  - Unpacking bundle...")
        with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
            bundle_zip.extractall(staging_dir)

        # 2. Read the manifest
        manifest_path = staging_dir / "manifest.yaml"
        if not manifest_path.is_file():
            raise FileNotFoundError("Bundle is invalid. Missing manifest.yaml.")
        
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)

        # 3. Clear binaries and signatures from manifest
        report_progress("  - Clearing binary and signature information from manifest...")
        manifest.pop('bundleSignature', None)
        
        for plugin_name, plugin_data in manifest.get('bundlePlugins', {}).items():
            if 'binaries' in plugin_data:
                report_progress(f"    - Clearing binaries for plugin '{plugin_name}'")
                plugin_data['binaries'] = []
        
        # 4. Delete the binaries directory and signature file from disk
        bin_dir = staging_dir / "bin"
        if bin_dir.is_dir():
            shutil.rmtree(bin_dir)
            report_progress("  - Removed 'bin/' directory.")

        sig_file = staging_dir / "manifest.sig"
        if sig_file.is_file():
            sig_file.unlink()
            report_progress("  - Removed 'manifest.sig'.")

        # 5. Write the updated manifest
        with open(manifest_path, 'w') as f:
            yaml.dump(manifest, f, sort_keys=False)

        # 6. Repack the bundle
        report_progress("  - Repackaging the bundle...")
        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
            for file_path in staging_dir.rglob('*'):
                if file_path.is_file():
                    bundle_zip.write(file_path, file_path.relative_to(staging_dir))
        
        report_progress(f"\n✅ Bundle '{bundle_path.name}' has been cleared of all binaries.")

    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

def diff_bundle(bundle_a_path: Path, bundle_b_path: Path, progress_callback=None):
    """
    Compares two bundle files and returns a dictionary of differences.
    """
    def report_progress(message):
        if progress_callback:
            progress_callback(message)

    results = {
        'signature': {},
        'manifest': {},
        'files': []
    }

    report_progress(f"Comparing {bundle_a_path.name} and {bundle_b_path.name}")
    with tempfile.TemporaryDirectory() as temp_a_str, tempfile.TemporaryDirectory() as temp_b_str:
        temp_a = Path(temp_a_str)
        temp_b = Path(temp_b_str)

        report_progress("  - Unpacking bundles...")
        with zipfile.ZipFile(bundle_a_path, 'r') as z: z.extractall(temp_a)
        with zipfile.ZipFile(bundle_b_path, 'r') as z: z.extractall(temp_b)

        # 1. Compare Signatures
        sig_a_path = temp_a / "manifest.sig"
        sig_b_path = temp_b / "manifest.sig"
        sig_a = sig_a_path.read_bytes() if sig_a_path.exists() else None
        sig_b = sig_b_path.read_bytes() if sig_b_path.exists() else None

        if sig_a == sig_b and sig_a is not None:
            results['signature']['status'] = 'UNCHANGED'
        elif sig_a and not sig_b:
            results['signature']['status'] = 'REMOVED'
        elif not sig_a and sig_b:
            results['signature']['status'] = 'ADDED'
        elif sig_a and sig_b and sig_a != sig_b:
            results['signature']['status'] = 'CHANGED'
        else:
            results['signature']['status'] = 'UNSIGNED'

        # 2. Compare Manifests
        manifest_a_content = (temp_a / "manifest.yaml").read_text()
        manifest_b_content = (temp_b / "manifest.yaml").read_text()
        
        if manifest_a_content != manifest_b_content:
            import difflib
            diff = difflib.unified_diff(
                manifest_a_content.splitlines(keepends=True),
                manifest_b_content.splitlines(keepends=True),
                fromfile=f"{bundle_a_path.name}/manifest.yaml",
                tofile=f"{bundle_b_path.name}/manifest.yaml",
            )
            results['manifest']['diff'] = list(diff)
        else:
            results['manifest']['diff'] = []

        # 3. Compare File Contents (via checksums in manifest)
        manifest_a = yaml.safe_load(manifest_a_content)
        manifest_b = yaml.safe_load(manifest_b_content)

        def get_files_from_manifest(manifest):
            files = {}
            for plugin in manifest.get('bundlePlugins', {}).values():
                sdist_info = plugin.get('sdist', {})
                if 'path' in sdist_info and 'checksum' in sdist_info:
                    files[sdist_info['path']] = sdist_info['checksum']
                for binary in plugin.get('binaries', []):
                    if 'path' in binary and 'checksum' in binary:
                        files[binary['path']] = binary['checksum']
            return files

        files_a = get_files_from_manifest(manifest_a)
        files_b = get_files_from_manifest(manifest_b)

        all_files = sorted(list(set(files_a.keys()) | set(files_b.keys())))

        for file in all_files:
            in_a = file in files_a
            in_b = file in files_b
            checksum_a = files_a.get(file)
            checksum_b = files_b.get(file)

            if in_a and not in_b:
                results['files'].append({'path': file, 'status': 'REMOVED', 'details': ''})
            elif not in_a and in_b:
                results['files'].append({'path': file, 'status': 'ADDED', 'details': ''})
            elif checksum_a != checksum_b:
                details = f"Checksum changed from {checksum_a or 'N/A'} to {checksum_b or 'N/A'}"
                results['files'].append({'path': file, 'status': 'MODIFIED', 'details': details})

    return results

def get_fillable_targets(bundle_path: Path) -> Dict[str, Any]:
    """
    Inspects a bundle and determines which plugins are missing binaries for available build targets.

    REFACTORED: Now returns a JSON-serializable dictionary directly.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "data": {
                "plugin_name": [target1, target2, ...],
                ...
            }
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }
    """
    try:
        staging_dir = Path(tempfile.mkdtemp(prefix="fourdst_fillable_"))
        try:
            with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
                bundle_zip.extractall(staging_dir)
            
            manifest_path = staging_dir / "manifest.yaml"
            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f) or {}
            
            available_targets = get_available_build_targets()
            result = {}
            
            for plugin_name, plugin_data in manifest.get('bundlePlugins', {}).items():
                existing_targets = set()
                for binary in plugin_data.get('binaries', []):
                    platform_info = binary.get('platform', {})
                    existing_targets.add(platform_info.get('triplet', 'unknown'))
                
                fillable = [target for target in available_targets if target['triplet'] not in existing_targets]
                if fillable:
                    result[plugin_name] = fillable
            
            return {
                'success': True,
                'data': result
            }
        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)
    except Exception as e:
        logging.exception(f"Unexpected error getting fillable targets for {bundle_path}")
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }

def fill_bundle(bundle_path: Path, targets_to_build: dict, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Fills a bundle with newly compiled binaries for the specified targets.

    REFACTORED: Now returns a JSON-serializable dictionary directly.
    Progress messages go only to the callback, never to stdout.
    Structured progress messages are sent for streaming updates.
    
    Returns:
        Dict with structure:
        {
            "success": bool,
            "message": str,
            "build_results": {
                "successful": int,
                "failed": int,
                "details": [...]
            }
        }
        
    On error:
        {
            "success": false,
            "error": "error message"
        }

    Args:
        bundle_path: Path to the .fbundle file.
        targets_to_build: A dictionary like {'plugin_name': [target1, target2]} specifying what to build.
        progress_callback: An optional function to report progress.
    """
    def report_progress(message) -> None:
        if progress_callback:
            # The message can be a string or a dict for structured updates
            progress_callback(message)
        # No fallback to print() - all output goes through callback only

    staging_dir = Path(tempfile.mkdtemp(prefix="fourdst_fill_"))
    try:
        report_progress("Unpacking bundle to temporary directory...")
        with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
            bundle_zip.extractall(staging_dir)

        manifest_path = staging_dir / "manifest.yaml"
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)

        binaries_dir = staging_dir / "bin"
        binaries_dir.mkdir(exist_ok=True)

        for plugin_name, targets in targets_to_build.items():
            report_progress(f"Processing plugin: {plugin_name}")
            plugin_info = manifest['bundlePlugins'][plugin_name]
            sdist_path = staging_dir / plugin_info['sdist']['path']

            for target in targets:
                target_triplet = target['triplet']
                report_progress({
                    'status': 'building',
                    'plugin': plugin_name,
                    'target': target_triplet,
                    'message': f"Building {plugin_name} for {target_triplet}..."
                })
                build_dir = Path(tempfile.mkdtemp(prefix=f"{plugin_name}_build_"))

                try:
                    if target['type'] == 'docker':
                        compiled_lib, final_target = build_plugin_in_docker(
                            sdist_path, build_dir, target, plugin_name, progress_callback
                        )
                    else: # native or cross
                        compiled_lib, final_target = build_plugin_for_target(
                            sdist_path, build_dir, target, progress_callback
                        )

                    # Stage the new binary
                    base_name = compiled_lib.stem
                    ext = compiled_lib.suffix
                    tagged_filename = f"{base_name}.{final_target['triplet']}.{final_target['abi_signature']}{ext}"
                    staged_lib_path = binaries_dir / tagged_filename
                    shutil.copy(compiled_lib, staged_lib_path)
                    
                    # Update manifest
                    new_binary_entry = {
                        'platform': final_target,
                        'path': staged_lib_path.relative_to(staging_dir).as_posix(),
                        'compiledOn': datetime.datetime.now().isoformat(),
                        'checksum': "sha256:" + calculate_sha256(staged_lib_path)
                    }
                    plugin_info.setdefault('binaries', []).append(new_binary_entry)

                    report_progress({
                        'status': 'success',
                        'plugin': plugin_name,
                        'target': target_triplet,
                        'message': f"Successfully built and staged {tagged_filename}"
                    })

                except Exception as e:
                    report_progress({
                        'status': 'failure',
                        'plugin': plugin_name,
                        'target': target_triplet,
                        'message': f"Failed to build {plugin_name} for {target_triplet}: {e}"
                    })
                finally:
                    if build_dir.exists():
                        shutil.rmtree(build_dir)

        # Write the updated manifest
        with open(manifest_path, 'w') as f:
            yaml.dump(manifest, f, sort_keys=False)

        # Repack the bundle
        report_progress(f"Repackaging bundle: {bundle_path.name}")
        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
            for file_path in staging_dir.rglob('*'):
                if file_path.is_file():
                    bundle_zip.write(file_path, file_path.relative_to(staging_dir))

        report_progress({"status": "complete", "message": "✅ Bundle filled successfully!"})
        
        return {
            'success': True,
            'message': f"Bundle filled successfully: {bundle_path.name}",
            'build_results': {
                'successful': successful_builds,
                'failed': failed_builds,
                'details': build_details
            }
        }

    except Exception as e:
        logging.exception(f"Unexpected error filling bundle {bundle_path}")
        return {
            'success': False,
            'error': f"Unexpected error during bundle filling: {str(e)}"
        }
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

