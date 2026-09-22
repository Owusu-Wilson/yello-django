"""yello tinker — an interactive shell with the project's models preloaded."""

import code

from yello.console.command import Command


class TinkerCommand(Command):
    """Start an interactive Python shell with every model preloaded."""

    def handle(self) -> None:
        self.bootstrap()
        import django
        from django.apps import apps

        namespace = {"django": django}
        for model in apps.get_models():
            namespace[model.__name__] = model

        self.info(f"Preloaded {len(apps.get_models())} model(s). Ctrl-D to exit.")
        code.InteractiveConsole(namespace).interact(banner="", exitmsg="")
