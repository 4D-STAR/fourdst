# fourdst/cli/cache/clear.py

import typer
import shutil
from fourdst.cli.common.config import CACHE_PATH
import typer

cache_app = typer.Typer()

@cache_app.command("clear")
def cache_clear():
    """
    Clears all cached data, including the ABI signature.
    Run this if you have updated your C++ compiler.
    """
    if CACHE_PATH.exists():
        shutil.rmtree(CACHE_PATH)
        print("✅ Local cache cleared.")
    else:
        print("No cache found to clear.")
