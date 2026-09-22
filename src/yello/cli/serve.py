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
