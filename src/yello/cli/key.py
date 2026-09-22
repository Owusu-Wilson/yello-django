"""yello key:generate — generate/rotate the Django secret key."""

import typer

from yello.cli._helpers import _project_root
from yello.console.command import Command


class KeyGenerateCommand(Command):
    """Generate a new Django secret key into .env."""

    def handle(
        self,
        show: bool = typer.Option(False, "--show", help="Print the key without writing it."),
    ) -> None:
        from django.core.management.utils import get_random_secret_key

        key = get_random_secret_key()

        if show:
            self.line(key)
            return

        env_path = _project_root() / ".env"
        lines = env_path.read_text().splitlines() if env_path.exists() else []
        lines = [line for line in lines if not line.startswith("DJANGO_SECRET_KEY=")]
        lines.append(f"DJANGO_SECRET_KEY={key}")
        env_path.write_text("\n".join(lines) + "\n")

        self.info(f"Application key set in {env_path.name}")
