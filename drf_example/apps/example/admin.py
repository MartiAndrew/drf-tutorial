from django.contrib import admin
from drf_example.apps.example.models import Author, Post, Tag


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'posts_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'color', 'posts_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'status', 'is_featured', 'views_count',
                    'published_at']
    list_filter = ['status', 'is_featured', 'created_at', 'published_at',
                   'tags']
    search_fields = ['title', 'content', 'author__user__username']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at', 'views_count']
    filter_horizontal = ['tags']
    date_hierarchy = 'published_at'

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'slug', 'author', 'content', 'excerpt')
        }),
        ('Метаданные', {
            'fields': ('tags', 'featured_image', 'status', 'is_featured')
        }),
        ('Даты', {
            'fields': ('published_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Статистика', {
            'fields': ('views_count',),
            'classes': ('collapse',)
        }),
    )
