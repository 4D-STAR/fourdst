# fourdst/cli/bundle/inspect.py

import typer
import sys
import shutil
import yaml
import zipfile
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ed25519
from cryptography.exceptions import InvalidSignature

from fourdst.cli.common.config import LOCAL_TRUST_STORE_PATH
from fourdst.cli.common.utils import get_platform_identifier, calculate_sha256, is_abi_compatible

bundle_app = typer.Typer()

def _reconstruct_canonical_checksum_list(staging_dir: Path, manifest: dict) -> tuple[str, list[str], list[str]]:
    """
    Reconstructs the canonical checksum list from the files on disk
    and compares them against the checksums listed in the manifest.

    Returns a tuple containing:
    1. The canonical string of actual checksums to verify against the signature.
    2. A list of files with checksum mismatches.
    3. A list of files that are listed in the manifest but missing from the disk.
    """
    checksum_map = {}
    mismatch_errors = []
    missing_files = []

    all_files_in_manifest = []
    # Gather all file paths from the manifest
    for plugin_data in manifest.get('bundlePlugins', {}).values():
        if 'sdist' in plugin_data and 'path' in plugin_data['sdist']:
            all_files_in_manifest.append(plugin_data['sdist'])
        if 'binaries' in plugin_data:
            all_files_in_manifest.extend(plugin_data['binaries'])

    for file_info in all_files_in_manifest:
        path_str = file_info.get('path')
        if not path_str:
            continue

        file_path = staging_dir / path_str
        expected_checksum = file_info.get('checksum')

        if not file_path.exists():
            missing_files.append(path_str)
            continue

        # Calculate actual checksum from the file on disk
        actual_checksum = "sha256:" + calculate_sha256(file_path)
        checksum_map[path_str] = actual_checksum

        # Compare with the checksum listed in the manifest
        if expected_checksum and actual_checksum != expected_checksum:
            mismatch_errors.append(path_str)

    # Create the canonical string for signature verification from the actual file checksums
    sorted_paths = sorted(checksum_map.keys())
    canonical_list = [f"{path}:{checksum_map[path]}" for path in sorted_paths]
    data_to_verify = "\n".join(canonical_list)

    return data_to_verify, mismatch_errors, missing_files


@bundle_app.command("inspect")
def bundle_inspect(bundle_path: Path = typer.Argument(..., help="The .fbundle file to inspect.", exists=True)):
    """
    Inspects a bundle, validating its contents and cryptographic signature.
    """
    staging_dir = Path(f"temp_inspect_{bundle_path.stem}")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    
    try:
        host_platform = get_platform_identifier()

        with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
            bundle_zip.extractall(staging_dir)

        manifest_path = staging_dir / "manifest.yaml"
        if not manifest_path.exists():
            typer.secho("Error: Bundle is invalid. Missing manifest.yaml.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)

        typer.secho(f"--- Bundle Inspection Report for: {bundle_path.name} ---", bold=True)
        # ... (header printing code is unchanged) ...
        typer.echo(f"Name:     {manifest.get('bundleName', 'N/A')}")
        typer.echo(f"Version:  {manifest.get('bundleVersion', 'N/A')}")
        typer.echo(f"Author:   {manifest.get('bundleAuthor', 'N/A')}")
        typer.echo(f"Bundled:  {manifest.get('bundledOn', 'N/A')}")
        typer.secho(f"Host ABI: {host_platform['abi_signature']}", dim=True)
        typer.secho(f"Host Arch: {host_platform['triplet']}", dim=True)
        typer.echo("-" * 50)


        # 3. Signature and Trust Verification
        fingerprint = manifest.get('bundleAuthorKeyFingerprint')
        sig_path = staging_dir / "manifest.sig"
        
        if not fingerprint or not sig_path.exists():
            typer.secho("Trust Status: 🟡 UNSIGNED", fg=typer.colors.YELLOW)
        else:
            trusted_key_path = None
            if LOCAL_TRUST_STORE_PATH.exists():
                # Find the key in the local trust store
                # ... (key finding logic is unchanged) ...
                for key_file in LOCAL_TRUST_STORE_PATH.rglob("*.pem"):
                    try:
                        pub_der = (serialization.load_pem_public_key(key_file.read_bytes())
                                   .public_bytes(
                                       encoding=serialization.Encoding.DER,
                                       format=serialization.PublicFormat.SubjectPublicKeyInfo
                                   ))
                        pub_key_fingerprint = "sha256:" + hashlib.sha256(pub_der).hexdigest()
                        if pub_key_fingerprint == fingerprint:
                            trusted_key_path = key_file
                            break
                    except Exception:
                        continue
            
            if not trusted_key_path:
                typer.secho(f"Trust Status: ⚠️ SIGNED but UNTRUSTED AUTHOR ({fingerprint})", fg=typer.colors.YELLOW)
            else:
                # --- MODIFIED VERIFICATION LOGIC ---
                try:
                    pub_key_obj = serialization.load_pem_public_key(trusted_key_path.read_bytes())
                    signature = sig_path.read_bytes()
                    
                    # Reconstruct the data that was originally signed
                    data_to_verify, checksum_errors, missing_files = _reconstruct_canonical_checksum_list(staging_dir, manifest)
                    with open("data_to_verify.bin", "wb") as f:
                        f.write(data_to_verify.encode('utf-8'))

                    # Verify the signature against the reconstructed data
                    if isinstance(pub_key_obj, ed25519.Ed25519PublicKey):
                        pub_key_obj.verify(signature, data_to_verify.encode('utf-8'))
                    elif isinstance(pub_key_obj, rsa.RSAPublicKey):
                         pub_key_obj.verify(
                            signature,
                            data_to_verify.encode('utf-8'),
                            padding.PKCS1v15(),
                            hashes.SHA256()
                        )
                    
                    # If we reach here, the signature is cryptographically valid.
                    # Now we check if the manifest's checksums match the actual file checksums.
                    if checksum_errors or missing_files:
                         typer.secho(f"Trust Status: ❌ INVALID - Files have been tampered with after signing.", fg=typer.colors.RED)
                         for f in missing_files:
                             typer.echo(f"  - Missing file listed in manifest: {f}")
                         for f in checksum_errors:
                             typer.echo(f"  - Checksum mismatch for: {f}")
                    else:
                        typer.secho(f"Trust Status: ✅ SIGNED and TRUSTED ({trusted_key_path.relative_to(LOCAL_TRUST_STORE_PATH)})", fg=typer.colors.GREEN)

                except InvalidSignature:
                    typer.secho(f"Trust Status: ❌ INVALID SIGNATURE - The bundle's integrity is compromised.", fg=typer.colors.RED)
        
        typer.echo("-" * 50)
        
        # ... (Plugin Details section is unchanged) ...
        typer.secho("Available Plugins:", bold=True)
        for plugin_name, plugin_data in manifest.get('bundlePlugins', {}).items():
            typer.echo(f"\n  Plugin: {plugin_name}")
            typer.echo(f"    Source Dist: {plugin_data.get('sdist', {}).get('path', 'N/A')}")
            binaries = plugin_data.get('binaries', [])
            
            host_compatible_binary_found = False
            if not binaries:
                typer.echo("    Binaries: None")
            else:
                typer.echo("    Binaries:")
                for b in binaries:
                    plat = b.get('platform', {})
                    is_compatible = (plat.get('triplet') == host_platform['triplet'] and 
                                     is_abi_compatible(host_platform['abi_signature'], plat.get('abi_signature', '')))
                    
                    color = typer.colors.GREEN if is_compatible else None
                    if is_compatible:
                        host_compatible_binary_found = True

                    typer.secho(f"      - Path: {b.get('path', 'N/A')}", fg=color)
                    typer.secho(f"        ABI:  {plat.get('abi_signature', 'N/A')}", fg=color, dim=True)
                    typer.secho(f"        Arch: {plat.get('triplet', 'N/A')}", fg=color, dim=True)

            if not host_compatible_binary_found:
                typer.secho(
                    f"    Note: No compatible binary found for the current system ({host_platform['triplet']}).",
                    fg=typer.colors.YELLOW
                )
                typer.secho(
                    "    Run 'fourdst-cli bundle fill' to build one.",
                    fg=typer.colors.YELLOW
                )

    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
