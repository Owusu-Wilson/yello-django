# Artisan CLI Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the `yello` CLI so its command surface mirrors `php artisan` (matching namespaces where a Django equivalent exists) and its internals are genuinely OOP — every command is a `Command` subclass, not a bare function.

**Architecture:** A new `yello.console.Command` base class (mirroring `Illuminate\Console\Command`) provides `bootstrap()`/`info()`/`warn()`/`error()`/`line()`/`confirm()`/`fail()`. Every CLI command becomes `class XCommand(Command)` with a `handle()` method carrying the same `typer.Argument`/`typer.Option` defaults used today; registration in `cli/__init__.py` calls `app.command(name=...)(cls().handle)` — Typer introspects the bound method's signature same as it does a function. New domain concepts (`Seeder`, `Factory`, `Rule`, `Mailable`, `Middleware`, exceptions) get their own base class + `.py-tpl` template + `make:*` generator, following the exact pattern `Policy`/`Controller` already use in this codebase.

**Tech Stack:** Python 3.10+, Typer, Rich, Django 5, Django REST Framework, pytest + pytest-django.

**Spec:** `docs/superpowers/specs/2026-09-22-artisan-cli-parity-design.md`

## Global Constraints

- Every CLI command is a `Command` subclass with a `handle()` method — no bare `def` functions registered directly with Typer (per user requirement: "make sure you're using OOP style").
- No new third-party dependencies (no `python-dotenv`, no IPython) — `.env` parsing and `tinker`'s REPL are hand-rolled, matching the existing manual `.yello`-file-parsing style in `_helpers.py`.
- Every renamed/new command needs CLI smoke-test coverage in `tests/test_cli.py` (help text + at least one behavioral test) before the task is done.
- Follow existing conventions exactly: generators write via `_render_template`/`_tpl_path` into `src/app/...`, refuse to overwrite existing files (`_ensure_not_exists`), print `[green]Created[/green] <relative path>` on success.
- Excluded entirely (do not implement): `queue:*`, `schedule:*`, `event:*`, `notifications:*`, `session:table`, `channel:*`, and anything from optional Laravel packages (Horizon, Telescope, Nova, Livewire, etc.) — no Django equivalent exists.

---

## Task 1: `Command` base class

**Files:**
- Create: `src/yello/console/__init__.py`
- Create: `src/yello/console/command.py`
- Test: `tests/test_console_command.py`

**Interfaces:**
- Produces: `yello.console.command.Command` with methods `bootstrap()`, `info(message: str)`, `warn(message: str)`, `error(message: str)`, `line(message: str)`, `confirm(question: str, default: bool = False) -> bool`, `fail(message: str) -> NoReturn`, and `handle(self, *args, **kwargs)` (raises `NotImplementedError`). Every later task subclasses this.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_console_command.py
import typer
import pytest

from yello.console.command import Command


class TestCommandOutput:
    def test_handle_not_implemented(self):
        with pytest.raises(NotImplementedError):
            Command().handle()

    def test_info_prints_green(self, capsys):
        Command().info("ok")
        assert "ok" in capsys.readouterr().out

    def test_error_prints_and_is_readable(self, capsys):
        Command().error("bad")
        assert "bad" in capsys.readouterr().out

    def test_fail_prints_error_and_exits_1(self, capsys):
        with pytest.raises(typer.Exit) as exc_info:
            Command().fail("nope")
        assert exc_info.value.exit_code == 1
        assert "nope" in capsys.readouterr().out

    def test_confirm_delegates_to_typer(self, monkeypatch):
        monkeypatch.setattr(typer, "confirm", lambda q, default=False: True)
        assert Command().confirm("continue?") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_console_command.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'yello.console'`

- [ ] **Step 3: Write the implementation**

```python
# src/yello/console/__init__.py
```

```python
# src/yello/console/command.py
"""Base class for all yello console commands, mirroring Artisan's Command."""

from typing import NoReturn

import typer
from rich.console import Console

console = Console()


class Command:
    """Subclass this and implement ``handle()`` for every CLI command."""

    def bootstrap(self) -> None:
        from yello.cli._helpers import _bootstrap_django

        _bootstrap_django()

    def info(self, message: str) -> None:
        console.print(f"[green]{message}[/green]")

    def warn(self, message: str) -> None:
        console.print(f"[yellow]{message}[/yellow]")

    def error(self, message: str) -> None:
        console.print(f"[red]{message}[/red]")

    def line(self, message: str) -> None:
        console.print(message)

    def confirm(self, question: str, default: bool = False) -> bool:
        return typer.confirm(question, default=default)

    def fail(self, message: str) -> NoReturn:
        self.error(message)
        raise typer.Exit(1)

    def handle(self, *args, **kwargs) -> None:
        raise NotImplementedError
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_console_command.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/yello/console tests/test_console_command.py
git commit -m "Add OOP Command base class for the yello CLI"
```

---

## Task 2: `.env` loading in `_bootstrap_django`

**Files:**
- Modify: `src/yello/cli/_helpers.py`
- Test: `tests/test_detect.py` (add a class; file already exists untracked, keep its existing tests unchanged)

**Interfaces:**
- Produces: `_load_dotenv(project_root: Path) -> None` in `_helpers.py`, called from `_bootstrap_django()` before `_detect_settings_module`. Sets `os.environ[key] = value` for each `KEY=value` line in `.env`, only if `key` is not already in `os.environ`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_detect.py (append)
import os

from yello.cli._helpers import _load_dotenv


class TestLoadDotenv:
    def test_sets_env_vars_from_file(self, tmp_path, monkeypatch):
        (tmp_path / ".env").write_text("DJANGO_SECRET_KEY=abc123\nFOO=bar\n")
        monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
        monkeypatch.delenv("FOO", raising=False)
        _load_dotenv(tmp_path)
        assert os.environ["DJANGO_SECRET_KEY"] == "abc123"
        assert os.environ["FOO"] == "bar"

    def test_does_not_override_existing_env(self, tmp_path, monkeypatch):
        (tmp_path / ".env").write_text("FOO=fromfile\n")
        monkeypatch.setenv("FOO", "fromenv")
        _load_dotenv(tmp_path)
        assert os.environ["FOO"] == "fromenv"

    def test_missing_file_is_a_noop(self, tmp_path):
        _load_dotenv(tmp_path)  # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_detect.py::TestLoadDotenv -v`
Expected: FAIL with `ImportError: cannot import name '_load_dotenv'`

- [ ] **Step 3: Write the implementation**

Add to `src/yello/cli/_helpers.py`, right after the existing `_detect_settings_module` function:

```python
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
```

Then update `_bootstrap_django` to call it — change:

```python
    project_root = Path.cwd()
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE") or _detect_settings_module(project_root)
```

to:

```python
    project_root = Path.cwd()
    _load_dotenv(project_root)
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE") or _detect_settings_module(project_root)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_detect.py -v`
Expected: PASS (all tests in the file, including the pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/_helpers.py tests/test_detect.py
git commit -m "Load .env into the environment before Django bootstrap"
```

---

## Task 3: Convert `route:list` and `dev`/`serve` to OOP commands

**Files:**
- Modify: `src/yello/cli/route.py`
- Delete: `src/yello/cli/dev.py`
- Create: `src/yello/cli/serve.py`
- Modify: `src/yello/cli/__init__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `RouteListCommand(Command)` in `route.py` with `handle()`; `ServeCommand(Command)` in `serve.py` with `handle(port: str = "8000")`, registered under **both** `serve` and `dev`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py — add to TestCliSmoke
    def test_serve_alias_and_dev_both_listed(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "serve" in result.output
        assert "dev" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestCliSmoke::test_serve_alias_and_dev_both_listed -v`
Expected: PASS already for "dev" but this locks in "serve" — run it now to confirm it currently FAILs on the "serve" assertion.

- [ ] **Step 3: Write the implementation**

```python
# src/yello/cli/route.py
"""yello route:list — list registered URLs."""

from yello.console.command import Command, console


def _collect(patterns, prefix: str = ""):
    rows = []
    for p in patterns:
        path = prefix
        if hasattr(p, "pattern"):
            path += str(p.pattern)
        if hasattr(p, "url_patterns"):
            rows.extend(_collect(p.url_patterns, path))
        else:
            view = getattr(p, "callback", None)
            if view is None:
                view_repr = "?"
            else:
                view_repr = f"{getattr(view, '__module__', '')}.{getattr(view, '__name__', '')}"
            rows.append((path, getattr(p, "name", None) or "", view_repr))
    return rows


class RouteListCommand(Command):
    """List every registered URL pattern."""

    def handle(self) -> None:
        self.bootstrap()
        from django.urls import get_resolver
        from rich.table import Table

        resolver = get_resolver()
        rows = _collect(resolver.url_patterns)

        table = Table(title="Registered URLs")
        table.add_column("Path", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("View")
        for path, name, view in rows:
            table.add_row(path, name, view)
        console.print(table)
```

```python
# src/yello/cli/serve.py
"""yello serve (alias: dev) — run the Django development server."""

import typer

from yello.console.command import Command


class ServeCommand(Command):
    """Run the Django development server."""

    def handle(
        self,
        port: str = typer.Option("8000", "--port", "-p", help="Port to bind."),
    ) -> None:
        self.bootstrap()
        from django.core.management import call_command

        call_command("runserver", port, use_reloader=True)
```

Delete `src/yello/cli/dev.py`.

Update `src/yello/cli/__init__.py`:

```python
"""yello CLI — assembly point.

One Typer app exposing all Artisan-style verbs. Nothing here touches Django at
import time; Django is bootstrapped lazily per-command via `_bootstrap_django`.
"""

import typer

from yello.cli import init, make, migrate, route, serve

app = typer.Typer(
    name="yello",
    help="Artisan-style CLI for Laravel-style Django projects.",
    no_args_is_help=True,
    add_completion=False,
)

for name, command_cls in make.MAKE_COMMANDS:
    app.command(name=name)(command_cls().handle)

app.command(name="route:list")(route.RouteListCommand().handle)
app.command(name="serve")(serve.ServeCommand().handle)
app.command(name="dev")(serve.ServeCommand().handle)
app.command(name="init")(init.InitCommand().handle)

for name, command_cls in migrate.MIGRATE_COMMANDS:
    app.command(name=name)(command_cls().handle)


if __name__ == "__main__":
    app()
```

Note: `make.MAKE_COMMANDS` and `migrate.MIGRATE_COMMANDS` don't have their new shapes yet — Task 4 and Task 6 update them. For this task, temporarily keep `make.py`'s `MAKE_COMMANDS` and `migrate.py` as they are today (function-based); only wire in `route.py`/`serve.py` as shown, and leave the `migrate.add_typer(...)` line from the original file in place until Task 6. Concretely, for *this* task only, the `__init__.py` diff is:

```python
from yello.cli import dev, init, make, migrate, route, serve
```
→
```python
from yello.cli import init, make, migrate, route, serve
```

and:

```python
app.command(name="route:list")(route.route_list)
app.command(name="dev")(dev.dev)
app.command(name="init")(init.init)
```
→
```python
app.command(name="route:list")(route.RouteListCommand().handle)
app.command(name="serve")(serve.ServeCommand().handle)
app.command(name="dev")(serve.ServeCommand().handle)
app.command(name="init")(init.init)
```

(`init.InitCommand` lands in Task 5 — keep `init.init` for now.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS, including `test_route_list`, `test_route_list_in_project`, and the new `test_serve_alias_and_dev_both_listed`.

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/route.py src/yello/cli/serve.py src/yello/cli/__init__.py tests/test_cli.py
git rm src/yello/cli/dev.py
git commit -m "Convert route:list and dev/serve to OOP Command classes"
```

---

## Task 4: Convert `init` to `InitCommand`

**Files:**
- Modify: `src/yello/cli/init.py`
- Modify: `src/yello/cli/__init__.py`
- Test: `tests/test_init.py` (unchanged — behavior is identical, just confirm it still passes)

**Interfaces:**
- Produces: `InitCommand(Command)` in `init.py` with `handle(name, manager, install, force)` — same signature/behavior as the current `init()` function.

- [ ] **Step 1: Write the failing test**

No new behavior — reuse the existing `tests/test_init.py` suite as the regression gate for this refactor.

Run: `python -m pytest tests/test_init.py -v`
Expected (pre-refactor baseline): PASS — confirms current behavior before you touch it.

- [ ] **Step 2: Run test to verify it fails after the rename (sanity check)**

After renaming the module-level `init` function to a method on a class but *before* updating `cli/__init__.py`'s registration, run:

Run: `python -m pytest tests/test_init.py -v`
Expected: FAIL (import error / missing `init.init`), proving the test suite actually exercises the wiring.

- [ ] **Step 3: Write the implementation**

In `src/yello/cli/init.py`, change the imports and wrap the existing function body into a class. Replace:

```python
from yello.cli._helpers import console
```

with:

```python
from yello.console.command import Command, console
```

Replace the final `def init(...) -> None:` function (keep every line of its body identical) with:

```python
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
        (target / ".yello").write_text("DJANGO_SETTINGS_MODULE=config.settings\n")
        console.print("[green]Created[/green] config/, src/app/, manage.py, Pipfile, .yello")

        if install:
            _install_dependencies(target, manager or _default_manager())
        else:
            console.print("[yellow]Skipping dependency install (--no-install).[/yellow]")

        cd = target.name if name else "."
        console.print(_NEXT_STEPS.format(cd=cd))
```

Update `_NEXT_STEPS` text (also touched again in Task 6) to reflect the flattened migrate commands:

```python
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
```

In `src/yello/cli/__init__.py`, change:

```python
app.command(name="init")(init.init)
```

to:

```python
app.command(name="init")(init.InitCommand().handle)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_init.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/init.py src/yello/cli/__init__.py
git commit -m "Convert init to an OOP Command class"
```

---

## Task 5: Convert existing `make:*` commands to OOP

**Files:**
- Modify: `src/yello/cli/make.py`
- Modify: `src/yello/cli/__init__.py`
- Test: `tests/test_cli.py` (existing `TestProjectFlow` cases are the regression gate)

**Interfaces:**
- Produces: `MakeModelCommand`, `MakeControllerCommand`, `MakeRequestCommand`, `MakeResourceCommand`, `MakePolicyCommand`, `MakeAdminCommand` — each `Command` subclass with a `handle()` carrying the exact same parameters as today's functions. `MAKE_COMMANDS` becomes `[("make:model", MakeModelCommand), ("make:controller", MakeControllerCommand), ...]` (name, class) tuples — this is the shape every later `make:*` task (6 through 12, 15-21) appends to.

- [ ] **Step 1: Confirm the regression gate passes first**

Run: `python -m pytest tests/test_cli.py::TestProjectFlow -v`
Expected: PASS (baseline before refactor)

- [ ] **Step 2: Rewrite `make.py` as classes**

Replace the entire body of `src/yello/cli/make.py` (keep `_tpl_path`, `_pluralize`, `_make_admin_file`, `_make_superuser` as module-level helpers unchanged) with class-wrapped commands:

```python
"""yello make:* — scaffold files into the Laravel-style domain layout."""

import os
from pathlib import Path

import typer

from yello.cli._helpers import (
    _ensure_not_exists,
    _project_root,
    _render_template,
    _src_app_dir,
)
from yello.codegen.aggregator import add_model_import
from yello.console.command import Command, console


def _tpl_path(kind: str) -> Path:
    return Path(__file__).resolve().parent.parent / "templates" / kind / f"{kind}_name.py-tpl"


def _pluralize(name: str) -> str:
    lower = name.lower()
    if lower.endswith("s"):
        return lower + "es"
    return lower + "s"


class MakeModelCommand(Command):
    """Create a Domain/<Domain>/Models/<Name>.py model and update app/models.py."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Model name, e.g. Post."),
        domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Domain" / domain / "Models" / f"{name}.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("model"), target, model_name=name, domain=domain)
        changed = add_model_import(_project_root(), domain, name)

        self.info(f"Created {target.relative_to(_project_root())}")
        if changed:
            self.info("Updated src/app/models.py (model import appended)")


class MakeControllerCommand(Command):
    """Create an Http/Controllers/<Name>Controller.py."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Model name, e.g. Post."),
        domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Http" / "Controllers" / f"{name}Controller.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("controller"), target, model_name=name, domain=domain)

        self.info(f"Created {target.relative_to(_project_root())}")
        self.line("Add to your routes, e.g. in routes/api.py:")
        self.line(f"  [cyan]path(\"{_pluralize(name)}/\", {name}Controller.as_view()),[/cyan]")


class MakeRequestCommand(Command):
    """Create an Http/Requests/<Name>.py validation class."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Request class name, e.g. StorePostRequest."),
        domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Http" / "Requests" / f"{name}.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("request"), target, request_name=name, domain=domain)

        self.info(f"Created {target.relative_to(_project_root())}")


class MakeResourceCommand(Command):
    """Create an Http/Resources/<Name>Resource.py output serializer."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Model name, e.g. Post."),
        domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Http" / "Resources" / f"{name}Resource.py"

        _ensure_not_exists(target)
        _render_template(
            _tpl_path("resource"),
            target,
            model_name=name,
            resource_name=f"{name}Resource",
            domain=domain,
        )

        self.info(f"Created {target.relative_to(_project_root())}")


class MakePolicyCommand(Command):
    """Create a Domain/<Domain>/Policies/<Name>Policy.py."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Model name, e.g. Post."),
        domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Domain" / domain / "Policies" / f"{name}Policy.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("policy"), target, policy_name=f"{name}Policy", domain=domain)

        self.info(f"Created {target.relative_to(_project_root())}")


class MakeAdminCommand(Command):
    """Generate an Admin class for a model, or create a superuser.

    Given a NAME, writes an Admin/<Name>Admin.py registration file. Without a
    NAME, falls back to superuser creation (interactive, or flag-based with
    ``--email``/``--password``).
    """

    def handle(
        self,
        name: str = typer.Argument(None, help="Model name to generate an Admin class for."),
        domain: str = typer.Option("", "--domain", "-d", help="PascalCase domain folder under Domain/."),
        email: str = typer.Option(None, "--email", "-e", help="Admin/superuser email."),
        password: str = typer.Option(None, "--password", "-p", help="Admin/superuser password."),
    ) -> None:
        if name:
            self._make_admin_file(name, domain)
            return
        self._make_superuser(email, password)

    def _make_admin_file(self, name: str, domain: str) -> None:
        if not domain:
            self.fail("--domain is required when generating an Admin class.")
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Admin" / f"{name}Admin.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("admin"), target, model_name=name, domain=domain)

        self.info(f"Created {target.relative_to(_project_root())}")

    def _make_superuser(self, email: str | None, password: str | None) -> None:
        self.bootstrap()
        from django.core.management import call_command

        if email and not password:
            self.fail("--password is required when --email is given.")

        if email and password:
            os.environ.setdefault("DJANGO_SUPERUSER_PASSWORD", password)
            call_command("createsuperuser", email=email, interactive=False)
            self.info(f"Superuser created {email}")
            return

        call_command("createsuperuser", interactive=True)


MAKE_COMMANDS = [
    ("make:model", MakeModelCommand),
    ("make:controller", MakeControllerCommand),
    ("make:request", MakeRequestCommand),
    ("make:resource", MakeResourceCommand),
    ("make:policy", MakePolicyCommand),
    ("make:admin", MakeAdminCommand),
]
```

Note `console` import stays available (re-exported from `yello.console.command`) for any code that still needs raw `console.print`, though the classes above now use `self.info`/`self.line`/`self.fail` instead.

`src/yello/cli/__init__.py` already does `app.command(name=name)(command_cls().handle)` for `MAKE_COMMANDS` from Task 3 — no further change needed here since that loop already expects `(name, cls)` tuples.

- [ ] **Step 3: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS (all of `TestProjectFlow`, unchanged assertions — output text switched from `[green]Created[/green] X` printed via `console.print` to `self.info(f"Created {X}")` which renders identically since `info()` wraps in `[green]...[/green]`)

- [ ] **Step 4: Commit**

```bash
git add src/yello/cli/make.py
git commit -m "Convert existing make:* commands to OOP Command classes"
```

---

## Task 6: Flatten `migrate` into colon-commands (Phase 0)

**Files:**
- Modify: `src/yello/cli/migrate.py` (full rewrite)
- Modify: `src/yello/cli/make.py` (add `MakeMigrationCommand`)
- Modify: `src/yello/cli/__init__.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Produces: `migrate.MIGRATE_COMMANDS = [("migrate", MigrateCommand), ("migrate:fresh", MigrateFreshCommand), ("migrate:rollback", MigrateRollbackCommand), ("migrate:status", MigrateStatusCommand)]`. `MakeMigrationCommand` added to `make.MAKE_COMMANDS` as `("make:migration", MakeMigrationCommand)`. Both `MigrateCommand.handle` and `MigrateFreshCommand.handle` gain a `seed: bool` parameter but do NOT act on it yet — Task 10 wires the actual seeding call. For now, `--seed` is accepted and, if true, prints `self.warn("Seeding is not wired up yet.")` (replaced by real behavior in Task 10 so this task's tests stay accurate at each step).

- [ ] **Step 1: Write the failing tests**

Replace, in `tests/test_cli.py`, every use of the old `["migrate", "run"]` / `["migrate", "make"]` / `["migrate", "fresh", ...]` / `["migrate", "rollback", ...]` / `["migrate", "status"]` argv shapes with the new flat names. Also update `TestCliSmoke.test_help_lists_all_commands`, `test_migrate_status`, `test_settings_module_autodetected_without_env_var`, `test_migrate_no_args_is_help` (delete this test — there's no longer a `migrate` sub-app with its own help screen), and every `run_cli(...)` call in `TestProjectFlow`:

```python
# tests/test_cli.py — replacements (apply throughout the file)
# "migrate", "run"        -> "migrate"
# "migrate", "make"       -> "make:migration"
# "migrate", "fresh", ... -> "migrate:fresh", ...
# "migrate", "rollback", ...-> "migrate:rollback", ...
# "migrate", "status"     -> "migrate:status"
```

Concretely:

```python
class TestCliSmoke:
    def test_help_lists_all_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for name in (
            "make:model",
            "make:controller",
            "make:request",
            "make:resource",
            "make:policy",
            "make:admin",
            "make:migration",
            "route:list",
            "serve",
            "dev",
            "init",
            "migrate",
            "migrate:fresh",
            "migrate:rollback",
            "migrate:status",
        ):
            assert name in result.output

    @pytest.mark.django_db
    def test_migrate_status(self):
        result = runner.invoke(app, ["migrate:status"])
        assert result.exit_code == 0, result.output
        assert "0001_initial" in result.output

    def test_settings_module_autodetected_without_env_var(self, project_dir):
        env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
        r = subprocess.run(
            [sys.executable, "-m", "yello", "migrate:status"],
            cwd=str(project_dir),
            env=env,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "0001_initial" in r.stdout

    def test_route_list(self):
        result = runner.invoke(app, ["route:list"])
        assert result.exit_code == 0, result.output
        assert "admin/" in result.output
```

(Remove `test_migrate_no_args_is_help` entirely — `migrate` is now a leaf command with no sub-help screen.)

```python
class TestProjectFlow:
    def test_make_model_then_migrations(self, project_dir, run_cli):
        r = run_cli("make:model", "Post", "--domain", "Posts")
        assert r.returncode == 0, r.stderr

        model_file = project_dir / "src/app/Domain/Posts/Models/Post.py"
        assert model_file.exists()
        assert "class Post(BaseModel):" in model_file.read_text()

        models_file = project_dir / "src/app/models.py"
        assert "from app.Domain.Posts.Models.Post import Post" in models_file.read_text()

        r = run_cli("make:migration")
        assert r.returncode == 0, r.stderr
        assert (project_dir / "src/app/migrations/0001_initial.py").exists()

        r = run_cli("migrate")
        assert r.returncode == 0, r.stderr
        assert (project_dir / "db.sqlite3").exists()

        r = run_cli("migrate:status")
        assert r.returncode == 0, r.stderr
        assert "0001_initial" in r.stdout

    # ... (test_make_model_twice_refuses_to_overwrite, test_other_generators_write_expected_paths unchanged)

    def test_make_admin_superuser(self, project_dir, run_cli):
        r = run_cli("migrate")
        assert r.returncode == 0, r.stderr

        r = run_cli("make:admin", "--email", "admin@example.com", "--password", "verysecret123")
        assert r.returncode == 0, r.stderr
        assert "Superuser created" in r.stdout

    def test_route_list_in_project(self, project_dir, run_cli):
        r = run_cli("route:list")
        assert r.returncode == 0, r.stderr
        assert "admin/" in r.stdout

    def test_migrate_rollback(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("make:migration").returncode == 0
        assert run_cli("migrate").returncode == 0

        r = run_cli("migrate:rollback", "app")
        assert r.returncode == 0, r.stderr
        assert "app.0001_initial" in r.stdout

        r = run_cli("migrate:status")
        assert "app.0001_initial" not in r.stdout

    def test_migrate_fresh(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("make:migration").returncode == 0
        assert run_cli("migrate").returncode == 0

        r = run_cli("migrate:fresh", "--yes")
        assert r.returncode == 0, r.stderr

    def test_init_end_to_end(self, tmp_path):
        r = _run_in("init", "blog", "--no-install", cwd=tmp_path)
        assert r.returncode == 0, r.stderr

        project = tmp_path / "blog"
        env = {"DJANGO_SETTINGS_MODULE": "config.settings"}

        clean_env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
        r = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=str(project),
            env=clean_env,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr

        r = _run_in("migrate", cwd=project, env_extra=env)
        assert r.returncode == 0, r.stderr
        assert (project / "db.sqlite3").exists()

        r = _run_in("make:model", "Post", "--domain", "Posts", cwd=project, env_extra=env)
        assert r.returncode == 0, r.stderr
        assert (project / "src/app/Domain/Posts/Models/Post.py").exists()
        assert "from app.Domain.Posts.Models.Post import Post" in (
            project / "src/app/models.py"
        ).read_text()

        assert _run_in("make:migration", cwd=project, env_extra=env).returncode == 0
        r = _run_in("migrate", cwd=project, env_extra=env)
        assert r.returncode == 0, r.stderr

        r = _run_in("make:controller", "Post", "--domain", "Posts", cwd=project, env_extra=env)
        assert r.returncode == 0, r.stderr
        assert (project / "src/app/Http/Controllers/PostController.py").exists()

        r = _run_in("route:list", cwd=project, env_extra=env)
        assert r.returncode == 0, r.stderr
        assert "admin/" in r.stdout

        r = _run_in(
            "make:admin", "--email", "admin@example.com", "--password", "verysecret123",
            cwd=project, env_extra=env,
        )
        assert r.returncode == 0, r.stderr
        assert "Superuser created" in r.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL — `migrate`, `migrate:fresh`, `migrate:rollback`, `migrate:status`, `make:migration` don't exist yet.

- [ ] **Step 3: Write the implementation**

```python
# src/yello/cli/migrate.py
"""yello migrate / migrate:* — database migration commands."""

import typer

from yello.console.command import Command


class MigrateCommand(Command):
    """Run pending migrations via ``migrate``."""

    def handle(
        self,
        seed: bool = typer.Option(False, "--seed", help="Seed the database after migrating."),
    ) -> None:
        self.bootstrap()
        from django.core.management import call_command

        call_command("migrate", interactive=False)
        if seed:
            self.warn("Seeding is not wired up yet.")


class MigrateFreshCommand(Command):
    """Flush the database and re-run every migration."""

    def handle(
        self,
        seed: bool = typer.Option(False, "--seed", help="Seed the database after migrating."),
        yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
    ) -> None:
        self.bootstrap()
        from django.core.management import call_command

        if not yes and not self.confirm(
            "This will flush all data and re-run every migration. Continue?"
        ):
            raise typer.Abort()

        call_command("flush", interactive=False)
        call_command("migrate", interactive=False)
        if seed:
            self.warn("Seeding is not wired up yet.")


class MigrateRollbackCommand(Command):
    """Roll a migration back via ``migrate <app> <migration>``."""

    def handle(
        self,
        app: str = typer.Argument(..., help="App label to roll back."),
        migration: str = typer.Argument("zero", help="Migration name to roll back to (default: zero)."),
    ) -> None:
        self.bootstrap()
        from django.core.management import call_command

        call_command("migrate", app, migration, interactive=False)


class MigrateStatusCommand(Command):
    """Show migration status via ``showmigrations``."""

    def handle(self) -> None:
        self.bootstrap()
        from django.core.management import call_command

        call_command("showmigrations", verbosity=2)


MIGRATE_COMMANDS = [
    ("migrate", MigrateCommand),
    ("migrate:fresh", MigrateFreshCommand),
    ("migrate:rollback", MigrateRollbackCommand),
    ("migrate:status", MigrateStatusCommand),
]
```

Add to `src/yello/cli/make.py`, alongside the other `Make*Command` classes:

```python
class MakeMigrationCommand(Command):
    """Create new migration(s) via ``makemigrations``."""

    def handle(
        self,
        app: str = typer.Option(None, "--app", "-a", help="Limit to an app label."),
        empty: bool = typer.Option(False, "--empty", help="Create an empty migration."),
    ) -> None:
        self.bootstrap()
        from django.core.management import call_command

        args = (app,) if app else ()
        call_command("makemigrations", *args, empty=empty, interactive=False)
```

Append it to `MAKE_COMMANDS`:

```python
MAKE_COMMANDS = [
    ("make:model", MakeModelCommand),
    ("make:controller", MakeControllerCommand),
    ("make:request", MakeRequestCommand),
    ("make:resource", MakeResourceCommand),
    ("make:policy", MakePolicyCommand),
    ("make:admin", MakeAdminCommand),
    ("make:migration", MakeMigrationCommand),
]
```

Update `src/yello/cli/__init__.py` — remove `app.add_typer(migrate.migrate_app)` and replace with the flat loop (this also drops the now-unneeded `migrate_app` Typer sub-app entirely):

```python
"""yello CLI — assembly point.

One Typer app exposing all Artisan-style verbs. Nothing here touches Django at
import time; Django is bootstrapped lazily per-command via `_bootstrap_django`.
"""

import typer

from yello.cli import init, make, migrate, route, serve

app = typer.Typer(
    name="yello",
    help="Artisan-style CLI for Laravel-style Django projects.",
    no_args_is_help=True,
    add_completion=False,
)

for name, command_cls in make.MAKE_COMMANDS:
    app.command(name=name)(command_cls().handle)

for name, command_cls in migrate.MIGRATE_COMMANDS:
    app.command(name=name)(command_cls().handle)

app.command(name="route:list")(route.RouteListCommand().handle)
app.command(name="serve")(serve.ServeCommand().handle)
app.command(name="dev")(serve.ServeCommand().handle)
app.command(name="init")(init.InitCommand().handle)


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/ -v`
Expected: PASS, full suite.

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/migrate.py src/yello/cli/make.py src/yello/cli/__init__.py tests/test_cli.py
git commit -m "Flatten migrate sub-app into migrate:* colon-commands"
```

---

## Task 7: `Seeder` base class + `make:seeder`

**Files:**
- Create: `src/yello/db/seeder.py`
- Create: `src/yello/templates/seeder/seeder_name.py-tpl`
- Modify: `src/yello/cli/make.py`
- Test: `tests/test_seeder.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `yello.db.seeder.Seeder` with `run()` (raises `NotImplementedError`) and `call(*seeder_classes: type[Seeder])`. `MakeSeederCommand` added to `MAKE_COMMANDS` as `("make:seeder", MakeSeederCommand)`, writing to `src/app/Database/Seeders/<Name>.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_seeder.py
import pytest

from yello.db.seeder import Seeder


class TestSeeder:
    def test_run_not_implemented(self):
        with pytest.raises(NotImplementedError):
            Seeder().run()

    def test_call_runs_each_seeder_in_order(self):
        order = []

        class First(Seeder):
            def run(self):
                order.append("first")

        class Second(Seeder):
            def run(self):
                order.append("second")

        Seeder().call(First, Second)
        assert order == ["first", "second"]
```

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_make_seeder(self, project_dir, run_cli):
        r = run_cli("make:seeder", "PostSeeder")
        assert r.returncode == 0, r.stderr
        target = project_dir / "src/app/Database/Seeders/PostSeeder.py"
        assert target.exists()
        assert "class PostSeeder(Seeder):" in target.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_seeder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yello.db.seeder'`

- [ ] **Step 3: Write the implementation**

```python
# src/yello/db/seeder.py
"""Base for Database/Seeders classes."""


class Seeder:
    def run(self) -> None:
        raise NotImplementedError

    def call(self, *seeder_classes: type["Seeder"]) -> None:
        for seeder_cls in seeder_classes:
            seeder_cls().run()
```

```
# src/yello/templates/seeder/seeder_name.py-tpl
from yello.db.seeder import Seeder


class {{ seeder_name }}(Seeder):
    def run(self) -> None:
        raise NotImplementedError
```

Add to `src/yello/cli/make.py`:

```python
class MakeSeederCommand(Command):
    """Create a Database/Seeders/<Name>.py seeder."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Seeder class name, e.g. PostSeeder."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Database" / "Seeders" / f"{name}.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("seeder"), target, seeder_name=name)

        self.info(f"Created {target.relative_to(_project_root())}")
```

Append to `MAKE_COMMANDS`: `("make:seeder", MakeSeederCommand),`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_seeder.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/db/seeder.py src/yello/templates/seeder src/yello/cli/make.py tests/test_seeder.py tests/test_cli.py
git commit -m "Add Seeder base class and make:seeder command"
```

---

## Task 8: `db.py` — `run_seed()` + `db:seed`

**Files:**
- Create: `src/yello/cli/db.py`
- Modify: `src/yello/cli/__init__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `run_seed(seeder_class: str = "DatabaseSeeder") -> None` (module-level function in `db.py`) and `DbSeedCommand(Command)` with `handle(cls: str = "DatabaseSeeder")`. `db.DB_COMMANDS = [("db:seed", DbSeedCommand)]` — later tasks (9-11) append to this list.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_db_seed(self, project_dir, run_cli):
        seeders_dir = project_dir / "src/app/Database/Seeders"
        seeders_dir.mkdir(parents=True)
        (seeders_dir / "__init__.py").write_text("")
        (seeders_dir / "DatabaseSeeder.py").write_text(
            "from yello.db.seeder import Seeder\n\n\n"
            "class DatabaseSeeder(Seeder):\n"
            "    def run(self) -> None:\n"
            "        print('seeded!')\n"
        )
        r = run_cli("db:seed")
        assert r.returncode == 0, r.stderr
        assert "seeded!" in r.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestProjectFlow::test_db_seed -v`
Expected: FAIL — `db:seed` doesn't exist.

- [ ] **Step 3: Write the implementation**

```python
# src/yello/cli/db.py
"""yello db:* — database inspection and seeding commands."""

import typer

from yello.cli._helpers import _bootstrap_django
from yello.console.command import Command


def run_seed(seeder_class: str = "DatabaseSeeder") -> None:
    """Import ``app.Database.Seeders.<seeder_class>`` and run it.

    Kept as a free function (not a Command method) so ``migrate``/
    ``migrate:fresh`` can call it without knowing anything about how
    seeding works — they only import this.
    """
    _bootstrap_django()
    import importlib

    module = importlib.import_module(f"app.Database.Seeders.{seeder_class}")
    seeder = getattr(module, seeder_class)()
    seeder.run()


class DbSeedCommand(Command):
    """Seed the database via a project Seeder class."""

    def handle(
        self,
        cls: str = typer.Option("DatabaseSeeder", "--class", "-c", help="Seeder class to run."),
    ) -> None:
        run_seed(cls)
        self.info(f"Seeded using {cls}.")


DB_COMMANDS = [
    ("db:seed", DbSeedCommand),
]
```

Update `src/yello/cli/__init__.py`:

```python
from yello.cli import db, init, make, migrate, route, serve
```

and add, alongside the `make`/`migrate` loops:

```python
for name, command_cls in db.DB_COMMANDS:
    app.command(name=name)(command_cls().handle)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/db.py src/yello/cli/__init__.py tests/test_cli.py
git commit -m "Add db:seed command and run_seed() helper"
```

---

## Task 9: `db:wipe`

**Files:**
- Modify: `src/yello/cli/db.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `DbWipeCommand(Command)` with `handle(yes: bool)`, appended to `DB_COMMANDS` as `("db:wipe", DbWipeCommand)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_db_wipe(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("make:migration").returncode == 0
        assert run_cli("migrate").returncode == 0

        r = run_cli("db:wipe", "--yes")
        assert r.returncode == 0, r.stderr

        r = run_cli("migrate:status")
        assert "app.0001_initial" not in r.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestProjectFlow::test_db_wipe -v`
Expected: FAIL — `db:wipe` doesn't exist.

- [ ] **Step 3: Write the implementation**

Add to `src/yello/cli/db.py`:

```python
class DbWipeCommand(Command):
    """Drop every table in the database, including migration history."""

    def handle(
        self,
        yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
    ) -> None:
        _bootstrap_django()
        if not yes and not self.confirm(
            "This will drop every table in the database. Continue?"
        ):
            raise typer.Abort()

        from django.db import connection

        with connection.cursor() as cursor:
            table_names = connection.introspection.table_names(cursor)

        with connection.schema_editor() as schema_editor:
            with connection.constraint_checks_disabled():
                for table in table_names:
                    schema_editor.execute(
                        schema_editor.sql_delete_table % {"table": schema_editor.quote_name(table)}
                    )

        self.info(f"Dropped {len(table_names)} table(s).")
```

Append to `DB_COMMANDS`: `("db:wipe", DbWipeCommand),`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/db.py tests/test_cli.py
git commit -m "Add db:wipe command"
```

---

## Task 10: `db:table` and `db:show`

**Files:**
- Modify: `src/yello/cli/db.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `DbTableCommand(Command)` with `handle(name: str)`, `DbShowCommand(Command)` with `handle()`. Both appended to `DB_COMMANDS`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_db_table(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("make:migration").returncode == 0
        assert run_cli("migrate").returncode == 0

        r = run_cli("db:table", "app_post")
        assert r.returncode == 0, r.stderr
        assert "title" not in r.stdout  # Post model has no `title` field by default; id/created_at must show
        assert "id" in r.stdout

    def test_db_show(self, project_dir, run_cli):
        assert run_cli("migrate").returncode == 0
        r = run_cli("db:show")
        assert r.returncode == 0, r.stderr
        assert "sqlite3" in r.stdout.lower() or "sqlite" in r.stdout.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestProjectFlow::test_db_table tests/test_cli.py::TestProjectFlow::test_db_show -v`
Expected: FAIL — commands don't exist.

- [ ] **Step 3: Write the implementation**

Add to `src/yello/cli/db.py`:

```python
class DbTableCommand(Command):
    """Show the columns of a single database table."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Table name, e.g. app_post."),
    ) -> None:
        _bootstrap_django()
        from django.db import connection
        from rich.table import Table

        from yello.console.command import console

        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, name)

        table = Table(title=f"Columns in {name}")
        table.add_column("Column", style="cyan")
        table.add_column("Type")
        table.add_column("Null?")
        for column in description:
            table.add_row(column.name, str(column.type_code), "Yes" if column.null_ok else "No")
        console.print(table)


class DbShowCommand(Command):
    """Show the database connection and every table with its row count."""

    def handle(self) -> None:
        _bootstrap_django()
        from django.conf import settings
        from django.db import connection
        from rich.table import Table

        from yello.console.command import console

        db_settings = settings.DATABASES["default"]
        self.line(f"Engine:   {db_settings['ENGINE']}")
        self.line(f"Database: {db_settings['NAME']}")

        with connection.cursor() as cursor:
            table_names = connection.introspection.table_names(cursor)

        table = Table(title="Tables")
        table.add_column("Table", style="cyan")
        table.add_column("Rows", justify="right")
        with connection.cursor() as cursor:
            for name in table_names:
                cursor.execute(f"SELECT COUNT(*) FROM {connection.ops.quote_name(name)}")
                count = cursor.fetchone()[0]
                table.add_row(name, str(count))
        console.print(table)
```

Append to `DB_COMMANDS`: `("db:table", DbTableCommand), ("db:show", DbShowCommand),`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/db.py tests/test_cli.py
git commit -m "Add db:table and db:show commands"
```

---

## Task 11: Wire `--seed` into `migrate` / `migrate:fresh`

**Files:**
- Modify: `src/yello/cli/migrate.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `run_seed(seeder_class: str = "DatabaseSeeder")` from Task 8's `db.py`.
- Produces: `MigrateCommand.handle` and `MigrateFreshCommand.handle` actually call `run_seed()` when `--seed` is passed (replacing the `self.warn("Seeding is not wired up yet.")` placeholder from Task 6).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_migrate_seed_flag_runs_seeder(self, project_dir, run_cli):
        seeders_dir = project_dir / "src/app/Database/Seeders"
        seeders_dir.mkdir(parents=True)
        (seeders_dir / "__init__.py").write_text("")
        (seeders_dir / "DatabaseSeeder.py").write_text(
            "from yello.db.seeder import Seeder\n\n\n"
            "class DatabaseSeeder(Seeder):\n"
            "    def run(self) -> None:\n"
            "        print('migrate seeded!')\n"
        )
        r = run_cli("migrate", "--seed")
        assert r.returncode == 0, r.stderr
        assert "migrate seeded!" in r.stdout

    def test_migrate_fresh_seed_flag_runs_seeder(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("make:migration").returncode == 0
        assert run_cli("migrate").returncode == 0

        seeders_dir = project_dir / "src/app/Database/Seeders"
        seeders_dir.mkdir(parents=True)
        (seeders_dir / "__init__.py").write_text("")
        (seeders_dir / "DatabaseSeeder.py").write_text(
            "from yello.db.seeder import Seeder\n\n\n"
            "class DatabaseSeeder(Seeder):\n"
            "    def run(self) -> None:\n"
            "        print('fresh seeded!')\n"
        )
        r = run_cli("migrate:fresh", "--seed", "--yes")
        assert r.returncode == 0, r.stderr
        assert "fresh seeded!" in r.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestProjectFlow::test_migrate_seed_flag_runs_seeder tests/test_cli.py::TestProjectFlow::test_migrate_fresh_seed_flag_runs_seeder -v`
Expected: FAIL — output only contains the "Seeding is not wired up yet." warning, not "migrate seeded!"/"fresh seeded!"

- [ ] **Step 3: Write the implementation**

In `src/yello/cli/migrate.py`, replace both occurrences of:

```python
        if seed:
            self.warn("Seeding is not wired up yet.")
```

with:

```python
        if seed:
            from yello.cli.db import run_seed

            run_seed()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/migrate.py tests/test_cli.py
git commit -m "Wire --seed into migrate and migrate:fresh"
```

---

## Task 12: `make:factory` — `Factory` base class

**Files:**
- Create: `src/yello/db/factory.py`
- Create: `src/yello/templates/factory/factory_name.py-tpl`
- Modify: `src/yello/cli/make.py`
- Test: `tests/test_factory.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `yello.db.factory.Factory` with class attribute `model`, method `definition() -> dict` (raises `NotImplementedError`), `make(**overrides)` (returns an unsaved instance), `create(**overrides)` (saves and returns it). `MakeFactoryCommand` appended to `MAKE_COMMANDS` as `("make:factory", MakeFactoryCommand)`, writing to `src/app/Database/Factories/<Name>Factory.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_factory.py
import pytest

from tests.models import TestPost
from yello.db.factory import Factory


class PostFactory(Factory):
    model = TestPost

    def definition(self) -> dict:
        return {"title": "A post"}


class TestFactoryBase:
    def test_definition_not_implemented_by_default(self):
        with pytest.raises(NotImplementedError):
            Factory().definition()

    def test_make_returns_unsaved_instance(self):
        post = PostFactory().make()
        assert post.title == "A post"
        assert post.pk is not None  # UUID assigned client-side by BaseModel
        assert not TestPost.objects.filter(pk=post.pk).exists()

    def test_make_applies_overrides(self):
        post = PostFactory().make(title="Custom")
        assert post.title == "Custom"

    @pytest.mark.django_db
    def test_create_persists_instance(self):
        post = PostFactory().create()
        assert TestPost.objects.filter(pk=post.pk).exists()
```

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_make_factory(self, project_dir, run_cli):
        r = run_cli("make:factory", "PostFactory", "--domain", "Posts")
        assert r.returncode == 0, r.stderr
        target = project_dir / "src/app/Database/Factories/PostFactory.py"
        assert target.exists()
        assert "class PostFactory(Factory):" in target.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_factory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yello.db.factory'`

- [ ] **Step 3: Write the implementation**

```python
# src/yello/db/factory.py
"""Base for Database/Factories classes."""


class Factory:
    model = None

    def definition(self) -> dict:
        raise NotImplementedError

    def make(self, **overrides):
        data = {**self.definition(), **overrides}
        return self.model(**data)

    def create(self, **overrides):
        instance = self.make(**overrides)
        instance.save()
        return instance
```

```
# src/yello/templates/factory/factory_name.py-tpl
from yello.db.factory import Factory
from app.Domain.{{ domain }}.Models.{{ model_name }} import {{ model_name }}


class {{ factory_name }}(Factory):
    model = {{ model_name }}

    def definition(self) -> dict:
        raise NotImplementedError
```

Add to `src/yello/cli/make.py`:

```python
class MakeFactoryCommand(Command):
    """Create a Database/Factories/<Name>Factory.py for a model."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Factory class name, e.g. PostFactory."),
        domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        model_name = name[: -len("Factory")] if name.endswith("Factory") else name
        target = app_dir / "Database" / "Factories" / f"{name}.py"

        _ensure_not_exists(target)
        _render_template(
            _tpl_path("factory"), target, factory_name=name, model_name=model_name, domain=domain
        )

        self.info(f"Created {target.relative_to(_project_root())}")
```

Append to `MAKE_COMMANDS`: `("make:factory", MakeFactoryCommand),`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_factory.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/db/factory.py src/yello/templates/factory src/yello/cli/make.py tests/test_factory.py tests/test_cli.py
git commit -m "Add Factory base class and make:factory command"
```

---

## Task 13: `make:test`

**Files:**
- Create: `src/yello/templates/test/test_name.py-tpl`
- Modify: `src/yello/cli/make.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `MakeTestCommand` appended to `MAKE_COMMANDS` as `("make:test", MakeTestCommand)`, writing to `tests/<Name>Test.py` at the project root (not under `src/app/`), creating `tests/` if missing.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_make_test(self, project_dir, run_cli):
        r = run_cli("make:test", "PostTest")
        assert r.returncode == 0, r.stderr
        target = project_dir / "tests/PostTest.py"
        assert target.exists()
        assert "class PostTest(TestCase):" in target.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestProjectFlow::test_make_test -v`
Expected: FAIL — `make:test` doesn't exist.

- [ ] **Step 3: Write the implementation**

```
# src/yello/templates/test/test_name.py-tpl
from django.test import TestCase


class {{ class_name }}(TestCase):
    def test_example(self) -> None:
        raise NotImplementedError
```

Add to `src/yello/cli/make.py`:

```python
class MakeTestCommand(Command):
    """Create a tests/<Name>.py test case."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Test class name, e.g. PostTest."),
    ) -> None:
        target = _project_root() / "tests" / f"{name}.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("test"), target, class_name=name)

        self.info(f"Created {target.relative_to(_project_root())}")
```

Append to `MAKE_COMMANDS`: `("make:test", MakeTestCommand),`

(No `self.bootstrap()` call needed — writing a plain `TestCase` subclass doesn't require Django to be configured.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/templates/test src/yello/cli/make.py tests/test_cli.py
git commit -m "Add make:test command"
```

---

## Task 14: `make:enum`

**Files:**
- Create: `src/yello/templates/enum/enum_name.py-tpl`
- Modify: `src/yello/cli/make.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `MakeEnumCommand` appended to `MAKE_COMMANDS` as `("make:enum", MakeEnumCommand)`, writing to `src/app/Enums/<Name>.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_make_enum(self, project_dir, run_cli):
        r = run_cli("make:enum", "PostStatus")
        assert r.returncode == 0, r.stderr
        target = project_dir / "src/app/Enums/PostStatus.py"
        assert target.exists()
        assert "class PostStatus(Enum):" in target.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestProjectFlow::test_make_enum -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

```
# src/yello/templates/enum/enum_name.py-tpl
from enum import Enum


class {{ class_name }}(Enum):
    pass
```

Add to `src/yello/cli/make.py`:

```python
class MakeEnumCommand(Command):
    """Create a src/app/Enums/<Name>.py enum."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Enum class name, e.g. PostStatus."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Enums" / f"{name}.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("enum"), target, class_name=name)

        self.info(f"Created {target.relative_to(_project_root())}")
```

Append to `MAKE_COMMANDS`: `("make:enum", MakeEnumCommand),`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/templates/enum src/yello/cli/make.py tests/test_cli.py
git commit -m "Add make:enum command"
```

---

## Task 15: `make:exception` — `YelloException` base class

**Files:**
- Create: `src/yello/exceptions/__init__.py`
- Create: `src/yello/exceptions/base.py`
- Create: `src/yello/templates/exception/exception_name.py-tpl`
- Modify: `src/yello/cli/make.py`
- Test: `tests/test_exceptions.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `yello.exceptions.base.YelloException(Exception)` (no extra behavior — a marker base). `MakeExceptionCommand` appended to `MAKE_COMMANDS` as `("make:exception", MakeExceptionCommand)`, writing to `src/app/Exceptions/<Name>.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_exceptions.py
import pytest

from yello.exceptions.base import YelloException


class TestYelloException:
    def test_is_an_exception(self):
        with pytest.raises(YelloException):
            raise YelloException("boom")
```

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_make_exception(self, project_dir, run_cli):
        r = run_cli("make:exception", "InsufficientStockException")
        assert r.returncode == 0, r.stderr
        target = project_dir / "src/app/Exceptions/InsufficientStockException.py"
        assert target.exists()
        assert "class InsufficientStockException(YelloException):" in target.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_exceptions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yello.exceptions'`

- [ ] **Step 3: Write the implementation**

```python
# src/yello/exceptions/__init__.py
```

```python
# src/yello/exceptions/base.py
class YelloException(Exception):
    """Base for all app-defined exceptions."""
```

```
# src/yello/templates/exception/exception_name.py-tpl
from yello.exceptions.base import YelloException


class {{ class_name }}(YelloException):
    pass
```

Add to `src/yello/cli/make.py`:

```python
class MakeExceptionCommand(Command):
    """Create a src/app/Exceptions/<Name>.py exception class."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Exception class name, e.g. InsufficientStockException."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Exceptions" / f"{name}.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("exception"), target, class_name=name)

        self.info(f"Created {target.relative_to(_project_root())}")
```

Append to `MAKE_COMMANDS`: `("make:exception", MakeExceptionCommand),`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_exceptions.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/exceptions src/yello/templates/exception src/yello/cli/make.py tests/test_exceptions.py tests/test_cli.py
git commit -m "Add YelloException base class and make:exception command"
```

---

## Task 16: `make:rule` — `Rule` base class

**Files:**
- Create: `src/yello/validation/__init__.py`
- Create: `src/yello/validation/rule.py`
- Create: `src/yello/templates/rule/rule_name.py-tpl`
- Modify: `src/yello/cli/make.py`
- Test: `tests/test_rule.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `yello.validation.rule.Rule` with class attribute `message = "The given value is invalid."`, method `passes(value) -> bool` (raises `NotImplementedError`), and `__call__(value)` (raises `rest_framework.serializers.ValidationError(self.message)` if `passes()` is falsy — makes it usable directly as a DRF field validator). `MakeRuleCommand` appended to `MAKE_COMMANDS` as `("make:rule", MakeRuleCommand)`, writing to `src/app/Rules/<Name>.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rule.py
import pytest
from rest_framework.serializers import ValidationError

from yello.validation.rule import Rule


class Even(Rule):
    message = "Value must be even."

    def passes(self, value) -> bool:
        return value % 2 == 0


class TestRule:
    def test_passes_not_implemented_by_default(self):
        with pytest.raises(NotImplementedError):
            Rule().passes(1)

    def test_call_is_noop_when_it_passes(self):
        Even()(4)  # must not raise

    def test_call_raises_validation_error_with_message(self):
        with pytest.raises(ValidationError) as exc_info:
            Even()(3)
        assert "Value must be even." in str(exc_info.value)
```

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_make_rule(self, project_dir, run_cli):
        r = run_cli("make:rule", "Even")
        assert r.returncode == 0, r.stderr
        target = project_dir / "src/app/Rules/Even.py"
        assert target.exists()
        assert "class Even(Rule):" in target.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rule.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yello.validation'`

- [ ] **Step 3: Write the implementation**

```python
# src/yello/validation/__init__.py
```

```python
# src/yello/validation/rule.py
"""Base for src/app/Rules classes — usable directly as a DRF field validator."""


class Rule:
    message = "The given value is invalid."

    def passes(self, value) -> bool:
        raise NotImplementedError

    def __call__(self, value) -> None:
        if not self.passes(value):
            from rest_framework.serializers import ValidationError

            raise ValidationError(self.message)
```

```
# src/yello/templates/rule/rule_name.py-tpl
from yello.validation.rule import Rule


class {{ class_name }}(Rule):
    message = "The given value is invalid."

    def passes(self, value) -> bool:
        raise NotImplementedError
```

Add to `src/yello/cli/make.py`:

```python
class MakeRuleCommand(Command):
    """Create a src/app/Rules/<Name>.py validation rule."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Rule class name, e.g. Even."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Rules" / f"{name}.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("rule"), target, class_name=name)

        self.info(f"Created {target.relative_to(_project_root())}")
```

Append to `MAKE_COMMANDS`: `("make:rule", MakeRuleCommand),`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_rule.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/validation src/yello/templates/rule src/yello/cli/make.py tests/test_rule.py tests/test_cli.py
git commit -m "Add Rule base class and make:rule command"
```

---

## Task 17: `make:mail` — `Mailable` base class

**Files:**
- Create: `src/yello/mail/__init__.py`
- Create: `src/yello/mail/mailable.py`
- Create: `src/yello/templates/mail/mail_name.py-tpl`
- Modify: `src/yello/cli/make.py`
- Test: `tests/test_mailable.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `yello.mail.mailable.Mailable` with `subject = ""`, `build() -> dict` (raises `NotImplementedError`, expected to return at least `{"body": str}`), `send(to: list[str]) -> None` (calls `build()` then `django.core.mail.send_mail`). `MakeMailCommand` appended to `MAKE_COMMANDS` as `("make:mail", MakeMailCommand)`, writing to `src/app/Mail/<Name>.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_mailable.py
import pytest

from yello.mail.mailable import Mailable


class WelcomeMail(Mailable):
    subject = "Welcome!"

    def build(self) -> dict:
        return {"body": "Thanks for signing up."}


class TestMailable:
    def test_build_not_implemented_by_default(self):
        with pytest.raises(NotImplementedError):
            Mailable().build()

    def test_send_calls_django_send_mail(self, mailoutbox):
        WelcomeMail().send(to=["user@example.com"])
        assert len(mailoutbox) == 1
        assert mailoutbox[0].subject == "Welcome!"
        assert mailoutbox[0].body == "Thanks for signing up."
        assert mailoutbox[0].to == ["user@example.com"]
```

Note: `mailoutbox` requires `pytest-django`'s mail fixture, already available transitively — no new dependency.

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_make_mail(self, project_dir, run_cli):
        r = run_cli("make:mail", "WelcomeMail")
        assert r.returncode == 0, r.stderr
        target = project_dir / "src/app/Mail/WelcomeMail.py"
        assert target.exists()
        assert "class WelcomeMail(Mailable):" in target.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mailable.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yello.mail'`

- [ ] **Step 3: Write the implementation**

```python
# src/yello/mail/__init__.py
```

```python
# src/yello/mail/mailable.py
"""Base for src/app/Mail classes."""


class Mailable:
    subject = ""

    def build(self) -> dict:
        raise NotImplementedError

    def send(self, to: list[str]) -> None:
        from django.core.mail import send_mail

        data = self.build()
        send_mail(self.subject, data.get("body", ""), None, to)
```

```
# src/yello/templates/mail/mail_name.py-tpl
from yello.mail.mailable import Mailable


class {{ class_name }}(Mailable):
    subject = ""

    def build(self) -> dict:
        raise NotImplementedError
```

Add to `src/yello/cli/make.py`:

```python
class MakeMailCommand(Command):
    """Create a src/app/Mail/<Name>.py mailable."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Mailable class name, e.g. WelcomeMail."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Mail" / f"{name}.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("mail"), target, class_name=name)

        self.info(f"Created {target.relative_to(_project_root())}")
```

Append to `MAKE_COMMANDS`: `("make:mail", MakeMailCommand),`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_mailable.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/mail src/yello/templates/mail src/yello/cli/make.py tests/test_mailable.py tests/test_cli.py
git commit -m "Add Mailable base class and make:mail command"
```

---

## Task 18: `make:middleware` — `Middleware` base class

**Files:**
- Create: `src/yello/http/middleware.py`
- Create: `src/yello/templates/middleware/middleware_name.py-tpl`
- Modify: `src/yello/cli/make.py`
- Test: `tests/test_middleware.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `yello.http.middleware.Middleware` implementing the Django middleware protocol (`__init__(self, get_response)`, `__call__(self, request)`), with `before(request)` (returns `None` or an early `HttpResponse`) and `after(request, response)` (returns `response`, override to mutate) as the Laravel-style hooks subclasses override. `MakeMiddlewareCommand` appended to `MAKE_COMMANDS` as `("make:middleware", MakeMiddlewareCommand)`, writing to `src/app/Http/Middleware/<Name>.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_middleware.py
from django.http import HttpResponse

from yello.http.middleware import Middleware


class BlockEverything(Middleware):
    def before(self, request):
        return HttpResponse("blocked", status=403)


class AddHeader(Middleware):
    def after(self, request, response):
        response["X-Test"] = "yes"
        return response


class TestMiddleware:
    def test_before_can_short_circuit(self):
        mw = BlockEverything(get_response=lambda request: HttpResponse("should not run"))
        response = mw(request=object())
        assert response.status_code == 403
        assert response.content == b"blocked"

    def test_after_can_mutate_response(self):
        mw = AddHeader(get_response=lambda request: HttpResponse("ok"))
        response = mw(request=object())
        assert response["X-Test"] == "yes"

    def test_default_passes_through(self):
        mw = Middleware(get_response=lambda request: HttpResponse("passthrough"))
        response = mw(request=object())
        assert response.content == b"passthrough"
```

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_make_middleware(self, project_dir, run_cli):
        r = run_cli("make:middleware", "EnsureIsAdmin")
        assert r.returncode == 0, r.stderr
        target = project_dir / "src/app/Http/Middleware/EnsureIsAdmin.py"
        assert target.exists()
        assert "class EnsureIsAdmin(Middleware):" in target.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_middleware.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yello.http.middleware'`

- [ ] **Step 3: Write the implementation**

```python
# src/yello/http/middleware.py
"""Base for src/app/Http/Middleware classes."""


class Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def before(self, request):
        """Return an HttpResponse to short-circuit, or None to continue."""
        return None

    def after(self, request, response):
        """Return the (optionally mutated) response."""
        return response

    def __call__(self, request):
        early = self.before(request)
        if early is not None:
            return early
        response = self.get_response(request)
        return self.after(request, response)
```

```
# src/yello/templates/middleware/middleware_name.py-tpl
from yello.http.middleware import Middleware


class {{ class_name }}(Middleware):
    def before(self, request):
        return None
```

Add to `src/yello/cli/make.py`:

```python
class MakeMiddlewareCommand(Command):
    """Create a src/app/Http/Middleware/<Name>.py middleware class."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Middleware class name, e.g. EnsureIsAdmin."),
    ) -> None:
        self.bootstrap()
        app_dir = _src_app_dir(_project_root())
        target = app_dir / "Http" / "Middleware" / f"{name}.py"

        _ensure_not_exists(target)
        _render_template(_tpl_path("middleware"), target, class_name=name)

        self.info(f"Created {target.relative_to(_project_root())}")
```

Append to `MAKE_COMMANDS`: `("make:middleware", MakeMiddlewareCommand),`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_middleware.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/http/middleware.py src/yello/templates/middleware src/yello/cli/make.py tests/test_middleware.py tests/test_cli.py
git commit -m "Add Middleware base class and make:middleware command"
```

---

## Task 19: `model:show`

**Files:**
- Create: `src/yello/cli/model.py`
- Modify: `src/yello/cli/__init__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `ModelShowCommand(Command)` with `handle(name: str, domain: str)`. Registered directly (not via a list — it's a single command, same as `route:list`/`serve`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_model_show(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        r = run_cli("model:show", "Post", "--domain", "Posts")
        assert r.returncode == 0, r.stderr
        assert "id" in r.stdout
        assert "created_at" in r.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestProjectFlow::test_model_show -v`
Expected: FAIL — `model:show` doesn't exist.

- [ ] **Step 3: Write the implementation**

```python
# src/yello/cli/model.py
"""yello model:show — inspect a model's fields and relations."""

import typer

from yello.console.command import Command, console


class ModelShowCommand(Command):
    """Show a model's fields, types, and relations."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Model name, e.g. Post."),
        domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
    ) -> None:
        self.bootstrap()
        import importlib

        from rich.table import Table

        module = importlib.import_module(f"app.Domain.{domain}.Models.{name}")
        model = getattr(module, name)

        table = Table(title=f"{name} fields")
        table.add_column("Field", style="cyan")
        table.add_column("Type")
        table.add_column("Null?")
        table.add_column("Relation")
        for field in model._meta.get_fields():
            relation = getattr(field, "related_model", None)
            table.add_row(
                field.name,
                type(field).__name__,
                "Yes" if getattr(field, "null", False) else "No",
                relation.__name__ if relation else "",
            )
        console.print(table)
```

Update `src/yello/cli/__init__.py`:

```python
from yello.cli import db, init, make, migrate, model, route, serve
```

and register:

```python
app.command(name="model:show")(model.ModelShowCommand().handle)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/model.py src/yello/cli/__init__.py tests/test_cli.py
git commit -m "Add model:show command"
```

---

## Task 20: `about`

**Files:**
- Create: `src/yello/cli/about.py`
- Modify: `src/yello/cli/__init__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `AboutCommand(Command)` with `handle()`, printing yello version, Python version, Django version, settings module, DB engine, `DEBUG`, and installed app count.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_about(self, project_dir, run_cli):
        r = run_cli("about")
        assert r.returncode == 0, r.stderr
        assert "yello" in r.stdout.lower()
        assert "django" in r.stdout.lower()
        assert "config.settings" in r.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestProjectFlow::test_about -v`
Expected: FAIL — `about` doesn't exist.

- [ ] **Step 3: Write the implementation**

```python
# src/yello/cli/about.py
"""yello about — environment and project diagnostics."""

import sys

from yello.__about__ import __version__
from yello.console.command import Command


class AboutCommand(Command):
    """Show yello, Python, and Django environment information."""

    def handle(self) -> None:
        self.line(f"yello:    {__version__}")
        self.line(f"Python:   {sys.version.split()[0]}")

        try:
            self.bootstrap()
        except Exception as exc:  # no project / bad settings — still report what we can
            self.warn(f"Django:   could not bootstrap ({exc})")
            return

        import django
        from django.conf import settings

        self.line(f"Django:   {django.get_version()}")
        self.line(f"Settings: {settings.SETTINGS_MODULE}")
        self.line(f"Database: {settings.DATABASES['default']['ENGINE']}")
        self.line(f"Debug:    {settings.DEBUG}")
        self.line(f"Apps:     {len(settings.INSTALLED_APPS)} installed")
```

Update `src/yello/cli/__init__.py`:

```python
from yello.cli import about, db, init, make, migrate, model, route, serve
```

and register:

```python
app.command(name="about")(about.AboutCommand().handle)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/about.py src/yello/cli/__init__.py tests/test_cli.py
git commit -m "Add about command"
```

---

## Task 21: `key:generate`

**Files:**
- Create: `src/yello/cli/key.py`
- Modify: `src/yello/cli/__init__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `KeyGenerateCommand(Command)` with `handle(show: bool)`. Writes/replaces the `DJANGO_SECRET_KEY=` line in the project's `.env` (creating it if missing, preserving other lines); `--show` prints the generated key without writing.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_key_generate_writes_env_file(self, project_dir, run_cli):
        r = run_cli("key:generate")
        assert r.returncode == 0, r.stderr
        env_file = project_dir / ".env"
        assert env_file.exists()
        assert "DJANGO_SECRET_KEY=" in env_file.read_text()

    def test_key_generate_preserves_other_lines(self, project_dir, run_cli):
        (project_dir / ".env").write_text("FOO=bar\n")
        r = run_cli("key:generate")
        assert r.returncode == 0, r.stderr
        content = (project_dir / ".env").read_text()
        assert "FOO=bar" in content
        assert "DJANGO_SECRET_KEY=" in content

    def test_key_generate_show_does_not_write(self, project_dir, run_cli):
        r = run_cli("key:generate", "--show")
        assert r.returncode == 0, r.stderr
        assert not (project_dir / ".env").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestProjectFlow::test_key_generate_writes_env_file -v`
Expected: FAIL — `key:generate` doesn't exist.

- [ ] **Step 3: Write the implementation**

```python
# src/yello/cli/key.py
"""yello key:generate — generate/rotate the Django secret key."""

import typer

from yello.cli._helpers import _project_root
from yello.console.command import Command


class KeyGenerateCommand(Command):
    """Generate a new Django secret key into .env."""

    def handle(
        self,
        show: bool = typer.Option(False, "--show", help="Print the key without writing it."),
    ) -> None:
        from django.core.management.utils import get_random_secret_key

        key = get_random_secret_key()

        if show:
            self.line(key)
            return

        env_path = _project_root() / ".env"
        lines = env_path.read_text().splitlines() if env_path.exists() else []
        lines = [line for line in lines if not line.startswith("DJANGO_SECRET_KEY=")]
        lines.append(f"DJANGO_SECRET_KEY={key}")
        env_path.write_text("\n".join(lines) + "\n")

        self.info(f"Application key set in {env_path.name}")
```

Update `src/yello/cli/__init__.py`:

```python
from yello.cli import about, db, init, key, make, migrate, model, route, serve
```

and register:

```python
app.command(name="key:generate")(key.KeyGenerateCommand().handle)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/key.py src/yello/cli/__init__.py tests/test_cli.py
git commit -m "Add key:generate command"
```

---

## Task 22: `tinker`

**Files:**
- Create: `src/yello/cli/tinker.py`
- Modify: `src/yello/cli/__init__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `TinkerCommand(Command)` with `handle()`. Bootstraps Django, builds a namespace dict of every installed model keyed by class name plus `django`, and starts `code.InteractiveConsole(namespace).interact()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_tinker_preloads_models_and_exits_on_eof(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("make:migration").returncode == 0
        assert run_cli("migrate").returncode == 0

        r = run_cli("tinker", input="Post\n")
        assert r.returncode == 0, r.stderr
        assert "<class 'app.Domain.Posts.Models.Post.Post'>" in r.stdout
```

Note: `run_cli` in `conftest.py` doesn't currently accept `input=`; extend it:

```python
# tests/conftest.py — modify run_cli's _run
    def _run(*args, env_extra=None, input=None):
        env = dict(os.environ)
        env["DJANGO_SETTINGS_MODULE"] = "config.settings"
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            [sys.executable, "-m", "yello", *args],
            cwd=str(project_dir),
            env=env,
            capture_output=True,
            text=True,
            input=input,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::TestProjectFlow::test_tinker_preloads_models_and_exits_on_eof -v`
Expected: FAIL — `tinker` doesn't exist.

- [ ] **Step 3: Write the implementation**

```python
# src/yello/cli/tinker.py
"""yello tinker — an interactive shell with the project's models preloaded."""

import code

from yello.console.command import Command


class TinkerCommand(Command):
    """Start an interactive Python shell with every model preloaded."""

    def handle(self) -> None:
        self.bootstrap()
        import django
        from django.apps import apps

        namespace = {"django": django}
        for model in apps.get_models():
            namespace[model.__name__] = model

        self.info(f"Preloaded {len(apps.get_models())} model(s). Ctrl-D to exit.")
        code.InteractiveConsole(namespace).interact(banner="", exitmsg="")
```

Update `src/yello/cli/__init__.py`:

```python
from yello.cli import about, db, init, key, make, migrate, model, route, serve, tinker
```

and register:

```python
app.command(name="tinker")(tinker.TinkerCommand().handle)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/cli/tinker.py src/yello/cli/__init__.py tests/test_cli.py tests/conftest.py
git commit -m "Add tinker command"
```

---

## Task 23: Maintenance mode — `MaintenanceModeMiddleware`, `down`, `up`

**Files:**
- Create: `src/yello/http/maintenance.py`
- Create: `src/yello/cli/maintenance.py`
- Modify: `src/yello/cli/__init__.py`
- Modify: `src/yello/settings/base.py`
- Modify: `src/yello/templates/project/config/settings.py`
- Test: `tests/test_maintenance.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `yello.http.maintenance.MaintenanceModeMiddleware(get_response)` — Django middleware; if `storage/framework/maintenance.json` exists at `Path.cwd()`, returns a 503 `JsonResponse` with the stored `message` (and `Retry-After` header if `retry` was stored); otherwise passes through. `DownCommand(Command)` with `handle(message: str, retry: int | None)` writes that file (creating `storage/framework/` if missing). `UpCommand(Command)` with `handle()` deletes it, printing "Application is already up." if it didn't exist.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_maintenance.py
import json

from django.http import HttpResponse

from yello.http.maintenance import MaintenanceModeMiddleware


class TestMaintenanceModeMiddleware:
    def test_passes_through_when_no_lock_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mw = MaintenanceModeMiddleware(get_response=lambda request: HttpResponse("ok"))
        response = mw(request=object())
        assert response.status_code == 200

    def test_returns_503_when_lock_file_present(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        lock_dir = tmp_path / "storage" / "framework"
        lock_dir.mkdir(parents=True)
        (lock_dir / "maintenance.json").write_text(json.dumps({"message": "Down for repairs"}))

        mw = MaintenanceModeMiddleware(get_response=lambda request: HttpResponse("should not run"))
        response = mw(request=object())
        assert response.status_code == 503
        assert b"Down for repairs" in response.content

    def test_includes_retry_after_header(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        lock_dir = tmp_path / "storage" / "framework"
        lock_dir.mkdir(parents=True)
        (lock_dir / "maintenance.json").write_text(json.dumps({"message": "brb", "retry": 60}))

        mw = MaintenanceModeMiddleware(get_response=lambda request: HttpResponse("should not run"))
        response = mw(request=object())
        assert response["Retry-After"] == "60"
```

```python
# tests/test_cli.py — add to TestProjectFlow
    def test_down_then_up(self, project_dir, run_cli):
        r = run_cli("down", "--message", "Maintenance in progress")
        assert r.returncode == 0, r.stderr
        lock_file = project_dir / "storage/framework/maintenance.json"
        assert lock_file.exists()
        assert "Maintenance in progress" in lock_file.read_text()

        r = run_cli("up")
        assert r.returncode == 0, r.stderr
        assert not lock_file.exists()

        r = run_cli("up")
        assert r.returncode == 0, r.stderr
        assert "already up" in r.stdout.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_maintenance.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yello.http.maintenance'`

- [ ] **Step 3: Write the implementation**

```python
# src/yello/http/maintenance.py
"""Maintenance-mode middleware — checks storage/framework/maintenance.json."""

import json
from pathlib import Path

from django.http import JsonResponse


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lock_file = Path.cwd() / "storage" / "framework" / "maintenance.json"
        if lock_file.exists():
            data = json.loads(lock_file.read_text())
            response = JsonResponse({"message": data.get("message", "Down for maintenance.")}, status=503)
            if data.get("retry"):
                response["Retry-After"] = str(data["retry"])
            return response
        return self.get_response(request)
```

```python
# src/yello/cli/maintenance.py
"""yello down / up — maintenance mode."""

import json

import typer

from yello.cli._helpers import _project_root
from yello.console.command import Command


def _lock_file():
    return _project_root() / "storage" / "framework" / "maintenance.json"


class DownCommand(Command):
    """Put the application into maintenance mode."""

    def handle(
        self,
        message: str = typer.Option("Down for maintenance.", "--message", "-m"),
        retry: int = typer.Option(None, "--retry", help="Retry-After seconds to advertise."),
    ) -> None:
        lock_file = _lock_file()
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"message": message}
        if retry is not None:
            data["retry"] = retry
        lock_file.write_text(json.dumps(data))
        self.info("Application is now in maintenance mode.")


class UpCommand(Command):
    """Bring the application out of maintenance mode."""

    def handle(self) -> None:
        lock_file = _lock_file()
        if not lock_file.exists():
            self.line("Application is already up.")
            return
        lock_file.unlink()
        self.info("Application is now live.")
```

Update `src/yello/cli/__init__.py`:

```python
from yello.cli import about, db, init, key, maintenance, make, migrate, model, route, serve, tinker
```

and register:

```python
app.command(name="down")(maintenance.DownCommand().handle)
app.command(name="up")(maintenance.UpCommand().handle)
```

Add `"yello.http.maintenance.MaintenanceModeMiddleware"` as the **first** entry of `MIDDLEWARE` in both `src/yello/settings/base.py` and `src/yello/templates/project/config/settings.py`:

```python
MIDDLEWARE = [
    "yello.http.maintenance.MaintenanceModeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    ...
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_maintenance.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/yello/http/maintenance.py src/yello/cli/maintenance.py src/yello/cli/__init__.py src/yello/settings/base.py src/yello/templates/project/config/settings.py tests/test_maintenance.py tests/test_cli.py
git commit -m "Add maintenance mode: down/up commands and middleware"
```

---

## Task 24: Full regression pass + help-listing coverage

**Files:**
- Modify: `tests/test_cli.py`

**Interfaces:**
- No new production code — this task only strengthens the `test_help_lists_all_commands` assertion to cover every command added across Tasks 1-23, and runs the entire suite as the final gate.

- [ ] **Step 1: Extend the help-listing test**

```python
# tests/test_cli.py
class TestCliSmoke:
    def test_help_lists_all_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for name in (
            "make:model",
            "make:controller",
            "make:request",
            "make:resource",
            "make:policy",
            "make:admin",
            "make:migration",
            "make:seeder",
            "make:factory",
            "make:test",
            "make:enum",
            "make:exception",
            "make:rule",
            "make:mail",
            "make:middleware",
            "route:list",
            "serve",
            "dev",
            "init",
            "migrate",
            "migrate:fresh",
            "migrate:rollback",
            "migrate:status",
            "db:seed",
            "db:wipe",
            "db:table",
            "db:show",
            "model:show",
            "about",
            "key:generate",
            "tinker",
            "down",
            "up",
        ):
            assert name in result.output, f"{name} missing from --help output"
```

- [ ] **Step 2: Run the full suite**

Run: `python -m pytest tests/ -v`
Expected: PASS — every test across all 24 tasks.

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "Extend CLI help-listing test to cover full Artisan-parity command set"
```
