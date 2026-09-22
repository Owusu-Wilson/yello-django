import os
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from yello.cli import app

runner = CliRunner()


def _run_in(*args, cwd, env_extra=None):
    """Run `python -m yello` in a subprocess from an arbitrary directory."""
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "yello", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


class TestCliSmoke:
    def test_help_lists_all_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for name in (
            "make:model",
            "make:controller",
            "make:request",
            "make:resource",
            "make:policy",
            "make:admin",
            "make:migration",
            "route:list",
            "serve",
            "dev",
            "init",
            "migrate",
            "migrate:fresh",
            "migrate:rollback",
            "migrate:status",
        ):
            assert name in result.output

    @pytest.mark.django_db
    def test_migrate_status(self):
        result = runner.invoke(app, ["migrate:status"])
        assert result.exit_code == 0, result.output
        assert "0001_initial" in result.output

    def test_settings_module_autodetected_without_env_var(self, project_dir):
        """The real-user case: run `yello migrate:status` from a project root
        with no DJANGO_SETTINGS_MODULE set, and let detection find it."""
        env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
        r = subprocess.run(
            [sys.executable, "-m", "yello", "migrate:status"],
            cwd=str(project_dir),
            env=env,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "0001_initial" in r.stdout

    def test_route_list(self):
        result = runner.invoke(app, ["route:list"])
        assert result.exit_code == 0, result.output
        assert "admin/" in result.output


class TestProjectFlow:
    """End-to-end acceptance flow against a throwaway project, in subprocesses
    so each command gets a fresh Django configuration against the project's
    own settings module (exactly how a real user runs it)."""

    def test_make_model_then_migrations(self, project_dir, run_cli):
        r = run_cli("make:model", "Post", "--domain", "Posts")
        assert r.returncode == 0, r.stderr

        model_file = project_dir / "src/app/Domain/Posts/Models/Post.py"
        assert model_file.exists()
        assert "class Post(BaseModel):" in model_file.read_text()

        models_file = project_dir / "src/app/models.py"
        assert "from app.Domain.Posts.Models.Post import Post" in models_file.read_text()

        r = run_cli("make:migration")
        assert r.returncode == 0, r.stderr
        assert (project_dir / "src/app/migrations/0001_initial.py").exists()

        r = run_cli("migrate")
        assert r.returncode == 0, r.stderr
        assert (project_dir / "db.sqlite3").exists()

        r = run_cli("migrate:status")
        assert r.returncode == 0, r.stderr
        assert "0001_initial" in r.stdout

    def test_make_model_twice_refuses_to_overwrite(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        r = run_cli("make:model", "Post", "--domain", "Posts")
        assert r.returncode == 1
        assert "Refusing to overwrite" in r.stdout

    def test_other_generators_write_expected_paths(self, project_dir, run_cli):
        cases = [
            (
                ("make:controller", "Post", "--domain", "Posts"),
                "src/app/Http/Controllers/PostController.py",
                "class PostController(Controller):",
            ),
            (
                ("make:request", "StorePostRequest", "--domain", "Posts"),
                "src/app/Http/Requests/StorePostRequest.py",
                "class StorePostRequest(Request):",
            ),
            (
                ("make:resource", "Post", "--domain", "Posts"),
                "src/app/Http/Resources/PostResource.py",
                "class PostResource(Resource):",
            ),
            (
                ("make:policy", "Post", "--domain", "Posts"),
                "src/app/Domain/Posts/Policies/PostPolicy.py",
                "class PostPolicy(Policy):",
            ),
        ]
        for args, rel_path, marker in cases:
            r = run_cli(*args)
            assert r.returncode == 0, (args, r.stderr)
            target = project_dir / rel_path
            assert target.exists(), rel_path
            assert marker in target.read_text()

    def test_make_admin_superuser(self, project_dir, run_cli):
        r = run_cli("migrate")
        assert r.returncode == 0, r.stderr

        r = run_cli("make:admin", "--email", "admin@example.com", "--password", "verysecret123")
        assert r.returncode == 0, r.stderr
        assert "Superuser created" in r.stdout

    def test_route_list_in_project(self, project_dir, run_cli):
        r = run_cli("route:list")
        assert r.returncode == 0, r.stderr
        assert "admin/" in r.stdout

    def test_migrate_rollback(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("make:migration").returncode == 0
        assert run_cli("migrate").returncode == 0

        r = run_cli("migrate:rollback", "app")
        assert r.returncode == 0, r.stderr
        assert "app.0001_initial" in r.stdout

        r = run_cli("migrate:status")
        assert "app.0001_initial" not in r.stdout

    def test_migrate_fresh(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("make:migration").returncode == 0
        assert run_cli("migrate").returncode == 0

        r = run_cli("migrate:fresh", "--yes")
        assert r.returncode == 0, r.stderr

    def test_make_seeder(self, project_dir, run_cli):
        r = run_cli("make:seeder", "PostSeeder")
        assert r.returncode == 0, r.stderr
        target = project_dir / "src/app/Database/Seeders/PostSeeder.py"
        assert target.exists()
        assert "class PostSeeder(Seeder):" in target.read_text()

    def test_db_seed(self, project_dir, run_cli):
        seeders_dir = project_dir / "src/app/Database/Seeders"
        seeders_dir.mkdir(parents=True)
        (seeders_dir / "__init__.py").write_text("")
        (seeders_dir / "DatabaseSeeder.py").write_text(
            "from yello.db.seeder import Seeder\n\n\n"
            "class DatabaseSeeder(Seeder):\n"
            "    def run(self) -> None:\n"
            "        print('seeded!')\n"
        )
        r = run_cli("db:seed")
        assert r.returncode == 0, r.stderr
        assert "seeded!" in r.stdout

    def test_db_wipe(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("make:migration").returncode == 0
        assert run_cli("migrate").returncode == 0

        r = run_cli("db:wipe", "--yes")
        assert r.returncode == 0, r.stderr

        r = run_cli("migrate:status")
        assert "app.0001_initial" not in r.stdout

    def test_db_table(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("make:migration").returncode == 0
        assert run_cli("migrate").returncode == 0

        r = run_cli("db:table", "app_post")
        assert r.returncode == 0, r.stderr
        assert "id" in r.stdout

    def test_db_show(self, project_dir, run_cli):
        assert run_cli("migrate").returncode == 0
        r = run_cli("db:show")
        assert r.returncode == 0, r.stderr
        assert "sqlite" in r.stdout.lower()

    def test_migrate_seed_flag_runs_seeder(self, project_dir, run_cli):
        seeders_dir = project_dir / "src/app/Database/Seeders"
        seeders_dir.mkdir(parents=True)
        (seeders_dir / "__init__.py").write_text("")
        (seeders_dir / "DatabaseSeeder.py").write_text(
            "from yello.db.seeder import Seeder\n\n\n"
            "class DatabaseSeeder(Seeder):\n"
            "    def run(self) -> None:\n"
            "        print('migrate seeded!')\n"
        )
        r = run_cli("migrate", "--seed")
        assert r.returncode == 0, r.stderr
        assert "migrate seeded!" in r.stdout

    def test_migrate_fresh_seed_flag_runs_seeder(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("make:migration").returncode == 0
        assert run_cli("migrate").returncode == 0

        seeders_dir = project_dir / "src/app/Database/Seeders"
        seeders_dir.mkdir(parents=True)
        (seeders_dir / "__init__.py").write_text("")
        (seeders_dir / "DatabaseSeeder.py").write_text(
            "from yello.db.seeder import Seeder\n\n\n"
            "class DatabaseSeeder(Seeder):\n"
            "    def run(self) -> None:\n"
            "        print('fresh seeded!')\n"
        )
        r = run_cli("migrate:fresh", "--seed", "--yes")
        assert r.returncode == 0, r.stderr
        assert "fresh seeded!" in r.stdout

    def test_init_end_to_end(self, tmp_path):
        """`yello init` → migrate → generate → route:list → superuser, entirely
        through the scaffolded project."""
        r = _run_in("init", "blog", "--no-install", cwd=tmp_path)
        assert r.returncode == 0, r.stderr

        project = tmp_path / "blog"
        env = {"DJANGO_SETTINGS_MODULE": "config.settings"}

        # The generated manage.py must work too (sys.path insert for src/).
        clean_env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
        r = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=str(project),
            env=clean_env,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr

        r = _run_in("migrate", cwd=project, env_extra=env)
        assert r.returncode == 0, r.stderr
        assert (project / "db.sqlite3").exists()

        r = _run_in("make:model", "Post", "--domain", "Posts", cwd=project, env_extra=env)
        assert r.returncode == 0, r.stderr
        assert (project / "src/app/Domain/Posts/Models/Post.py").exists()
        assert "from app.Domain.Posts.Models.Post import Post" in (
            project / "src/app/models.py"
        ).read_text()

        assert _run_in("make:migration", cwd=project, env_extra=env).returncode == 0
        r = _run_in("migrate", cwd=project, env_extra=env)
        assert r.returncode == 0, r.stderr

        r = _run_in("make:controller", "Post", "--domain", "Posts", cwd=project, env_extra=env)
        assert r.returncode == 0, r.stderr
        assert (project / "src/app/Http/Controllers/PostController.py").exists()

        r = _run_in("route:list", cwd=project, env_extra=env)
        assert r.returncode == 0, r.stderr
        assert "admin/" in r.stdout

        r = _run_in(
            "make:admin", "--email", "admin@example.com", "--password", "verysecret123",
            cwd=project, env_extra=env,
        )
        assert r.returncode == 0, r.stderr
        assert "Superuser created" in r.stdout