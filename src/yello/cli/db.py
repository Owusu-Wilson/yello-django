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


DB_COMMANDS = [
    ("db:seed", DbSeedCommand().handle),
    ("db:wipe", DbWipeCommand().handle),
    ("db:table", DbTableCommand().handle),
    ("db:show", DbShowCommand().handle),
]
