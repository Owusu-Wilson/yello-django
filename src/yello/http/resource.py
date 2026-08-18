from rest_framework import serializers


class Resource(serializers.ModelSerializer):
    """Base for Http/Resources classes. Output shaping only.

    Pair with a ``Request`` class for input validation rather than reusing this
    for writes.
    """