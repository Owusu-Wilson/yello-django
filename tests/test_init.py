import pytest
from typer.testing import CliRunner

from yello.cli import app

runner = CliRunner()


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestInit:
    def test_scaffolds_full_skeleton(self, workdir):
        result = runner.invoke(app, ["init", "blog", "--no-install"])
        assert result.exit_code == 0, result.output

        base = workdir / "blog"
        assert (base / "manage.py").exists()
        assert (base / "config/__init__.py").exists()
        assert (base / "config/settings.py").exists()
        assert (base / "config/urls.py").exists()
        assert (base / "src/app/__init__.py").exists()
        assert (base / "src/app/apps.py").exists()
        assert (base / "src/app/models.py").exists()
        assert (base / "src/app/migrations/__init__.py").exists()
        assert (base / "Pipfile").exists()
        assert (base / ".gitignore").exists()

    def test_models_py_has_aggregator_header(self, workdir):
        result = runner.invoke(app, ["init", "blog", "--no-install"])
        assert result.exit_code == 0, result.output
        content = (workdir / "blog/src/app/models.py").read_text()
        assert "auto-maintained by" in content

    def test_pipfile_pins_dependencies(self, workdir):
        runner.invoke(app, ["init", "blog", "--no-install"])
        content = (workdir / "blog/Pipfile").read_text()
        assert "django" in content
        assert "djangorestframework" in content
        assert "yello-core" in content

    def test_settings_include_auth_and_app(self, workdir):
        runner.invoke(app, ["init", "blog", "--no-install"])
        content = (workdir / "blog/config/settings.py").read_text()
        assert '"app"' in content
        assert '"yello.auth"' in content
        assert 'AUTH_USER_MODEL = "yello_auth.User"' in content

    def test_init_in_current_directory(self, workdir):
        result = runner.invoke(app, ["init", "--no-install"])
        assert result.exit_code == 0, result.output
        assert (workdir / "manage.py").exists()
        assert (workdir / "config/settings.py").exists()

    def test_refuses_non_empty_directory(self, workdir):
        (workdir / "blog").mkdir()
        (workdir / "blog" / "existing.txt").write_text("x")
        result = runner.invoke(app, ["init", "blog", "--no-install"])
        assert result.exit_code == 1
        assert "not empty" in result.output
        assert (workdir / "blog" / "existing.txt").exists()

    def test_force_overwrites(self, workdir):
        (workdir / "blog").mkdir()
        (workdir / "blog" / "stale.txt").write_text("stale")
        result = runner.invoke(app, ["init", "blog", "--no-install", "--force"])
        assert result.exit_code == 0, result.output
        assert (workdir / "blog" / "config" / "settings.py").exists()

    def test_rejects_invalid_name(self, workdir):
        result = runner.invoke(app, ["init", "not valid!", "--no-install"])
        assert result.exit_code == 1
        assert "not a valid project name" in result.output

    def test_unknown_manager_errors(self, workdir):
        result = runner.invoke(app, ["init", "blog", "--manager", "poetry", "--install"])
        assert result.exit_code == 1
        assert "Unknown package manager" in result.output