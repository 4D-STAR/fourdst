# fourdst/cli/keys/generate.py

import typer
from pathlib import Path
from fourdst.core.keys import generate_key

keys_app = typer.Typer()

@keys_app.command("generate")
def keys_generate(
    key_name: str = typer.Option("author_key", "--name", "-n", help="The base name for the generated key files."),
    key_type: str = typer.Option("ed25519", "--type", "-t", help="Type of key to generate (ed25519|rsa).", case_sensitive=False),
    output_dir: str = typer.Option(".", "--output", "-o", help="Directory to save the generated keys.")
):
    """
    Generates a new Ed25519 or RSA key pair for signing bundles.
    """
    def progress_callback(message):
        typer.echo(message)
    
    result = generate_key(
        key_name=key_name,
        key_type=key_type,
        output_dir=Path(output_dir),
        progress_callback=progress_callback
    )
    
    if result["success"]:
        typer.echo("\n✅ PEM and OpenSSH-compatible keys generated successfully!")
        typer.echo(f"  -> Private Key (KEEP SECRET): {result['private_key_path']}")
        typer.echo(f"  -> Public Key (SHARE): {result['public_key_path']}")
        typer.echo(f"  -> OpenSSH Public Key: {result['openssh_public_key_path']}")
        typer.echo(f"  -> Key Type: {result['key_type'].upper()}")
        typer.echo(f"  -> Fingerprint: {result['fingerprint']}")
        typer.echo("\nShare the public key with users who need to trust your bundles.")
    else:
        typer.secho(f"Error: {result['error']}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
