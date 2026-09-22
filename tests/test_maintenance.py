import json

from django.http import HttpResponse

from yello.http.maintenance import MaintenanceModeMiddleware


class TestMaintenanceModeMiddleware:
    def test_passes_through_when_no_lock_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mw = MaintenanceModeMiddleware(get_response=lambda request: HttpResponse("ok"))
        response = mw(request=object())
        assert response.status_code == 200

    def test_returns_503_when_lock_file_present(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        lock_dir = tmp_path / "storage" / "framework"
        lock_dir.mkdir(parents=True)
        (lock_dir / "maintenance.json").write_text(json.dumps({"message": "Down for repairs"}))

        mw = MaintenanceModeMiddleware(get_response=lambda request: HttpResponse("should not run"))
        response = mw(request=object())
        assert response.status_code == 503
        assert b"Down for repairs" in response.content

    def test_includes_retry_after_header(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        lock_dir = tmp_path / "storage" / "framework"
        lock_dir.mkdir(parents=True)
        (lock_dir / "maintenance.json").write_text(json.dumps({"message": "brb", "retry": 60}))

        mw = MaintenanceModeMiddleware(get_response=lambda request: HttpResponse("should not run"))
        response = mw(request=object())
        assert response["Retry-After"] == "60"
