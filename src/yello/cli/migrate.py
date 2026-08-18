"""yello migrate — database migration shortcuts."""

import typer

from yello.cli._helpers import _bootstrap_django, console

migrate_app = typer.Typer(
    name="migrate",
    help="Run database migrations.",
    no_args_is_help=True,
)


@migrate_app.command("make")
def migrate_make(
    app: str = typer.Option(None, "--app", "-a", help="Limit to an app label."),
    empty: bool = typer.Option(False, "--empty", help="Create an empty migration."),
) -> None:
    """Create new migration(s) via ``makemigrations``."""
    _bootstrap_django()
    from django.core.management import call_command

    args = ()
    if app:
        args = (app,)
    call_command("makemigrations", *args, empty=empty, interactive=False)


@migrate_app.command("run")
def migrate_run(
    app: str = typer.Argument(None, help="App label to migrate (optional)."),
    migration: str = typer.Argument(None, help="Migration name to apply (optional)."),
) -> None:
    """Apply migrations via ``migrate``."""
    _bootstrap_django()
    from django.core.management import call_command

    args = ()
    if app:
        args = (app,)
    if migration:
        args = args + (migration,)
    call_command("migrate", *args, interactive=False)


@migrate_app.command("rollback")
def migrate_rollback(
    app: str = typer.Argument(..., help="App label to roll back."),
    migration: str = typer.Argument("zero", help="Migration name to roll back to (default: zero)."),
) -> None:
    """Roll a migration back via ``migrate <app> <migration>``."""
    _bootstrap_django()
    from django.core.management import call_command

    call_command("migrate", app, migration, interactive=False)


@migrate_app.command("status")
def migrate_status() -> None:
    """Show migration status via ``showmigrations``."""
    _bootstrap_django()
    from django.core.management import call_command

    call_command("showmigrations", verbosity=2)


@migrate_app.command("fresh")
def migrate_fresh(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Flush the database and re-run every migration."""
    _bootstrap_django()
    from django.core.management import call_command

    if not yes:
        if not typer.confirm("This will flush all data and re-run every migration. Continue?"):
            raise typer.Abort()

    call_command("flush", interactive=False)
    call_command("migrate", interactive=False)