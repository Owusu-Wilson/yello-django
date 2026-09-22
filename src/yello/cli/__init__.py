"""yello CLI — assembly point.

One Typer app exposing all Artisan-style verbs. Nothing here touches Django at
import time; Django is bootstrapped lazily per-command via `_bootstrap_django`.
"""

import typer

from yello.cli import init, make, migrate, route, serve

app = typer.Typer(
    name="yello",
    help="Artisan-style CLI for Laravel-style Django projects.",
    no_args_is_help=True,
    add_completion=False,
)

for name, callback in make.MAKE_COMMANDS:
    app.command(name=name)(callback)

app.command(name="route:list")(route.RouteListCommand().handle)
app.command(name="serve")(serve.ServeCommand().handle)
app.command(name="dev")(serve.ServeCommand().handle)
app.command(name="init")(init.init)

app.add_typer(migrate.migrate_app)


if __name__ == "__main__":
    app()