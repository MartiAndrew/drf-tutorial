from django.db import models


class Tag(models.Model):
    """
    Модель тега
    Связь: Many-to-Many с Post (много тегов - много постов)
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Название'
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name='Slug'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    color = models.CharField(
        max_length=7,
        default='#007bff',
        help_text='Цвет в формате HEX',
        verbose_name='Цвет'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def posts_count(self):
        return self.posts.count()
