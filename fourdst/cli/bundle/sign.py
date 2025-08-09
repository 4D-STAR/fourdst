# fourdst/cli/bundle/sign.py

import typer
import shutil
import yaml
import zipfile
import hashlib
from pathlib import Path
import sys
import subprocess

from fourdst.cli.common.utils import calculate_sha256

bundle_app = typer.Typer()

def _create_canonical_checksum_list(staging_dir: Path, manifest: dict) -> str:
    """
    Creates a deterministic, sorted string of all file paths and their checksums.
    This string is the actual data that will be signed.
    """
    checksum_map = {}

    # Iterate through all plugins to find all files to be checksummed
    for plugin_data in manifest.get('bundlePlugins', {}).values():
        # Add sdist (source code zip) to the list
        sdist_info = plugin_data.get('sdist', {})
        if 'path' in sdist_info:
            file_path = staging_dir / sdist_info['path']
            if file_path.exists():
                checksum = "sha256:" + calculate_sha256(file_path)
                # Also update the manifest with the sdist checksum
                sdist_info['checksum'] = checksum
                checksum_map[sdist_info['path']] = checksum
            else:
                # This case should ideally be caught by a validation step
                typer.secho(f"Warning: sdist file not found: {sdist_info['path']}", fg=typer.colors.YELLOW)


        # Add all binaries to the list
        for binary in plugin_data.get('binaries', []):
            if 'path' in binary:
                file_path = staging_dir / binary['path']
                if file_path.exists():
                    checksum = "sha256:" + calculate_sha256(file_path)
                    # Update the manifest with the binary checksum
                    binary['checksum'] = checksum
                    checksum_map[binary['path']] = checksum
                else:
                    typer.secho(f"Warning: Binary file not found: {binary['path']}", fg=typer.colors.YELLOW)

    # Sort the file paths to ensure a deterministic order
    sorted_paths = sorted(checksum_map.keys())

    # Create the final canonical string (e.g., "path1:checksum1\npath2:checksum2")
    canonical_list = [f"{path}:{checksum_map[path]}" for path in sorted_paths]
    
    return "\n".join(canonical_list)


@bundle_app.command("sign")
def bundle_sign(
    bundle_path: Path = typer.Argument(..., help="The .fbundle file to sign.", exists=True),
    private_key: Path = typer.Option(..., "--key", "-k", help="Path to the author's private signing key.", exists=True)
):
    """
    Signs a bundle with an author's private key.

    This process calculates checksums for all source and binary files,
    adds them to the manifest, and then signs a canonical list of these
    checksums to ensure the integrity of the entire bundle.
    """
    print(f"Signing bundle: {bundle_path}")
    staging_dir = Path("temp_sign_staging")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)

    # 1. Unpack the bundle
    with zipfile.ZipFile(bundle_path, 'r') as bundle_zip:
        bundle_zip.extractall(staging_dir)

    manifest_path = staging_dir / "manifest.yaml"
    if not manifest_path.exists():
        print("Error: manifest.yaml not found in bundle.", file=sys.stderr)
        raise typer.Exit(code=1)

    # 2. Ensure PEM private key and derive public key fingerprint via openssl
    if private_key.suffix.lower() != ".pem":
        typer.secho("Error: Private key must be a .pem file.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.echo("  - Deriving public key fingerprint via openssl...")
    try:
        proc = subprocess.run(
            ["openssl", "pkey", "-in", str(private_key), "-pubout", "-outform", "DER"],
            capture_output=True, check=True
        )
        pub_der = proc.stdout
        fingerprint = "sha256:" + hashlib.sha256(pub_der).hexdigest()
        typer.echo(f"  - Signing with key fingerprint: {fingerprint}")
    except subprocess.CalledProcessError as e:
        typer.secho(f"Error extracting public key: {e.stderr.decode().strip()}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 3. Load manifest and generate the canonical checksum list
    with open(manifest_path, 'r') as f:
        manifest = yaml.safe_load(f)

    print("  - Calculating checksums for all source and binary files...")
    # This function now also modifies the manifest in-place to add the checksums
    data_to_sign = _create_canonical_checksum_list(staging_dir, manifest)
    
    # Add the key fingerprint to the manifest
    manifest['bundleAuthorKeyFingerprint'] = fingerprint

    # 4. Write the updated manifest back to the staging directory
    with open(manifest_path, 'w') as f:
        yaml.dump(manifest, f, sort_keys=False)
    print("  - Added file checksums and key fingerprint to manifest.")

    # 5. Sign the canonical checksum list
    typer.echo("  - Signing the canonical checksum list...")
    canonical_temp_data_file = staging_dir / "canonical_checksums.txt"
    canonical_temp_data_file.write_text(data_to_sign, encoding='utf-8')
    sig_path = staging_dir / "manifest.sig"
    try:
        # We sign the string data directly, not the manifest file
        cmd_list = [
            "openssl",
            "pkeyutl",
            "-sign",
            "-in", str(canonical_temp_data_file),
            "-inkey", str(private_key),
            "-out", str(sig_path)
            ]
        subprocess.run(
            cmd_list,
            check=True,
            capture_output=True
        )
        typer.echo(f"  - Created manifest.sig (> $ {' '.join(cmd_list)} ")
    except subprocess.CalledProcessError as e:
        typer.secho(f"Error signing manifest: {e.stderr.decode().strip()}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 6. Repackage the bundle
    with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
        for file_path in staging_dir.rglob('*'):
            if file_path.is_file():
                bundle_zip.write(file_path, file_path.relative_to(staging_dir))

    shutil.rmtree(staging_dir)
    print("\n✅ Bundle signed successfully!")
