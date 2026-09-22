import pytest

from yello.exceptions.base import YelloException


class TestYelloException:
    def test_is_an_exception(self):
        with pytest.raises(YelloException):
            raise YelloException("boom")
