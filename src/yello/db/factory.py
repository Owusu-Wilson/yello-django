"""Base for Database/Factories classes."""


class Factory:
    model = None

    def definition(self) -> dict:
        raise NotImplementedError

    def make(self, **overrides):
        data = {**self.definition(), **overrides}
        return self.model(**data)

    def create(self, **overrides):
        instance = self.make(**overrides)
        instance.save()
        return instance
