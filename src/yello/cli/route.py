"""yello route:list — list registered URLs."""

from yello.console.command import Command, console


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


class RouteListCommand(Command):
    """List every registered URL pattern."""

    def handle(self) -> None:
        self.bootstrap()
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
