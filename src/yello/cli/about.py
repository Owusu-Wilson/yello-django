"""yello about — environment and project diagnostics."""

import sys

from yello.__about__ import __version__
from yello.console.command import Command


class AboutCommand(Command):
    """Show yello, Python, and Django environment information."""

    def handle(self) -> None:
        self.line(f"yello:    {__version__}")
        self.line(f"Python:   {sys.version.split()[0]}")

        try:
            self.bootstrap()
        except Exception as exc:  # no project / bad settings — still report what we can
            self.warn(f"Django:   could not bootstrap ({exc})")
            return

        import django
        from django.conf import settings

        self.line(f"Django:   {django.get_version()}")
        self.line(f"Settings: {settings.SETTINGS_MODULE}")
        self.line(f"Database: {settings.DATABASES['default']['ENGINE']}")
        self.line(f"Debug:    {settings.DEBUG}")
        self.line(f"Apps:     {len(settings.INSTALLED_APPS)} installed")
