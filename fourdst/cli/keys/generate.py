# fourdst/cli/keys/generate.py

import typer
import sys
from pathlib import Path
from fourdst.cli.common.utils import run_command

keys_app = typer.Typer()

@keys_app.command("generate")
def keys_generate(
    key_name: str = typer.Option("author_key", "--name", "-n", help="The base name for the generated key files.")
):
    """
    Generates a new Ed25519 key pair for signing bundles.
    """
    private_key_path = Path(f"{key_name}")
    public_key_path = Path(f"{key_name}.pub")

    if private_key_path.exists() or public_key_path.exists():
        print(f"Error: Key files '{private_key_path}' or '{public_key_path}' already exist.", file=sys.stderr)
        raise typer.Exit(code=1)

    print("Generating Ed25519 key pair...")
    run_command([
        "ssh-keygen",
        "-t", "ed25519",
        "-f", str(private_key_path),
        "-N", "", # No passphrase
        "-C", "fourdst bundle signing key"
    ])
    print("\n✅ Keys generated successfully!")
    print(f"  -> Private Key (KEEP SECRET): {private_key_path.resolve()}")
    print(f"  -> Public Key (SHARE): {public_key_path.resolve()}")
    print("\nShare the public key with users who need to trust your bundles.")
