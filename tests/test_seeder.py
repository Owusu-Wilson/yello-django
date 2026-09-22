import pytest

from yello.db.seeder import Seeder


class TestSeeder:
    def test_run_not_implemented(self):
        with pytest.raises(NotImplementedError):
            Seeder().run()

    def test_call_runs_each_seeder_in_order(self):
        order = []

        class First(Seeder):
            def run(self):
                order.append("first")

        class Second(Seeder):
            def run(self):
                order.append("second")

        Seeder().call(First, Second)
        assert order == ["first", "second"]
