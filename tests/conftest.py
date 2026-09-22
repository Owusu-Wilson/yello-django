import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.management import call_command

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Run migrate with --run-syncdb so apps without migrations (tests) get
    their tables created too."""
    with django_db_blocker.unblock():
        call_command("migrate", run_syncdb=True, interactive=False, verbosity=0)
    yield


# --- Throwaway project used by the CLI acceptance tests ---------------------

_SETTINGS = """\
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "django-insecure-test"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "app",
    "yello.auth",
]

AUTH_USER_MODEL = "yello_auth.User"
ROOT_URLCONF = "config.urls"
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
STATIC_URL = "static/"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]
"""

_URLS = """\
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
"""

_APP_APPS = """\
from django.apps import AppConfig


class AppConfig(AppConfig):
    name = "app"
"""

PROJECT_FILES = {
    "config/__init__.py": "",
    "config/settings.py": _SETTINGS,
    "config/urls.py": _URLS,
    "src/app/__init__.py": "",
    "src/app/apps.py": _APP_APPS,
    "src/app/migrations/__init__.py": "",
}


@pytest.fixture
def project_dir(tmp_path):
    base = tmp_path / "project"
    for rel, content in PROJECT_FILES.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return base


@pytest.fixture
def run_cli(project_dir):
    """Run the real `yello` CLI (via `python -m yello`) in a subprocess,
    pointed at the throwaway project's own settings module."""

    def _run(*args, env_extra=None, input=None):
        env = dict(os.environ)
        # Never leak this dev repo's own PYTHONPATH into the scaffolded
        # project's subprocess — its "tests" package collides with the
        # throwaway project's own tests/ directory otherwise.
        env.pop("PYTHONPATH", None)
        env["DJANGO_SETTINGS_MODULE"] = "config.settings"
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            [sys.executable, "-m", "yello", *args],
            cwd=str(project_dir),
            env=env,
            capture_output=True,
            text=True,
            input=input,
        )

    return _run
