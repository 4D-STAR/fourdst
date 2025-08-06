# fourdst/cli/plugin/validate.py
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

def plugin_validate(
    plugin_path: Path = typer.Argument(
        ".",
        help="The path to the plugin directory to validate.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True
    )
):
    """
    Validates a plugin's structure and meson.build file.
    """
    console.print(Panel(f"Validating Plugin: [bold]{plugin_path.name}[/bold]", border_style="blue"))

    errors = 0
    warnings = 0

    def check(condition, success_msg, error_msg, is_warning=False):
        nonlocal errors, warnings
        if condition:
            console.print(Text(f"✅ {success_msg}", style="green"))
            return True
        else:
            if is_warning:
                console.print(Text(f"⚠️ {error_msg}", style="yellow"))
                warnings += 1
            else:
                console.print(Text(f"❌ {error_msg}", style="red"))
                errors += 1
            return False

    # 1. Check for meson.build
    meson_file = plugin_path / "meson.build"
    if check(meson_file.exists(), "Found meson.build file.", "Missing meson.build file."):
        meson_content = meson_file.read_text()
        # 2. Check for project() definition
        check("project(" in meson_content, "Contains project() definition.", "meson.build is missing a project() definition.", is_warning=True)
        # 3. Check for shared_library()
        check("shared_library(" in meson_content, "Contains shared_library() definition.", "meson.build does not appear to define a shared_library().")

    # 4. Check for source files
    has_cpp = any(plugin_path.rglob("*.cpp"))
    has_h = any(plugin_path.rglob("*.h")) or any(plugin_path.rglob("*.hpp"))
    check(has_cpp, "Found C++ source files (.cpp).", "No .cpp source files found in the directory.", is_warning=True)
    check(has_h, "Found C++ header files (.h/.hpp).", "No .h or .hpp header files found in the directory.", is_warning=True)

    # 5. Check for test definition (optional)
    check("test(" in meson_content, "Contains test() definitions.", "No test() definitions found in meson.build. Consider adding tests.", is_warning=True)

    # Final summary
    console.print("-" * 40)
    if errors == 0:
        console.print(Panel(
            f"[bold green]Validation Passed[/bold green]\nWarnings: {warnings}",
            title="Result",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[bold red]Validation Failed[/bold red]\nErrors: {errors}\nWarnings: {warnings}",
            title="Result",
            border_style="red"
        ))
        raise typer.Exit(code=1)
