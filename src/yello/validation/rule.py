"""Base for src/app/Rules classes — usable directly as a DRF field validator."""


class Rule:
    message = "The given value is invalid."

    def passes(self, value) -> bool:
        raise NotImplementedError

    def __call__(self, value) -> None:
        if not self.passes(value):
            from rest_framework.serializers import ValidationError

            raise ValidationError(self.message)
