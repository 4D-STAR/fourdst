# fourdst/cli/keys/generate.py

import typer
import sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives import serialization

keys_app = typer.Typer()

@keys_app.command("generate")
def keys_generate(
    key_name: str = typer.Option("author_key", "--name", "-n", help="The base name for the generated key files."),
    key_type: str = typer.Option("ed25519", "--type", "-t", help="Type of key to generate (ed25519|rsa).", case_sensitive=False)
):
    """
    Generates a new Ed25519 or RSA key pair for signing bundles.
    """
    # Define PEM-formatted key file paths
    private_key_path = Path(f"{key_name}.pem")
    public_key_path = Path(f"{key_name}.pub.pem")

    if private_key_path.exists() or public_key_path.exists():
        print(f"Error: Key files '{private_key_path}' or '{public_key_path}' already exist.", file=sys.stderr)
        raise typer.Exit(code=1)

    # Generate key based on requested type
    if key_type.lower() == "ed25519":
        typer.echo("Generating Ed25519 key pair in PEM format via cryptography...")
        private_key_obj = ed25519.Ed25519PrivateKey.generate()
    elif key_type.lower() == "rsa":
        typer.echo("Generating RSA-2048 key pair in PEM format via cryptography...")
        private_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    else:
        typer.secho(f"Unsupported key type: {key_type}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    # Serialize private key to PEM
    priv_pem = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    private_key_path.write_bytes(priv_pem)
    # Derive and serialize public key to PEM
    public_key_obj = private_key_obj.public_key()
    pub_pem = public_key_obj.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    public_key_path.write_bytes(pub_pem)
    # Also write OpenSSH-compatible public key
    openssh_pub = public_key_obj.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )
    Path(f"{key_name}.pub").write_bytes(openssh_pub)
    print("\n✅ PEM and OpenSSH-compatible keys generated successfully!")
    print(f"  -> Private Key (KEEP SECRET): {private_key_path.resolve()}")
    print(f"  -> Public Key (SHARE): {public_key_path.resolve()}")
    print("\nShare the public key with users who need to trust your bundles.")
