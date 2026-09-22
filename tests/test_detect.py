import os

from yello.cli._helpers import _detect_settings_module, _load_dotenv


class TestDetectSettingsModule:
    def test_from_yello_file(self, tmp_path):
        (tmp_path / ".yello").write_text("DJANGO_SETTINGS_MODULE=myproj.settings\n")
        assert _detect_settings_module(tmp_path) == "myproj.settings"

    def test_yello_file_with_quotes(self, tmp_path):
        (tmp_path / ".yello").write_text('DJANGO_SETTINGS_MODULE = "myproj.settings"\n')
        assert _detect_settings_module(tmp_path) == "myproj.settings"

    def test_yello_file_beats_manage_py(self, tmp_path):
        (tmp_path / ".yello").write_text("DJANGO_SETTINGS_MODULE=myproj.settings\n")
        (tmp_path / "manage.py").write_text(
            'os.environ.setdefault("DJANGO_SETTINGS_MODULE", "other.settings")'
        )
        assert _detect_settings_module(tmp_path) == "myproj.settings"

    def test_from_manage_py(self, tmp_path):
        (tmp_path / "manage.py").write_text(
            'os.environ.setdefault("DJANGO_SETTINGS_MODULE", "restock_backend.settings")\n'
        )
        assert _detect_settings_module(tmp_path) == "restock_backend.settings"

    def test_from_config_dir(self, tmp_path):
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "settings.py").write_text("")
        assert _detect_settings_module(tmp_path) == "config.settings"

    def test_config_beats_other_subdirs(self, tmp_path):
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "settings.py").write_text("")
        (tmp_path / "other").mkdir()
        (tmp_path / "other" / "settings.py").write_text("")
        assert _detect_settings_module(tmp_path) == "config.settings"

    def test_from_subdir_settings(self, tmp_path):
        (tmp_path / "restock_backend").mkdir()
        (tmp_path / "restock_backend" / "settings.py").write_text("")
        assert _detect_settings_module(tmp_path) == "restock_backend.settings"

    def test_none_when_no_project(self, tmp_path):
        assert _detect_settings_module(tmp_path) is None


class TestLoadDotenv:
    def test_sets_env_vars_from_file(self, tmp_path, monkeypatch):
        (tmp_path / ".env").write_text("DJANGO_SECRET_KEY=abc123\nFOO=bar\n")
        monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
        monkeypatch.delenv("FOO", raising=False)
        _load_dotenv(tmp_path)
        assert os.environ["DJANGO_SECRET_KEY"] == "abc123"
        assert os.environ["FOO"] == "bar"

    def test_does_not_override_existing_env(self, tmp_path, monkeypatch):
        (tmp_path / ".env").write_text("FOO=fromfile\n")
        monkeypatch.setenv("FOO", "fromenv")
        _load_dotenv(tmp_path)
        assert os.environ["FOO"] == "fromenv"

    def test_missing_file_is_a_noop(self, tmp_path):
        _load_dotenv(tmp_path)  # must not raise