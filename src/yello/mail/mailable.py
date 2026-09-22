"""Base for src/app/Mail classes."""


class Mailable:
    subject = ""

    def build(self) -> dict:
        raise NotImplementedError

    def send(self, to: list[str]) -> None:
        from django.core.mail import send_mail

        data = self.build()
        send_mail(self.subject, data.get("body", ""), None, to)
