from rest_framework import serializers

from drf_example.apps.example.models import Author

class TagPostAuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(max_length=100)


class PostsAuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=False)
    title = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=255)
    tags = TagPostAuthorSerializer(many=True, read_only=True)


class AuthorSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для Author
    """
    full_name = serializers.ReadOnlyField()
    posts_count = serializers.ReadOnlyField()
    posts = serializers.ListSerializer(
        child=PostsAuthorSerializer(),
        required=False,
    )

    def validate_bio(self, value):
        """
        Проверка длины поля bio
        """
        if '!' not in value:
            raise serializers.ValidationError("Bio must contain at least one exclamation mark '!'")

    class Meta:
        model = Author
        fields = [
            'id',
            'user',
            'full_name',
            'bio',
            'avatar',
            'website', 'birth_date',
            'posts_count',
            'created_at', 'updated_at', 'posts',
        ]
        read_only_fields = ['created_at', 'updated_at']

class CreateAuthorSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для Author
    """

    class Meta:
        model = Author
        fields = [
            'id',
            'user',
            'full_name',
            'avatar',
            'website',
            'birth_date',
        ]
