"""yello make:* — scaffold files into the Laravel-style domain layout."""

import os
from pathlib import Path

import typer

from yello.cli._helpers import (
    _ensure_not_exists,
    _project_root,
    _render_simple_template,
    _render_template,
    _src_app_dir,
)
from yello.codegen.aggregator import add_model_import
from yello.console.command import Command


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


class MakeTestCommand(Command):
    """Create a tests/<Name>.py test case."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Test class name, e.g. PostTest."),
    ) -> None:
        target = _project_root() / "tests" / f"{name}.py"

        _ensure_not_exists(target)
        _render_simple_template(_tpl_path("test"), target, class_name=name)

        self.info(f"Created {target.relative_to(_project_root())}")


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
        _render_simple_template(_tpl_path("enum"), target, class_name=name)

        self.info(f"Created {target.relative_to(_project_root())}")


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
        _render_simple_template(_tpl_path("exception"), target, class_name=name)

        self.info(f"Created {target.relative_to(_project_root())}")


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
        _render_simple_template(_tpl_path("rule"), target, class_name=name)

        self.info(f"Created {target.relative_to(_project_root())}")


MAKE_COMMANDS = [
    ("make:model", MakeModelCommand().handle),
    ("make:controller", MakeControllerCommand().handle),
    ("make:request", MakeRequestCommand().handle),
    ("make:resource", MakeResourceCommand().handle),
    ("make:policy", MakePolicyCommand().handle),
    ("make:admin", MakeAdminCommand().handle),
    ("make:migration", MakeMigrationCommand().handle),
    ("make:seeder", MakeSeederCommand().handle),
    ("make:factory", MakeFactoryCommand().handle),
    ("make:test", MakeTestCommand().handle),
    ("make:enum", MakeEnumCommand().handle),
    ("make:exception", MakeExceptionCommand().handle),
    ("make:rule", MakeRuleCommand().handle),
]
