# fourdst/cli/bundle/sign.py

import typer
import shutil
import yaml
import zipfile
import hashlib
from pathlib import Path
import sys

try:
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa, ed25519
except ImportError:
    print("Error: This CLI now requires 'cryptography'. Please install it.", file=sys.stderr)
    print("Run: pip install cryptography", file=sys.stderr)
    sys.exit(1)

from fourdst.cli.common.utils import calculate_sha256

bundle_app = typer.Typer()

@bundle_app.command("sign")
def bundle_sign(
    bundle_path: Path = typer.Argument(..., help="The .fbundle file to sign.", exists=True),
    private_key: Path = typer.Option(..., "--key", "-k", help="Path to the author's private signing key.", exists=True)
):
    """
    Signs a bundle with an author's private key, adding checksums and a signature.
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

    # 2. Load private key and derive public key to get fingerprint
    with open(private_key, "rb") as key_file:
        priv_key_obj = serialization.load_ssh_private_key(key_file.read(), password=None)
    
    pub_key_obj = priv_key_obj.public_key()
    pub_key_bytes = pub_key_obj.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )
    fingerprint = "sha256:" + hashlib.sha256(pub_key_bytes).hexdigest()
    print(f"  - Signing with key fingerprint: {fingerprint}")

    # 3. Update manifest with checksums and fingerprint
    with open(manifest_path, 'r') as f:
        manifest = yaml.safe_load(f)

    manifest['bundleAuthorKeyFingerprint'] = fingerprint
    for plugin in manifest['bundlePlugins'].values():
        for binary in plugin.get('binaries', []):
            binary_path = staging_dir / binary['path']
            if binary_path.exists():
                 binary['checksum'] = "sha256:" + calculate_sha256(binary_path)
            else:
                 binary['checksum'] = "MISSING_FILE"


    with open(manifest_path, 'w') as f:
        yaml.dump(manifest, f, sort_keys=False)
    print("  - Added file checksums and key fingerprint to manifest.")

    # 4. Sign the manifest
    manifest_content = manifest_path.read_bytes()
    
    if isinstance(priv_key_obj, ed25519.Ed25519PrivateKey):
        signature = priv_key_obj.sign(manifest_content)
    elif isinstance(priv_key_obj, rsa.RSAPrivateKey):
        signature = priv_key_obj.sign(
            manifest_content,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    else:
        print("Error: Unsupported private key type for signing.", file=sys.stderr)
        raise typer.Exit(code=1)


    sig_path = staging_dir / "manifest.sig"
    sig_path.write_bytes(signature)
    print("  - Created manifest.sig.")

    # 5. Repackage the bundle
    with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as bundle_zip:
        for file_path in staging_dir.rglob('*'):
            if file_path.is_file():
                bundle_zip.write(file_path, file_path.relative_to(staging_dir))

    shutil.rmtree(staging_dir)
    print("\n✅ Bundle signed successfully!")
