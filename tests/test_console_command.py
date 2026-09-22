import typer
import pytest

from yello.console.command import Command


class TestCommandOutput:
    def test_handle_not_implemented(self):
        with pytest.raises(NotImplementedError):
            Command().handle()

    def test_info_prints_green(self, capsys):
        Command().info("ok")
        assert "ok" in capsys.readouterr().out

    def test_error_prints_and_is_readable(self, capsys):
        Command().error("bad")
        assert "bad" in capsys.readouterr().out

    def test_fail_prints_error_and_exits_1(self, capsys):
        with pytest.raises(typer.Exit) as exc_info:
            Command().fail("nope")
        assert exc_info.value.exit_code == 1
        assert "nope" in capsys.readouterr().out

    def test_confirm_delegates_to_typer(self, monkeypatch):
        monkeypatch.setattr(typer, "confirm", lambda q, default=False: True)
        assert Command().confirm("continue?") is True
