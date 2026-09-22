# Artisan CLI Parity — Design

## Goal

Rework the `yello` CLI so its command surface and internal structure genuinely
mirror Laravel's `php artisan`: matching command names/namespaces where a
Django equivalent exists, and an OOP `Command` class per command (mirroring
`Illuminate\Console\Command`) instead of bare functions.

Explicitly out of scope (no Django equivalent without inventing fake
infrastructure): `queue:*`, `schedule:*`, `event:*`, `notifications:*`,
`session:table`, `channel:*`/broadcasting, and anything from optional Laravel
packages (Horizon, Telescope, Nova, Livewire, Jetstream, Fortify, Breeze,
Cashier, Sanctum, Octane, Reverb, Passport, Scout, Dusk, Folio, Volt, Inertia,
Vapor, Sail, Spark, Pennant, Boost).

## Foundation: OOP `Command` base class

New module `src/yello/console/command.py`:

```python
class Command:
    """Base for all yello console commands, mirroring Artisan's Command."""

    def bootstrap(self) -> None:
        from yello.cli._helpers import _bootstrap_django
        _bootstrap_django()

    def info(self, message: str) -> None: ...   # green
    def warn(self, message: str) -> None: ...    # yellow
    def error(self, message: str) -> None: ...   # red
    def line(self, message: str) -> None: ...    # plain
    def confirm(self, question: str, default: bool = False) -> bool: ...
    def fail(self, message: str) -> NoReturn: ...  # error() then typer.Exit(1)

    def handle(self, *args, **kwargs) -> None:
        raise NotImplementedError
```

Each command becomes `class XCommand(Command)` with a `handle()` method
carrying the same `typer.Argument`/`typer.Option` defaults used today.
Registration keeps the existing `(name, target)` tuple-list pattern already
used in `make.py`/`cli/__init__.py`, but registers `cls().handle` (a bound
method — Typer's signature introspection drops `self` automatically, so this
requires no changes to how Typer parses arguments).

`console.py` also keeps the module-level `console = Console()` (moved from
`_helpers.py`, re-exported there for compatibility) since `Command` methods
need it.

### `.env` loading (prerequisite for Phase 3's `key:generate`)

`_bootstrap_django()` in `_helpers.py` gains a `_load_dotenv(project_root)`
step (manual parse, same style as the existing `.yello` file parser — no new
dependency) that sets any `KEY=value` line from a `.env` file into
`os.environ` *if not already set*, before Django settings are read. Without
this, `key:generate` would write a file nothing ever reads.

## Phase 0 — Migrate namespace flatten

`src/yello/cli/migrate.py` stops being a Typer sub-app. It becomes four
`Command` classes registered as flat top-level commands:

| Old | New |
|---|---|
| `migrate run` | `migrate` (bare) |
| `migrate fresh` | `migrate:fresh` |
| `migrate rollback` | `migrate:rollback` |
| `migrate status` | `migrate:status` |
| `migrate make` | `make:migration` (moves to `make.py`, matches real Artisan namespace) |

- `MigrateCommand.handle(seed: bool = Option(False, "--seed"))` — runs
  `migrate`, then `run_seed()` if `--seed`.
- `MigrateFreshCommand.handle(seed: bool, yes: bool)` — same as today's
  `migrate fresh` plus `--seed`.
- `MigrateRollbackCommand`, `MigrateStatusCommand` — same behavior, new name.
- `MakeMigrationCommand` in `make.py`'s `MAKE_COMMANDS` — same behavior as the
  old `migrate make`.

## Phase 1 — Database namespace

New `src/yello/db/seeder.py`:

```python
class Seeder:
    def run(self) -> None:
        raise NotImplementedError

    def call(self, *seeder_classes: type["Seeder"]) -> None:
        for cls in seeder_classes:
            cls().run()
```

New template `templates/seeder/seeder_name.py-tpl` → generated into
`src/app/Database/Seeders/<Name>.py` (mirrors Artisan's `database/seeders/`).

New `src/yello/cli/db.py`:

- `run_seed(seeder_class: str = "DatabaseSeeder") -> None` — module-level
  helper (not a Command method) that imports
  `app.Database.Seeders.<seeder_class>` and calls `.run()`. This is what
  `migrate`/`migrate:fresh` import — migrate.py never knows how seeding
  works, only that this function exists (keeps seeding decoupled from
  migration, per earlier direction).
- `DbSeedCommand` → `db:seed [--class/-c]` (default `DatabaseSeeder`), calls
  `run_seed(cls)`.
- `DbWipeCommand` → `db:wipe [--yes/-y]`. Drops every table Django knows about
  (`connection.introspection.table_names()`) via the schema editor, including
  `django_migrations`, so a subsequent `migrate` starts from zero. Confirms
  unless `--yes`.
- `DbTableCommand` → `db:table <name>`. Uses
  `connection.introspection.get_table_description()` to print a column/type
  table via `rich.table.Table`.
- `DbShowCommand` → `db:show`. Prints engine, database name/path, and every
  table with its row count.

`make.py` gains `MakeSeederCommand` → `make:seeder <Name>` →
`src/app/Database/Seeders/<Name>.py`.

## Phase 2 — Make namespace expansion

Each follows the exact same shape already used by `Policy`/`Controller`: a
base class in its own module, a `.py-tpl` template, a `Make<X>Command`, and an
entry in `MAKE_COMMANDS`.

| Command | Base class | Output path |
|---|---|---|
| `make:factory` | `yello/db/factory.py::Factory` (`model`, `definition()`, `make()`, `create()`) | `src/app/Database/Factories/<Name>Factory.py` |
| `make:test` | none (subclasses Django's `TestCase` directly, same as Django itself) | `tests/<Name>Test.py` (project root `tests/`, created if missing) |
| `make:enum` | none (subclasses stdlib `enum.Enum`) | `src/app/Enums/<Name>.py` |
| `make:exception` | `yello/exceptions/base.py::YelloException(Exception)` | `src/app/Exceptions/<Name>.py` |
| `make:rule` | `yello/validation/rule.py::Rule` (`message`, `passes(value)`, `__call__` raises DRF `ValidationError`) | `src/app/Rules/<Name>.py` |
| `make:mail` | `yello/mail/mailable.py::Mailable` (`subject`, `build()`, `send(to)` via `django.core.mail.send_mail`) | `src/app/Mail/<Name>.py` |
| `make:middleware` | `yello/http/middleware.py::Middleware` (`before(request)`, `after(request, response)`, `__call__` implements the Django middleware protocol) | `src/app/Http/Middleware/<Name>.py` |

All follow the existing `--domain` convention only where the existing
Domain-scoped commands do (factory pairs with a model, so it takes
`--domain` like `make:model`); the rest (`test`, `enum`, `exception`, `rule`,
`mail`, `middleware`) are app-wide like `make:admin`, so no `--domain`.

## Phase 3 — Introspection & environment

- `ModelShowCommand` → `model:show <Name> [--domain]` — new
  `src/yello/cli/model.py`. Locates the model class, prints fields (name,
  type, null/blank, default) and relations via a `rich.table.Table`.
- `AboutCommand` → `about` — new `src/yello/cli/about.py`. Prints yello
  version (`yello.__about__.__version__`), Python version, Django version,
  settings module, DB engine, `DEBUG`, and installed app count. Bootstraps
  Django defensively (catches and reports if no project is found, rather than
  crashing) since `about` should work as a diagnostic even in a broken
  project.
- `KeyGenerateCommand` → `key:generate [--show]` — new
  `src/yello/cli/key.py`. Generates a key via
  `django.core.management.utils.get_random_secret_key()`, writes/replaces the
  `DJANGO_SECRET_KEY=` line in the project's `.env` (created if missing,
  preserving other lines). `--show` prints the key without writing (mirrors
  Artisan's `key:generate --show`).

## Phase 4 — REPL & dev ergonomics

- `TinkerCommand` → `tinker` — new `src/yello/cli/tinker.py`. Bootstraps
  Django, builds a namespace dict pre-populated with every installed model
  (via `django.apps.apps.get_models()`, keyed by class name) plus `django`
  itself, then starts `code.InteractiveConsole(namespace).interact()`. No new
  dependency (no IPython requirement) — matches Tinker's zero-config feel
  without a heavier REPL dependency.
- `dev` is renamed to `ServeCommand` internally and registered under **both**
  `serve` (the real Artisan name, becomes the documented one) and `dev`
  (kept for backward compatibility, since existing scaffolded projects and
  docs already say `yello dev`). Same `--port` option.

## Phase 5 — Maintenance mode

- New `src/yello/http/maintenance.py::MaintenanceModeMiddleware` — Django
  middleware; if `storage/framework/maintenance.json` exists at the project
  root, returns a 503 with the stored message (and `Retry-After` if a retry
  value was stored); otherwise passes through.
- `DownCommand` → `down [--message] [--retry]` — new `src/yello/cli/maintenance.py`.
  Writes `storage/framework/maintenance.json` (`{"message": ..., "retry": ...}`),
  creating `storage/framework/` if missing.
- `UpCommand` → `up` — deletes the lock file if present, else prints
  "Application is already up."
- `init`'s project template gains `MaintenanceModeMiddleware` as the first
  entry in `MIDDLEWARE` (in both `templates/project/config/settings.py` and
  `settings/base.py`, so it applies to both scaffolded and yello-authored
  projects) and `storage/framework/.gitkeep` so the directory exists from
  scaffold time.

## Testing strategy

- Unit tests for each new base class (`Seeder.call`, `Factory.make/create`,
  `Rule.__call__`, `Mailable.send`, `Middleware.__call__`) using Django's test
  models already present in `tests/models.py` where relevant.
- CLI smoke tests (extend `tests/test_cli.py`) for every renamed/new command:
  help text lists all new names, and the `TestProjectFlow` acceptance flow
  exercises `migrate:fresh --seed`, `db:seed`, `db:wipe`, `db:table`,
  `db:show`, `make:seeder`/`make:factory`/`make:test`/`make:enum`/
  `make:exception`/`make:rule`/`make:mail`/`make:middleware`, `model:show`,
  `about`, `key:generate`, `tinker` (non-interactively, feeding EOF), `serve`
  alias existing, `down`/`up`.
- `tests/test_detect.py` (already exists, untracked) stays as-is — unrelated
  to this work, not touched.

## File layout summary (new files)

```
src/yello/console/command.py
src/yello/db/seeder.py
src/yello/db/factory.py
src/yello/exceptions/base.py
src/yello/validation/rule.py
src/yello/mail/mailable.py
src/yello/http/middleware.py
src/yello/http/maintenance.py
src/yello/cli/db.py
src/yello/cli/model.py
src/yello/cli/about.py
src/yello/cli/key.py
src/yello/cli/tinker.py
src/yello/cli/maintenance.py
src/yello/templates/seeder/seeder_name.py-tpl
src/yello/templates/factory/factory_name.py-tpl
src/yello/templates/test/test_name.py-tpl
src/yello/templates/enum/enum_name.py-tpl
src/yello/templates/exception/exception_name.py-tpl
src/yello/templates/rule/rule_name.py-tpl
src/yello/templates/mail/mail_name.py-tpl
src/yello/templates/middleware/middleware_name.py-tpl
```

Modified: `cli/__init__.py`, `cli/_helpers.py`, `cli/make.py`, `cli/migrate.py`
(rewritten), `cli/dev.py` (renamed to `serve.py`, aliased), `settings/base.py`,
`templates/project/config/settings.py`, `tests/test_cli.py`, `tests/test_init.py`.
