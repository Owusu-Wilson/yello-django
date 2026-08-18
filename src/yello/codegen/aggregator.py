"""Maintenance of the ``src/app/models.py`` import aggregator.

``models.py`` is the single file that makes the one-app domain layout legal
Django: it imports every ``Domain/<Name>/Models/*.py`` model. It is never
hand-edited; these functions append/remove the import lines idempotently.

Parsing is deliberately dead-simple line diffing (not an AST rewrite) so the
behavior is obvious and inspectable.
"""

from pathlib import Path

HEADER_COMMENT = "# app/models.py — auto-maintained by yello make:model, safe to commit"
_IMPORT_PREFIX = "from app.Domain."
_MODELS_SUBPATH = "src/app/models.py"


def _import_line(domain: str, model_name: str) -> str:
    return f"{_IMPORT_PREFIX}{domain}.Models.{model_name} import {model_name}"


def _models_file(project_root: Path) -> Path:
    return Path(project_root) / _MODELS_SUBPATH


def _is_import(line: str) -> bool:
    return line.startswith(_IMPORT_PREFIX)


def _parse(content: str) -> tuple[list[str], list[str]]:
    """Split content into (header lines, import lines). Blank lines are dropped."""
    header = []
    imports = []
    for line in content.splitlines():
        if _is_import(line):
            imports.append(line)
        elif line.strip():
            header.append(line)
    return header, imports


def _render(header: list[str], imports: list[str]) -> str:
    if not header and not imports:
        return ""
    blocks = []
    if header:
        blocks.append("\n".join(header))
    if imports:
        blocks.append("\n".join(imports))
    return "\n\n".join(blocks) + "\n"


def add_model_import(project_root: Path, domain: str, model_name: str) -> bool:
    """Idempotently add the import for a generated model to ``app/models.py``.

    Creates the file (with a header comment) if it does not exist yet, keeps
    imports alphabetically sorted, and never inserts duplicates. Returns
    ``True`` if the file was changed, ``False`` otherwise.
    """
    path = _models_file(project_root)
    line = _import_line(domain, model_name)

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render([HEADER_COMMENT], [line]))
        return True

    header, imports = _parse(path.read_text())
    if line in imports:
        return False

    imports.append(line)
    imports.sort()
    path.write_text(_render(header, imports))
    return True


def remove_model_import(project_root: Path, domain: str, model_name: str) -> bool:
    """Remove the import line for a model from ``app/models.py``.

    Returns ``True`` if the file was changed, ``False`` if the line was not
    present (or the file does not exist).
    """
    path = _models_file(project_root)
    if not path.exists():
        return False

    header, imports = _parse(path.read_text())
    line = _import_line(domain, model_name)
    if line not in imports:
        return False

    imports.remove(line)
    path.write_text(_render(header, imports))
    return True