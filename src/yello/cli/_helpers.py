"""Shared helpers for the yello CLI: Django bootstrap + common make:* utilities."""

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import typer
from rich.console import Console

console = Console()

_MANAGE_SETDEFAULT_RE = re.compile(
    r'setdefault\(["\']DJANGO_SETTINGS_MODULE["\']\s*,\s*["\']([^"\']+)["\']'
)
_MANAGE_ASSIGN_RE = re.compile(r'DJANGO_SETTINGS_MODULE\s*=\s*["\']([^"\']+)["\']')


def _detect_settings_module(project_root: Path) -> str | None:
    """Find the project's settings module without any env var.

    Precedence: a ``.yello`` config file, then ``manage.py`` (parsed for the
    ``DJANGO_SETTINGS_MODULE`` assignment), then common settings locations
    (``config/settings.py``, then any ``<dir>/settings.py`` at the root).
    """
    yello_cfg = project_root / ".yello"
    if yello_cfg.exists():
        for line in yello_cfg.read_text().splitlines():
            line = line.strip()
            if line.startswith("DJANGO_SETTINGS_MODULE"):
                _, _, value = line.partition("=")
                return value.strip().strip("\"'") or None

    manage_py = project_root / "manage.py"
    if manage_py.exists():
        content = manage_py.read_text()
        match = _MANAGE_SETDEFAULT_RE.search(content) or _MANAGE_ASSIGN_RE.search(content)
        if match:
            return match.group(1)

    config_settings = project_root / "config" / "settings.py"
    if config_settings.exists():
        return "config.settings"

    for subdir in sorted(project_root.iterdir()):
        if subdir.is_dir() and (subdir / "settings.py").exists():
            return f"{subdir.name}.settings"

    return None


def _load_dotenv(project_root: Path) -> None:
    """Load ``KEY=value`` lines from a ``.env`` file into the environment.

    Never overrides a variable that's already set. Mirrors the manual parsing
    already used for the ``.yello`` file above — no new dependency.
    """
    dotenv = project_root / ".env"
    if not dotenv.exists():
        return
    for line in dotenv.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("\"'")


def _bootstrap_django() -> None:
    """Bootstrap Django against the consuming project's settings module.

    Called lazily per-command, never at import time. Idempotent: returns
    immediately if Django is already configured. The settings module comes
    from ``DJANGO_SETTINGS_MODULE`` or is auto-detected from the project.
    """
    from django.apps import apps

    if apps.ready:
        return

    project_root = Path.cwd()
    _load_dotenv(project_root)
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE") or _detect_settings_module(project_root)
    if not settings_module:
        raise typer.BadParameter(
            "Could not find the Django settings module. Set "
            "DJANGO_SETTINGS_MODULE (e.g. config.settings), or run this "
            "from a project root that has a manage.py / settings.py."
        )

    # Mirror what manage.py does: the project root and the src/app layout must
    # be importable for INSTALLED_APPS ("app", "config", ...) to resolve.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
    cwd = str(project_root)
    for entry in (cwd, str(project_root / "src")):
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
