"""Base for Database/Seeders classes."""


class Seeder:
    def run(self) -> None:
        raise NotImplementedError

    def call(self, *seeder_classes: type["Seeder"]) -> None:
        for seeder_cls in seeder_classes:
            seeder_cls().run()
