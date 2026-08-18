class Policy:
    """Base for Domain/<Entity>/Policies classes.

    Plain Python — no container, no gate, no service resolution. Subclasses
    implement boolean-returning methods (e.g. ``update``, ``delete``) which are
    called directly from controllers.
    """

    def before(self, user, action=None):
        """Optional override.

        Return ``True``/``False`` to short-circuit every check (e.g. superuser
        bypass), or ``None`` to fall through to the named method.
        """
        return None