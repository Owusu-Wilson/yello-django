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
