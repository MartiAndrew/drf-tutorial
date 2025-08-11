import re

from rest_framework import serializers

from drf_example.apps.example.models import Tag


class ColorField(serializers.Field):
    """
    Кастомное поле для работы с цветами в HEX формате
    """

    def to_representation(self, value):
        """Конвертируем значение в JSON-представление"""
        if not value:
            return None

        # Возвращаем объект с HEX и RGB значениями
        hex_value = value
        # Простая конвертация HEX -> RGB
        if hex_value.startswith('#'):
            hex_value = hex_value[1:]

        try:
            r = int(hex_value[0:2], 16)
            g = int(hex_value[2:4], 16)
            b = int(hex_value[4:6], 16)

            return {
                'hex': f"#{hex_value}",
                'rgb': f"rgb({r}, {g}, {b})",
                'rgba': f"rgba({r}, {g}, {b}, 1.0)"
            }
        except (ValueError, IndexError):
            return {'hex': value, 'rgb': None, 'rgba': None}

    def to_internal_value(self, data):
        """Конвертируем JSON-представление в значение"""
        if isinstance(data, dict) and 'hex' in data:
            hex_value = data['hex']
        elif isinstance(data, str):
            hex_value = data
        else:
            raise serializers.ValidationError(
                'Ожидается HEX цвет или объект с полем hex')

        # Валидируем HEX формат
        if not re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', hex_value):
            raise serializers.ValidationError('Неверный формат HEX цвета')

        return hex_value

class TagSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для Tag
    """
    posts_count = serializers.ReadOnlyField()
    color = ColorField()

    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'slug', 'description',
            'color', 'posts_count', 'created_at'
        ]
        read_only_fields = ['created_at']
