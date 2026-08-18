"""yello dev — run the Django development server."""

import typer

from yello.cli._helpers import _bootstrap_django


def dev(
    port: str = typer.Option("8000", "--port", "-p", help="Port to bind."),
) -> None:
    """Run the Django development server."""
    _bootstrap_django()
    from django.core.management import call_command

    call_command("runserver", port, use_reloader=True)
