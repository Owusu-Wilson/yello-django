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
            from yello.cli.db import run_seed

            run_seed()


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
            from yello.cli.db import run_seed

            run_seed()


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
    ("migrate", MigrateCommand().handle),
    ("migrate:fresh", MigrateFreshCommand().handle),
    ("migrate:rollback", MigrateRollbackCommand().handle),
    ("migrate:status", MigrateStatusCommand().handle),
]
