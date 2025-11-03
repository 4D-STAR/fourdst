# fourdst/cli/keys/sync.py
import typer
import questionary

from fourdst.core.keys import sync_remotes, remove_remote_source

keys_app = typer.Typer()

@keys_app.command("sync")
def keys_sync():
    """
    Syncs the local trust store with all configured remote Git repositories.
    """
    def progress_callback(message):
        typer.echo(message)
    
    result = sync_remotes(progress_callback=progress_callback)
    
    if not result["success"]:
        typer.secho(f"Error: {result['error']}", fg=typer.colors.YELLOW)
        raise typer.Exit()
    
    # Display results
    success_count = len([r for r in result["synced_remotes"] if r["status"] == "success"])
    failed_count = len([r for r in result["synced_remotes"] if r["status"] == "failed"])
    
    typer.echo(f"\nSync completed:")
    typer.echo(f"  ✅ Successful: {success_count}")
    typer.echo(f"  ❌ Failed: {failed_count}")
    typer.echo(f"  📦 Total keys synced: {result['total_keys_synced']}")
    
    # Show details for each remote
    for remote_info in result["synced_remotes"]:
        if remote_info["status"] == "success":
            typer.secho(f"  ✅ {remote_info['name']}: {remote_info.get('keys_count', 0)} keys", fg=typer.colors.GREEN)
        else:
            typer.secho(f"  ❌ {remote_info['name']}: {remote_info['error']}", fg=typer.colors.RED)
    
    # Handle removed remotes
    if result["removed_remotes"]:
        typer.secho(f"\nRemoved failing remotes: {', '.join(result['removed_remotes'])}", fg=typer.colors.YELLOW)
    
    # Ask about failed remotes that weren't automatically removed
    failed_remotes = [r for r in result["synced_remotes"] if r["status"] == "failed" and r["name"] not in result["removed_remotes"]]
    for remote_info in failed_remotes:
        if questionary.confirm(f"Do you want to remove the failing remote '{remote_info['name']}'?").ask():
            remove_result = remove_remote_source(remote_info['name'])
            if remove_result["success"]:
                typer.secho(f"✅ Removed remote '{remote_info['name']}'", fg=typer.colors.GREEN)
            else:
                typer.secho(f"❌ Failed to remove remote '{remote_info['name']}': {remove_result['error']}", fg=typer.colors.RED)

