from rest_framework import serializers


class Request(serializers.Serializer):
    """Base for Http/Requests classes. Validation only.

    Do not use for output shaping — see ``Resource`` for that. In a controller
    call ``.is_valid(raise_exception=True)`` then read ``validated_data``.
    """