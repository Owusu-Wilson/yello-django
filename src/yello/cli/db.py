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
    ("db:seed", DbSeedCommand().handle),
]
