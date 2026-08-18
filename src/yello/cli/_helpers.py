"""Shared helpers for the yello CLI: Django bootstrap + common make:* utilities."""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def _bootstrap_django() -> None:
    """Bootstrap Django against the consuming project's settings module.

    Called lazily per-command, never at import time. Idempotent: returns
    immediately if Django is already configured.
    """
    from django.apps import apps

    if apps.ready:
        return

    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
    if not settings_module:
        raise typer.BadParameter(
            "DJANGO_SETTINGS_MODULE is not set. Point it at the consuming "
            "project's settings, e.g.\n\n"
            "    DJANGO_SETTINGS_MODULE=config.settings yello migrate status"
        )

    # Mirror what manage.py does: the project root and the src/app layout must
    # be importable for INSTALLED_APPS ("app", "config", ...) to resolve.
    cwd = str(Path.cwd())
    for entry in (cwd, str(Path.cwd() / "src")):
        if entry not in sys.path:
            sys.path.insert(0, entry)

    import django

    django.setup()


def _project_root() -> Path:
    """The consuming project root — where the `src/app` layout lives."""
    return Path.cwd()


def _src_app_dir(project_root: Path) -> Path:
    return project_root / "src" / "app"


def _fail(msg: str) -> None:
    console.print(f"[red]{msg}[/red]")
    raise typer.Exit(1)


def _ensure_not_exists(target: Path) -> None:
    if target.exists():
        _fail(f"Refusing to overwrite existing file: {target}")


def _render_template(src_template: Path, target: Path, **context) -> None:
    """Render a ``.py-tpl`` file into ``target``.

    Uses Django's own ``TemplateCommand`` machinery (the same code behind
    ``startapp``) for ``{{ variable }}`` substitution. The generic template is
    staged into a temp dir under the concrete target basename so the final file
    lands at exactly ``target``.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        shutil.copy(src_template, tmp_dir / f"{target.stem}.py-tpl")
        try:
            # Django >= 6.0
            from django.core.management.templates import TemplateCommand
        except ImportError:  # pragma: no cover - Django 5.x module path
            from django.core.management.commands.template import TemplateCommand
        TemplateCommand().handle(
            "app",
            context.get("model_name", target.stem),
            str(target.parent),
            template=str(tmp_dir),
            verbosity=0,
            extensions=["py"],
            files=[],
            exclude=[],
            **context,
        )
