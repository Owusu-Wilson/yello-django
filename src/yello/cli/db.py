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


DB_COMMANDS = [
    ("db:seed", DbSeedCommand().handle),
    ("db:wipe", DbWipeCommand().handle),
]
