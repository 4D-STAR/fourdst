# fourdst/cli/main.py

import typer
from pathlib import Path

from fourdst.cli.common.config import CACHE_PATH

from fourdst.cli.bundle.create import bundle_create
from fourdst.cli.bundle.fill import bundle_fill
from fourdst.cli.bundle.sign import bundle_sign
from fourdst.cli.bundle.inspect import bundle_inspect
from fourdst.cli.bundle.clear import bundle_clear
from fourdst.cli.bundle.diff import bundle_diff
from fourdst.cli.bundle.validate import bundle_validate

from fourdst.cli.plugin.init import plugin_init
from fourdst.cli.plugin.pack import plugin_pack
from fourdst.cli.plugin.extract import plugin_extract
from fourdst.cli.plugin.diff import plugin_diff
from fourdst.cli.plugin.validate import plugin_validate

from fourdst.cli.cache.clear import cache_clear

from fourdst.cli.keys.generate import keys_generate
from fourdst.cli.keys.sync import keys_sync
from fourdst.cli.keys.add import keys_add
from fourdst.cli.keys.remove import keys_remove
from fourdst.cli.keys.list import keys_list

from fourdst.cli.keys.remote.add import remote_add
from fourdst.cli.keys.remote.list import remote_list
from fourdst.cli.keys.remote.remove import remote_remove


app = typer.Typer(
    name="fourdst-cli",
    help="A command-line tool for managing fourdst projects, plugins, and bundles."
)

plugin_app = typer.Typer(name="plugin", help="Commands for managing individual fourdst plugins.")
bundle_app = typer.Typer(name="bundle", help="Commands for creating, signing, and managing plugin bundles.")
cache_app = typer.Typer(name="cache", help="Commands for managing the local cache.")

keys_app = typer.Typer(name="keys", help="Commands for cryptographic key generation and management.")
remote_app = typer.Typer(name="remote", help="Manage remote git repositories for public keys.")

# Add commands to their respective apps
plugin_app.command("init")(plugin_init)
plugin_app.command("pack")(plugin_pack)
plugin_app.command("extract")(plugin_extract)
plugin_app.command("validate")(plugin_validate)
plugin_app.command("diff")(plugin_diff)

bundle_app.command("create")(bundle_create)
bundle_app.command("fill")(bundle_fill)
bundle_app.command("sign")(bundle_sign)
bundle_app.command("inspect")(bundle_inspect)
bundle_app.command("clear")(bundle_clear)
bundle_app.command("diff")(bundle_diff)
bundle_app.command("validate")(bundle_validate)

cache_app.command("clear")(cache_clear)


keys_app.add_typer(remote_app)

keys_app.command("generate")(keys_generate)
keys_app.command("sync")(keys_sync)
keys_app.command("add")(keys_add)
keys_app.command("remove")(keys_remove)
keys_app.command("list")(keys_list)

remote_app.command("add")(remote_add)
remote_app.command("list")(remote_list)
remote_app.command("remove")(remote_remove)


# Add the sub-apps to the main app
app.add_typer(plugin_app, name="plugin")
app.add_typer(bundle_app, name="bundle")
app.add_typer(keys_app, name="keys")
app.add_typer(cache_app, name="cache")

def main():
    # Create config directory if it doesn't exist
    CACHE_PATH.mkdir(parents=True, exist_ok=True)
    app()

if __name__ == "__main__":
    main()
