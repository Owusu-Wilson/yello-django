"""Maintenance-mode middleware — checks storage/framework/maintenance.json."""

import json
from pathlib import Path

from django.http import JsonResponse


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lock_file = Path.cwd() / "storage" / "framework" / "maintenance.json"
        if lock_file.exists():
            data = json.loads(lock_file.read_text())
            response = JsonResponse({"message": data.get("message", "Down for maintenance.")}, status=503)
            if data.get("retry"):
                response["Retry-After"] = str(data["retry"])
            return response
        return self.get_response(request)
