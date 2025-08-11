from rest_framework import serializers

from drf_example.apps.example.models import Post


class PostSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для Post
    """
    reading_time = serializers.ReadOnlyField()
    is_published = serializers.ReadOnlyField()
    featured_image = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text='Изображение для поста, необязательное поле'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        fields = self.context.get('fields')

        if fields is not None:
            # Оставляем только указанные поля
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


    def validate(self, attrs):
        return attrs

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'excerpt',
            'author', 'tags', 'featured_image', 'status',
            'views_count', 'is_featured', 'reading_time',
            'is_published', 'published_at', 'created_at', 'updated_at',
            # 'author_name',
        ]
        read_only_fields = ['created_at', 'updated_at', 'views_count']
