# fourdst/cli/bundle/inspect.py

import typer
import sys
import shutil
import yaml
import zipfile
import hashlib
from pathlib import Path

try:
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa, ed25519
    from cryptography.exceptions import InvalidSignature
except ImportError:
    print("Error: This CLI now requires 'cryptography'. Please install it.", file=sys.stderr)
    print("Run: pip install cryptography", file=sys.stderr)
    sys.exit(1)

from fourdst.cli.common.config import LOCAL_TRUST_STORE_PATH
from fourdst.cli.common.utils import get_platform_identifier, calculate_sha256, is_abi_compatible

bundle_app = typer.Typer()

@bundle_app.command("inspect")
def bundle_inspect(bundle_path: Path = typer.Argument(..., help="The .fbundle file to inspect.", exists=True)):
    """
    Inspects a bundle, validating its contents and cryptographic signature.
    """
    staging_dir = Path(f"temp_inspect_{bundle_path.stem}")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    
    try:
        # Get current system info first
        host_platform = get_platform_identifier()

        # 1. Unpack and load manifest
        with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
            archive_files = set(bundle_zip.namelist())
            bundle_zip.extractall(staging_dir)

        manifest_path = staging_dir / "manifest.yaml"
        if not manifest_path.exists():
            typer.secho("Error: Bundle is invalid. Missing manifest.yaml.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)

        # 2. Print Header
        typer.secho(f"--- Bundle Inspection Report for: {bundle_path.name} ---", bold=True)
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
            # Find the key in the local trust store
            trusted_key_path = None
            if LOCAL_TRUST_STORE_PATH.exists():
                for key_file in LOCAL_TRUST_STORE_PATH.rglob("*.pub"):
                    pub_key = serialization.load_ssh_public_key(key_file.read_bytes())
                    pub_key_bytes = pub_key.public_bytes(
                        encoding = serialization.Encoding.OpenSSH,
                        format = serialization.PublicFormat.OpenSSH
                    )
                    pub_key_fingerprint = "sha256:" + hashlib.sha256(pub_key_bytes).hexdigest()
                    if pub_key_fingerprint == fingerprint:
                        trusted_key_path = key_file
                        break
            
            if not trusted_key_path:
                typer.secho(f"Trust Status: ⚠️ SIGNED but UNTRUSTED AUTHOR ({fingerprint})", fg=typer.colors.YELLOW)
            else:
                try:
                    pub_key_obj = serialization.load_ssh_public_key(trusted_key_path.read_bytes())
                    signature = sig_path.read_bytes()
                    manifest_content = manifest_path.read_bytes()

                    if isinstance(pub_key_obj, ed25519.Ed25519PublicKey):
                        pub_key_obj.verify(signature, manifest_content)
                    elif isinstance(pub_key_obj, rsa.RSAPublicKey):
                         pub_key_obj.verify(
                            signature,
                            manifest_content,
                            padding.PKCS1v15(),
                            hashes.SHA256()
                        )
                    typer.secho(f"Trust Status: ✅ SIGNED and TRUSTED ({trusted_key_path.relative_to(LOCAL_TRUST_STORE_PATH)})", fg=typer.colors.GREEN)
                except InvalidSignature:
                    typer.secho(f"Trust Status: ❌ INVALID SIGNATURE ({fingerprint})", fg=typer.colors.RED)
        
        typer.echo("-" * 50)

        # 4. Content Validation
        typer.echo("Validating bundle contents...")
        missing_files = []
        checksum_errors = []

        for plugin_name, plugin_data in manifest.get('bundlePlugins', {}).items():
            sdist_path = plugin_data.get('sdist', {}).get('path')
            if sdist_path and sdist_path not in archive_files:
                missing_files.append(sdist_path)
            
            for binary in plugin_data.get('binaries', []):
                binary_path_str = binary.get('path')
                if binary_path_str and binary_path_str not in archive_files:
                    missing_files.append(binary_path_str)
                elif binary_path_str:
                    # Verify checksum if present
                    expected_checksum = binary.get('checksum')
                    if expected_checksum:
                        actual_checksum = "sha256:" + calculate_sha256(staging_dir / binary_path_str)
                        if actual_checksum != expected_checksum:
                            checksum_errors.append(binary_path_str)

        if not missing_files and not checksum_errors:
            typer.secho("Content Validation: ✅ OK", fg=typer.colors.GREEN)
        else:
            typer.secho("Content Validation: ❌ FAILED", fg=typer.colors.RED)
            for f in missing_files:
                typer.echo(f"  - Missing file from archive: {f}")
            for f in checksum_errors:
                typer.echo(f"  - Checksum mismatch for: {f}")

        # 5. Plugin Details
        typer.echo("-" * 50)
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
