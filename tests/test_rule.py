import pytest
from rest_framework.serializers import ValidationError

from yello.validation.rule import Rule


class Even(Rule):
    message = "Value must be even."

    def passes(self, value) -> bool:
        return value % 2 == 0


class TestRule:
    def test_passes_not_implemented_by_default(self):
        with pytest.raises(NotImplementedError):
            Rule().passes(1)

    def test_call_is_noop_when_it_passes(self):
        Even()(4)  # must not raise

    def test_call_raises_validation_error_with_message(self):
        with pytest.raises(ValidationError) as exc_info:
            Even()(3)
        assert "Value must be even." in str(exc_info.value)
