"""yello CLI — assembly point.

One Typer app exposing all Artisan-style verbs. Nothing here touches Django at
import time; Django is bootstrapped lazily per-command via `_bootstrap_django`.
"""

import typer

from yello.cli import about, db, init, key, make, migrate, model, route, serve

app = typer.Typer(
    name="yello",
    help="Artisan-style CLI for Laravel-style Django projects.",
    no_args_is_help=True,
    add_completion=False,
)

for name, callback in make.MAKE_COMMANDS:
    app.command(name=name)(callback)

for name, callback in migrate.MIGRATE_COMMANDS:
    app.command(name=name)(callback)

for name, callback in db.DB_COMMANDS:
    app.command(name=name)(callback)

app.command(name="about")(about.AboutCommand().handle)
app.command(name="key:generate")(key.KeyGenerateCommand().handle)
app.command(name="model:show")(model.ModelShowCommand().handle)
app.command(name="route:list")(route.RouteListCommand().handle)
app.command(name="serve")(serve.ServeCommand().handle)
app.command(name="dev")(serve.ServeCommand().handle)
app.command(name="init")(init.InitCommand().handle)


if __name__ == "__main__":
    app()