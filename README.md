# yello-core

Artisan-style CLI + base classes for organizing a Django project into a
Laravel-style domain layout. Yello is a **CLI + base classes + code generator**:
it arranges and scaffolds Django/DRF code into domain folders — it does **not**
add a second abstraction layer over Django.

## Install

```bash
pip install -e /path/to/yello-core        # editable, local
pip install "yello-core @ git+https://github.com/you/yello-core"  # git URL
```

## What it provides

- A global `yello` CLI: `make:model`, `make:controller`, `make:request`,
  `make:resource`, `make:policy`, `make:admin`, `migrate`, `route:list`, `dev`.
- Base classes: `BaseModel`, `Controller`, `Request`, `Resource`, `Policy`, and
  a custom `User` model (`yello.auth`).

## CLI reference

| Command | Generates / does |
|---|---|
| `yello init [name] [--manager pip\|pipenv] [--no-install]` | scaffolds a fresh project (config/, src/app/, manage.py, Pipfile) and installs dependencies |
| `yello make:model <Name> --domain <Domain>` | `src/app/Domain/<Domain>/Models/<Name>.py` + appends the import to `src/app/models.py` |
| `yello make:controller <Name> --domain <Domain>` | `src/app/Http/Controllers/<Name>Controller.py` + prints the route snippet |
| `yello make:request <Name> --domain <Domain>` | `src/app/Http/Requests/<Name>.py` |
| `yello make:resource <Name> --domain <Domain>` | `src/app/Http/Resources/<Name>Resource.py` |
| `yello make:policy <Name> --domain <Domain>` | `src/app/Domain/<Domain>/Policies/<Name>Policy.py` |
| `yello make:admin [Name] --domain <Domain>` | `src/app/Admin/<Name>Admin.py` (with a Name), or superuser creation (`--email`/`--password`, or interactive) |
| `yello migrate make [--app X] [--empty]` | `makemigrations` (applies to the *project's* settings module) |
| `yello migrate run [app] [migration]` | `migrate` |
| `yello migrate rollback <app> [migration=zero]` | `migrate <app> <migration>` |
| `yello migrate status` | `showmigrations` |
| `yello migrate fresh [--yes]` | flush + migrate, with confirmation |
| `yello route:list` | lists every registered URL |
| `yello dev [--port]` | `runserver` |

Every command that touches Django bootstraps it lazily against the consuming
project via `DJANGO_SETTINGS_MODULE` — nothing is imported at module load time.

## The one-app domain layout

Register exactly one app named `app`, then let the generators organize files
under it:

```
src/app/
├── apps.py
├── models.py                # auto-maintained import aggregator
├── migrations/
├── Domain/
│   ├── Posts/Models/Post.py
│   └── Posts/Policies/PostPolicy.py
└── Http/
    ├── Controllers/PostController.py
    ├── Requests/StorePostRequest.py
    └── Resources/PostResource.py
```

`src/app/models.py` is the single hand-untouched file that makes this legal
Django. `yello make:model` appends the required import to it automatically:

```python
# app/models.py — auto-maintained by `yello make:model`, safe to commit
from app.Domain.Posts.Models.Post import Post
```

## Quickstart in a new project

```bash
pip install yello-core
yello init myapp                      # scaffolds config/, src/app/, manage.py, Pipfile
cd myapp
pipenv install                        # or: pip install django djangorestframework
export DJANGO_SETTINGS_MODULE=config.settings
yello migrate run
yello make:model Post --domain Posts
yello migrate make && yello migrate run
yello make:admin --email you@example.com --password <strong-password>
yello dev
```

`yello init` creates the full single-app layout. Pass `--manager pip` /
`--manager pipenv` to choose the package manager, `--no-install` to scaffold
only, and `--force` to overwrite an existing directory.

## Quickstart in a throwaway project

```bash
pip install -e /path/to/yello-core
DJANGO_SETTINGS_MODULE=config.settings yello make:model Post --domain Posts
DJANGO_SETTINGS_MODULE=config.settings yello migrate make
DJANGO_SETTINGS_MODULE=config.settings yello migrate run
```

`AUTH_USER_MODEL = "yello_auth.User"` and `yello.auth` in `INSTALLED_APPS`
opt you into the custom email-first user model.

## Development

```bash
pipenv install --dev
pipenv run pytest
```
