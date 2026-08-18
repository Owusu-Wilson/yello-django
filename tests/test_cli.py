import pytest
from typer.testing import CliRunner

from yello.cli import app

runner = CliRunner()


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
            "route:list",
            "dev",
            "migrate",
        ):
            assert name in result.output

    @pytest.mark.django_db
    def test_migrate_status(self):
        result = runner.invoke(app, ["migrate", "status"])
        assert result.exit_code == 0, result.output
        assert "0001_initial" in result.output

    def test_route_list(self):
        result = runner.invoke(app, ["route:list"])
        assert result.exit_code == 0, result.output
        assert "admin/" in result.output

    def test_migrate_no_args_is_help(self):
        result = runner.invoke(app, ["migrate"])
        assert result.exit_code in (0, 2)
        assert "make" in result.output
        assert "rollback" in result.output


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

        r = run_cli("migrate", "make")
        assert r.returncode == 0, r.stderr
        assert (project_dir / "src/app/migrations/0001_initial.py").exists()

        r = run_cli("migrate", "run")
        assert r.returncode == 0, r.stderr
        assert (project_dir / "db.sqlite3").exists()

        r = run_cli("migrate", "status")
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
        r = run_cli("migrate", "run")
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
        assert run_cli("migrate", "make").returncode == 0
        assert run_cli("migrate", "run").returncode == 0

        r = run_cli("migrate", "rollback", "app")
        assert r.returncode == 0, r.stderr
        assert "app.0001_initial" in r.stdout

        r = run_cli("migrate", "status")
        assert "app.0001_initial" not in r.stdout

    def test_migrate_fresh(self, project_dir, run_cli):
        assert run_cli("make:model", "Post", "--domain", "Posts").returncode == 0
        assert run_cli("migrate", "make").returncode == 0
        assert run_cli("migrate", "run").returncode == 0

        r = run_cli("migrate", "fresh", "--yes")
        assert r.returncode == 0, r.stderr