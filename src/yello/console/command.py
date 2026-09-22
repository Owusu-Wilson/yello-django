"""Base class for all yello console commands, mirroring Artisan's Command."""

from typing import NoReturn

import typer
from rich.console import Console

console = Console()


class Command:
    """Subclass this and implement ``handle()`` for every CLI command."""

    def bootstrap(self) -> None:
        from yello.cli._helpers import _bootstrap_django

        _bootstrap_django()

    def info(self, message: str) -> None:
        console.print(f"[green]{message}[/green]")

    def warn(self, message: str) -> None:
        console.print(f"[yellow]{message}[/yellow]")

    def error(self, message: str) -> None:
        console.print(f"[red]{message}[/red]")

    def line(self, message: str) -> None:
        console.print(message)

    def confirm(self, question: str, default: bool = False) -> bool:
        return typer.confirm(question, default=default)

    def fail(self, message: str) -> NoReturn:
        self.error(message)
        raise typer.Exit(1)

    def handle(self, *args, **kwargs) -> None:
        raise NotImplementedError
