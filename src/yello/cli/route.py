"""yello route:list — list registered URLs."""

import typer

from yello.cli._helpers import _bootstrap_django, console


def _collect(patterns, prefix: str = ""):
    rows = []
    for p in patterns:
        path = prefix
        if hasattr(p, "pattern"):
            path += str(p.pattern)
        if hasattr(p, "url_patterns"):
            rows.extend(_collect(p.url_patterns, path))
        else:
            view = getattr(p, "callback", None)
            if view is None:
                view_repr = "?"
            else:
                view_repr = f"{getattr(view, '__module__', '')}.{getattr(view, '__name__', '')}"
            rows.append((path, getattr(p, "name", None) or "", view_repr))
    return rows


def route_list() -> None:
    """List every registered URL pattern."""
    _bootstrap_django()
    from django.urls import get_resolver

    from rich.table import Table

    resolver = get_resolver()
    rows = _collect(resolver.url_patterns)

    table = Table(title="Registered URLs")
    table.add_column("Path", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("View")
    for path, name, view in rows:
        table.add_row(path, name, view)
    console.print(table)