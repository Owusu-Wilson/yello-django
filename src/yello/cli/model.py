"""yello model:show — inspect a model's fields and relations."""

import typer

from yello.console.command import Command, console


class ModelShowCommand(Command):
    """Show a model's fields, types, and relations."""

    def handle(
        self,
        name: str = typer.Argument(..., help="Model name, e.g. Post."),
        domain: str = typer.Option(..., "--domain", "-d", help="PascalCase domain folder under Domain/."),
    ) -> None:
        self.bootstrap()
        import importlib

        from rich.table import Table

        module = importlib.import_module(f"app.Domain.{domain}.Models.{name}")
        model = getattr(module, name)

        table = Table(title=f"{name} fields")
        table.add_column("Field", style="cyan")
        table.add_column("Type")
        table.add_column("Null?")
        table.add_column("Relation")
        for field in model._meta.get_fields():
            relation = getattr(field, "related_model", None)
            table.add_row(
                field.name,
                type(field).__name__,
                "Yes" if getattr(field, "null", False) else "No",
                relation.__name__ if relation else "",
            )
        console.print(table)
