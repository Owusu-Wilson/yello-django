"""yello make:* — scaffold files into the Laravel-style domain layout."""

import os
from pathlib import Path

import typer

from yello.cli._helpers import (
    _bootstrap_django,
    _ensure_not_exists,
    _project_root,
    _render_template,
    _src_app_dir,
    console,
)
from yello.codegen.aggregator import add_model_import


def _tpl_path(kind: str) -> Path:
    return Path(__file__).resolve().parent.parent / "templates" / kind / f"{kind}_name.py-tpl"


def _pluralize(name: str) -> str:
    lower = name.lower()
    if lower.endswith("s"):
        return lower + "es"
    return lower + "s"


def make_model(
    name: str = typer.Argument(..., help="Model name, e.g. Post."),
    domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
) -> None:
    """Create a Domain/<Domain>/Models/<Name>.py model and update app/models.py."""
    _bootstrap_django()
    app_dir = _src_app_dir(_project_root())
    target = app_dir / "Domain" / domain / "Models" / f"{name}.py"

    _ensure_not_exists(target)
    _render_template(_tpl_path("model"), target, model_name=name, domain=domain)
    changed = add_model_import(_project_root(), domain, name)

    console.print(f"[green]Created[/green] {target.relative_to(_project_root())}")
    if changed:
        console.print("[green]Updated[/green] src/app/models.py (model import appended)")


def make_controller(
    name: str = typer.Argument(..., help="Model name, e.g. Post."),
    domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
) -> None:
    """Create an Http/Controllers/<Name>Controller.py."""
    _bootstrap_django()
    app_dir = _src_app_dir(_project_root())
    target = app_dir / "Http" / "Controllers" / f"{name}Controller.py"

    _ensure_not_exists(target)
    _render_template(_tpl_path("controller"), target, model_name=name, domain=domain)

    console.print(f"[green]Created[/green] {target.relative_to(_project_root())}")
    console.print("Add to your routes, e.g. in routes/api.py:")
    console.print(f"  [cyan]path(\"{_pluralize(name)}/\", {name}Controller.as_view()),[/cyan]")


def make_request(
    name: str = typer.Argument(..., help="Request class name, e.g. StorePostRequest."),
    domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
) -> None:
    """Create an Http/Requests/<Name>.py validation class."""
    _bootstrap_django()
    app_dir = _src_app_dir(_project_root())
    target = app_dir / "Http" / "Requests" / f"{name}.py"

    _ensure_not_exists(target)
    _render_template(_tpl_path("request"), target, request_name=name, domain=domain)

    console.print(f"[green]Created[/green] {target.relative_to(_project_root())}")


def make_resource(
    name: str = typer.Argument(..., help="Model name, e.g. Post."),
    domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
) -> None:
    """Create an Http/Resources/<Name>Resource.py output serializer."""
    _bootstrap_django()
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

    console.print(f"[green]Created[/green] {target.relative_to(_project_root())}")


def make_policy(
    name: str = typer.Argument(..., help="Model name, e.g. Post."),
    domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
) -> None:
    """Create a Domain/<Domain>/Policies/<Name>Policy.py."""
    _bootstrap_django()
    app_dir = _src_app_dir(_project_root())
    target = app_dir / "Domain" / domain / "Policies" / f"{name}Policy.py"

    _ensure_not_exists(target)
    _render_template(_tpl_path("policy"), target, policy_name=f"{name}Policy", domain=domain)

    console.print(f"[green]Created[/green] {target.relative_to(_project_root())}")


def make_admin(
    name: str = typer.Argument(None, help="Model name to generate an Admin class for."),
    domain: str = typer.Option("", "--domain", "-d", help="PascalCase domain folder under Domain/."),
    email: str = typer.Option(None, "--email", "-e", help="Admin/superuser email."),
    password: str = typer.Option(None, "--password", "-p", help="Admin/superuser password."),
) -> None:
    """Generate an Admin class for a model, or create a superuser.

    Given a NAME, writes an Admin/<Name>Admin.py registration file. Without a
    NAME, falls back to superuser creation (interactive, or flag-based with
    ``--email``/``--password``).
    """
    if name:
        _make_admin_file(name, domain)
        return
    _make_superuser(email, password)


def _make_admin_file(name: str, domain: str) -> None:
    if not domain:
        console.print("[red]--domain is required when generating an Admin class.[/red]")
        raise typer.Exit(1)
    _bootstrap_django()
    app_dir = _src_app_dir(_project_root())
    target = app_dir / "Admin" / f"{name}Admin.py"

    _ensure_not_exists(target)
    _render_template(_tpl_path("admin"), target, model_name=name, domain=domain)

    console.print(f"[green]Created[/green] {target.relative_to(_project_root())}")


def _make_superuser(email: str | None, password: str | None) -> None:
    _bootstrap_django()
    from django.core.management import call_command

    if email and not password:
        console.print("[red]--password is required when --email is given.[/red]")
        raise typer.Exit(1)

    if email and password:
        os.environ.setdefault("DJANGO_SUPERUSER_PASSWORD", password)
        call_command("createsuperuser", email=email, interactive=False)
        console.print(f"[green]Superuser created[/green] {email}")
        return

    call_command("createsuperuser", interactive=True)


MAKE_COMMANDS = [
    ("make:model", make_model),
    ("make:controller", make_controller),
    ("make:request", make_request),
    ("make:resource", make_resource),
    ("make:policy", make_policy),
    ("make:admin", make_admin),
]