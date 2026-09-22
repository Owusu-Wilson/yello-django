"""yello CLI — assembly point.

One Typer app exposing all Artisan-style verbs. Nothing here touches Django at
import time; Django is bootstrapped lazily per-command via `_bootstrap_django`.
"""

import typer

from yello.cli import about, db, init, key, maintenance, make, migrate, model, route, serve, tinker

app = typer.Typer(
    name="yello",
    help="Artisan-style CLI for Laravel-style Django projects.",
    no_args_is_help=True,
    add_completion=False,
)


def _register(name: str, callback) -> None:
    """Register a bound ``Command.handle`` method, using its class's
    docstring as the command's help text (Typer reads ``callback.__doc__``,
    which is empty on a bound method whose docstring lives on the class)."""
    app.command(name=name, help=callback.__self__.__doc__)(callback)


for name, callback in make.MAKE_COMMANDS:
    _register(name, callback)

for name, callback in migrate.MIGRATE_COMMANDS:
    _register(name, callback)

for name, callback in db.DB_COMMANDS:
    _register(name, callback)

_register("about", about.AboutCommand().handle)
_register("key:generate", key.KeyGenerateCommand().handle)
_register("tinker", tinker.TinkerCommand().handle)
_register("down", maintenance.DownCommand().handle)
_register("up", maintenance.UpCommand().handle)
_register("model:show", model.ModelShowCommand().handle)
_register("route:list", route.RouteListCommand().handle)
_register("serve", serve.ServeCommand().handle)
_register("dev", serve.ServeCommand().handle)
_register("init", init.InitCommand().handle)


if __name__ == "__main__":
    app()
