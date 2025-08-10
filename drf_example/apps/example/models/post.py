
from django.db import models
from django.utils.timezone import now


class Post(models.Model):
    """
    Модель поста
    Связи:
    - Many-to-One с Author (много постов - один автор)
    - Many-to-Many с Tag (много постов - много тегов)
    """

    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('published', 'Опубликован'),
        ('archived', 'Архивирован'),
    ]

    title = models.CharField(
        max_length=200,
        verbose_name='Заголовок'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name='Slug'
    )
    content = models.TextField(
        verbose_name='Содержание'
    )
    excerpt = models.TextField(
        max_length=300,
        blank=True,
        verbose_name='Краткое описание'
    )

    # Many-to-One связь с Author
    author = models.ForeignKey(
        'example.Author',
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор'
    )

    # Many-to-Many связь с Tag
    tags = models.ManyToManyField(
        'example.Tag',  # Предполагается, что Tag определен в том же приложении
        blank=True,
        related_name='posts',
        verbose_name='Теги'
    )

    featured_image = models.ImageField(
        upload_to='posts/',
        blank=True,
        null=True,
        verbose_name='Изображение'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Статус'
    )

    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество просмотров'
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name='Рекомендуемый'
    )

    published_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Дата публикации'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['author', 'status']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Автоматически устанавливаем дату публикации при смене статуса
        if self.status == 'published' and not self.published_at:
            self.published_at = now()
        super().save(*args, **kwargs)

    @property
    def is_published(self):
        return self.status == 'published'

    @property
    def reading_time(self):
        """Примерное время чтения (слов в минуту)"""
        words_count = len(self.content.split())
        return max(1, words_count // 200)  # 200 слов в минуту
