import pytest
from typer.testing import CliRunner

from yello.cli import app

runner = CliRunner()


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestMakeModel:
    def test_creates_model_file_and_updates_aggregator(self, workdir):
        result = runner.invoke(app, ["make:model", "Post", "--domain", "Posts"])
        assert result.exit_code == 0, result.output

        target = workdir / "src/app/Domain/Posts/Models/Post.py"
        assert target.exists()
        content = target.read_text()
        assert "from yello.db.models import BaseModel" in content
        assert "class Post(BaseModel):" in content
        assert 'verbose_name = "Post"' in content

        models = workdir / "src/app/models.py"
        assert "from app.Domain.Posts.Models.Post import Post" in models.read_text()

    def test_refuses_to_overwrite(self, workdir):
        assert runner.invoke(app, ["make:model", "Post", "--domain", "Posts"]).exit_code == 0
        result = runner.invoke(app, ["make:model", "Post", "--domain", "Posts"])
        assert result.exit_code == 1
        assert "Refusing to overwrite" in result.output
        assert "Created" not in result.output

    def test_different_models_in_different_domains(self, workdir):
        assert runner.invoke(app, ["make:model", "Post", "--domain", "Posts"]).exit_code == 0
        assert runner.invoke(app, ["make:model", "Post", "--domain", "Blog"]).exit_code == 0
        assert (workdir / "src/app/Domain/Blog/Models/Post.py").exists()
        models = (workdir / "src/app/models.py").read_text()
        assert "from app.Domain.Posts.Models.Post import Post" in models
        assert "from app.Domain.Blog.Models.Post import Post" in models


class TestMakeController:
    def test_creates_controller_with_route_snippet(self, workdir):
        result = runner.invoke(app, ["make:controller", "Post", "--domain", "Posts"])
        assert result.exit_code == 0, result.output

        target = workdir / "src/app/Http/Controllers/PostController.py"
        assert target.exists()
        content = target.read_text()
        assert "class PostController(Controller):" in content
        assert "from app.Domain.Posts.Models.Post import Post" in content
        assert "def index(self, request):" in content

        assert 'path("posts/", PostController.as_view()),' in result.output

    def test_pluralizes_names_ending_in_s(self, workdir):
        result = runner.invoke(app, ["make:controller", "Bus", "--domain", "Buses"])
        assert result.exit_code == 0, result.output
        assert 'path("buses/", BusController.as_view()),' in result.output

    def test_overwrite_guard(self, workdir):
        assert runner.invoke(app, ["make:controller", "Post", "--domain", "Posts"]).exit_code == 0
        result = runner.invoke(app, ["make:controller", "Post", "--domain", "Posts"])
        assert result.exit_code == 1
        assert "Refusing to overwrite" in result.output


class TestMakeRequest:
    def test_creates_request(self, workdir):
        result = runner.invoke(app, ["make:request", "StorePostRequest", "--domain", "Posts"])
        assert result.exit_code == 0, result.output

        target = workdir / "src/app/Http/Requests/StorePostRequest.py"
        assert target.exists()
        content = target.read_text()
        assert "from yello.http.request import Request" in content
        assert "class StorePostRequest(Request):" in content


class TestMakeResource:
    def test_creates_resource(self, workdir):
        result = runner.invoke(app, ["make:resource", "Post", "--domain", "Posts"])
        assert result.exit_code == 0, result.output

        target = workdir / "src/app/Http/Resources/PostResource.py"
        assert target.exists()
        content = target.read_text()
        assert "class PostResource(Resource):" in content
        assert "model = Post" in content
        assert 'fields = "__all__"' in content


class TestMakePolicy:
    def test_creates_policy(self, workdir):
        result = runner.invoke(app, ["make:policy", "Post", "--domain", "Posts"])
        assert result.exit_code == 0, result.output

        target = workdir / "src/app/Domain/Posts/Policies/PostPolicy.py"
        assert target.exists()
        content = target.read_text()
        assert "class PostPolicy(Policy):" in content
        assert "from yello.policy.base import Policy" in content


class TestMakeAdmin:
    def test_creates_admin_registration_file(self, workdir):
        result = runner.invoke(app, ["make:admin", "Post", "--domain", "Posts"])
        assert result.exit_code == 0, result.output

        target = workdir / "src/app/Admin/PostAdmin.py"
        assert target.exists()
        content = target.read_text()
        assert "@admin.register(Post)" in content
        assert "class PostAdmin(BaseModelAdmin):" in content

    def test_requires_domain(self, workdir):
        result = runner.invoke(app, ["make:admin", "Post"])
        assert result.exit_code == 1
        assert "--domain is required" in result.output