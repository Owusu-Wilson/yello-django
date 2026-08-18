import pytest

from yello.codegen.aggregator import (
    HEADER_COMMENT,
    _import_line,
    add_model_import,
    remove_model_import,
)


@pytest.fixture
def models_file(tmp_path):
    path = tmp_path / "src/app/models.py"
    path.parent.mkdir(parents=True)
    return path


class TestImportLine:
    def test_format(self):
        assert _import_line("Posts", "Post") == "from app.Domain.Posts.Models.Post import Post"


class TestAddModelImport:
    def test_creates_missing_file_with_header_and_import(self, tmp_path):
        assert add_model_import(tmp_path, "Posts", "Post") is True
        content = (tmp_path / "src/app/models.py").read_text()
        assert content == f"{HEADER_COMMENT}\n\nfrom app.Domain.Posts.Models.Post import Post\n"

    def test_creates_parent_directories(self, tmp_path):
        add_model_import(tmp_path, "Posts", "Post")
        assert (tmp_path / "src/app/models.py").exists()

    def test_is_idempotent(self, tmp_path):
        assert add_model_import(tmp_path, "Posts", "Post") is True
        assert add_model_import(tmp_path, "Posts", "Post") is False
        content = (tmp_path / "src/app/models.py").read_text()
        assert content.count("from app.Domain.Posts.Models.Post import Post") == 1

    def test_appends_to_existing_imports(self, models_file):
        models_file.write_text(
            f"{HEADER_COMMENT}\n\nfrom app.Domain.Comments.Models.Comment import Comment\n"
        )
        assert add_model_import(models_file.parent.parent.parent, "Posts", "Post") is True
        content = models_file.read_text()
        assert "from app.Domain.Posts.Models.Post import Post" in content
        assert "from app.Domain.Comments.Models.Comment import Comment" in content

    def test_sorts_imports_alphabetically(self, models_file):
        models_file.write_text(f"{HEADER_COMMENT}\n\nfrom app.Domain.Posts.Models.Post import Post\n")
        assert add_model_import(models_file.parent.parent.parent, "Categories", "Category") is True
        content = models_file.read_text()
        categories = content.index("from app.Domain.Categories.Models.Category import Category")
        posts = content.index("from app.Domain.Posts.Models.Post import Post")
        assert categories < posts

    def test_preserves_custom_header(self, models_file):
        models_file.write_text("# custom header line\nfrom app.Domain.Comments.Models.Comment import Comment\n")
        assert add_model_import(models_file.parent.parent.parent, "Posts", "Post") is True
        content = models_file.read_text()
        assert content.startswith("# custom header line")
        assert "# custom header line\n\nfrom app.Domain.Comments.Models.Comment import Comment" in content

    def test_multiple_adds_stay_sorted(self, tmp_path):
        for domain, name in [("Posts", "Post"), ("Tags", "Tag"), ("Categories", "Category")]:
            add_model_import(tmp_path, domain, name)
        imports = [l for l in (tmp_path / "src/app/models.py").read_text().splitlines() if l.startswith("from app.Domain.")]
        assert imports == sorted(imports)
        assert len(imports) == 3

    def test_handles_empty_existing_file(self, models_file):
        models_file.write_text("")
        assert add_model_import(models_file.parent.parent.parent, "Posts", "Post") is True
        assert "from app.Domain.Posts.Models.Post import Post" in models_file.read_text()


class TestRemoveModelImport:
    def test_removes_line(self, tmp_path):
        add_model_import(tmp_path, "Posts", "Post")
        assert remove_model_import(tmp_path, "Posts", "Post") is True
        content = (tmp_path / "src/app/models.py").read_text()
        assert "from app.Domain.Posts.Models.Post import Post" not in content

    def test_noop_when_line_missing(self, tmp_path):
        add_model_import(tmp_path, "Posts", "Post")
        assert remove_model_import(tmp_path, "Categories", "Category") is False
        assert "Post" in (tmp_path / "src/app/models.py").read_text()

    def test_noop_when_file_missing(self, tmp_path):
        assert remove_model_import(tmp_path, "Posts", "Post") is False
        assert not (tmp_path / "src/app/models.py").exists()

    def test_keeps_remaining_imports_sorted(self, tmp_path):
        add_model_import(tmp_path, "Posts", "Post")
        add_model_import(tmp_path, "Categories", "Category")
        remove_model_import(tmp_path, "Posts", "Post")
        content = (tmp_path / "src/app/models.py").read_text()
        assert "Category" in content
        assert "Post" not in content
        imports = [l for l in content.splitlines() if l.startswith("from app.Domain.")]
        assert imports == sorted(imports)

    def test_header_preserved_after_last_removal(self, tmp_path):
        add_model_import(tmp_path, "Posts", "Post")
        remove_model_import(tmp_path, "Posts", "Post")
        content = (tmp_path / "src/app/models.py").read_text()
        assert HEADER_COMMENT in content
        assert "from app.Domain." not in content

    def test_remove_and_re_add(self, tmp_path):
        add_model_import(tmp_path, "Posts", "Post")
        remove_model_import(tmp_path, "Posts", "Post")
        assert add_model_import(tmp_path, "Posts", "Post") is True
        content = (tmp_path / "src/app/models.py").read_text()
        assert content.count("from app.Domain.Posts.Models.Post import Post") == 1

    def test_removing_last_line_without_header_empties_file(self, tmp_path):
        models_file = tmp_path / "src/app/models.py"
        models_file.parent.mkdir(parents=True)
        models_file.write_text("from app.Domain.Posts.Models.Post import Post\n")
        assert remove_model_import(tmp_path, "Posts", "Post") is True
        assert models_file.read_text() == ""
        assert add_model_import(tmp_path, "Posts", "Post") is True
        assert "from app.Domain.Posts.Models.Post import Post" in models_file.read_text()