"""yello CLI — assembly point.

One Typer app exposing all Artisan-style verbs. Nothing here touches Django at
import time; Django is bootstrapped lazily per-command via `_bootstrap_django`.
"""

import typer

from yello.cli import dev, make, migrate, route

app = typer.Typer(
    name="yello",
    help="Artisan-style CLI for Laravel-style Django projects.",
    no_args_is_help=True,
    add_completion=False,
)

for name, callback in make.MAKE_COMMANDS:
    app.command(name=name)(callback)

app.command(name="route:list")(route.route_list)
app.command(name="dev")(dev.dev)

app.add_typer(migrate.migrate_app)


if __name__ == "__main__":
    app()