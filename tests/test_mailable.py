import pytest

from yello.mail.mailable import Mailable


class WelcomeMail(Mailable):
    subject = "Welcome!"

    def build(self) -> dict:
        return {"body": "Thanks for signing up."}


class TestMailable:
    def test_build_not_implemented_by_default(self):
        with pytest.raises(NotImplementedError):
            Mailable().build()

    def test_send_calls_django_send_mail(self, mailoutbox):
        WelcomeMail().send(to=["user@example.com"])
        assert len(mailoutbox) == 1
        assert mailoutbox[0].subject == "Welcome!"
        assert mailoutbox[0].body == "Thanks for signing up."
        assert mailoutbox[0].to == ["user@example.com"]
