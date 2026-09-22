"""yello init — scaffold a fresh consuming project.

Downloads the runtime dependencies (already implied by yello being installed),
creates the single-app domain layout, and writes the standard boilerplate so a
brand-new project can run `yello migrate` and `yello make:*` immediately.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import typer

from yello.console.command import Command, console

PROJECT_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "project"

_DEPENDENCIES = ["django", "djangorestframework"]

_GITIGNORE = """\
*.py[cod]
__pycache__/
db.sqlite3
staticfiles/
media/
.venv/
.env
Pipfile.lock
"""

_NEXT_STEPS = """\
[bold]Next steps[/bold]
  cd {cd}
  export DJANGO_SETTINGS_MODULE=config.settings
  yello migrate
  yello make:model Post --domain Posts
  yello make:migration && yello migrate
  yello make:admin --email you@example.com --password <a-strong-password>
  yello serve
"""


def _target_dir(name: str | None) -> Path:
    return Path.cwd() / name if name else Path.cwd()


def _validate_name(name: str | None) -> None:
    if name is None:
        return
    if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_-]*", name):
        console.print(f"[red]'{name}' is not a valid project name.[/red]")
        raise typer.Exit(1)


def _ensure_target_usable(target: Path, force: bool) -> None:
    if not target.exists():
        return
    contents = [p for p in target.iterdir() if p.name != ".git"]
    if contents and not force:
        console.print(f"[red]Target directory exists and is not empty:[/red] {target}")
        console.print("Pass [bold]--force[/bold] to overwrite.")
        raise typer.Exit(1)


def _copy_template(target: Path) -> None:
    shutil.copytree(PROJECT_TEMPLATE_DIR, target, dirs_exist_ok=True)


def _default_manager() -> str:
    return "pipenv" if shutil.which("pipenv") else "pip"


def _install_dependencies(target: Path, manager: str) -> None:
    if manager == "pipenv":
        console.print("[bold]Installing dependencies with pipenv...[/bold]")
        result = subprocess.run(["pipenv", "install"], cwd=str(target))
    elif manager == "pip":
        console.print(f"[bold]Installing dependencies with {sys.executable}...[/bold]")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", *(_DEPENDENCIES)],
        )
    else:
        console.print(f"[red]Unknown package manager '{manager}'. Use 'pip' or 'pipenv'.[/red]")
        raise typer.Exit(1)

    if result.returncode != 0:
        console.print(
            "[yellow]Dependency install failed — scaffolding is done, "
            "fix the install and run it again yourself.[/yellow]"
        )
    else:
        console.print("[green]Dependencies installed.[/green]")


class InitCommand(Command):
    """Scaffold a new Yello project and optionally install its dependencies."""

    def handle(
        self,
        name: str = typer.Argument(None, help="Project name (created as a subdirectory). Defaults to the current directory."),
        manager: str = typer.Option(None, "--manager", "-m", help="Package manager: pip or pipenv (default: auto)."),
        install: bool = typer.Option(True, "--install/--no-install", help="Install dependencies after scaffolding."),
        force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files."),
    ) -> None:
        _validate_name(name)
        target = _target_dir(name)

        console.print(f"[bold]Scaffolding Yello project[/bold] {target}")
        _ensure_target_usable(target, force)
        _copy_template(target)
        (target / ".gitignore").write_text(_GITIGNORE)
        # Pin the settings module so every yello command auto-detects it.
        (target / ".yello").write_text("DJANGO_SETTINGS_MODULE=config.settings\n")
        console.print("[green]Created[/green] config/, src/app/, manage.py, Pipfile, .yello")

        if install:
            _install_dependencies(target, manager or _default_manager())
        else:
            console.print("[yellow]Skipping dependency install (--no-install).[/yellow]")

        cd = target.name if name else "."
        console.print(_NEXT_STEPS.format(cd=cd))