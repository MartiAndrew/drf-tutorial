from django.db import transaction
from django.db.models import Q, QuerySet
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from drf_example.apps.example.api.renderer import CSVRenderer
from drf_example.apps.example.api.serializers import PostSerializer
from drf_example.apps.example.models import Post

import django_filters

class CustomThrottle(UserRateThrottle):
    """
    Кастомный throttle для ограничения частоты запросов к API
    """
    scope = 'custom_throttle'
    rate = '1/m'  # Ограничение 100 запросов в час


class PostFilter(django_filters.FilterSet):
    """
    Кастомные фильтры для постов
    """
    # Фильтр по дате создания (диапазон)
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text='Посты, созданные после указанной даты'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text='Посты, созданные до указанной даты'
    )

    # Поиск по автору
    author_name = django_filters.CharFilter(
        method='filter_by_author_name',
        help_text='Поиск по имени автора'
    )

    # Фильтр по популярности
    popular = django_filters.BooleanFilter(
        method='filter_popular',
        help_text='Только популярные посты (views > 100)'
    )

    class Meta:
        model = Post
        fields = {
            'status': ['exact', 'in'],
            'is_featured': ['exact'],
            'published_at': ['year', 'year__gte', 'year__lte'],
            'views_count': ['gte', 'lte'],
        }

    def filter_by_author_name(self, queryset, name, value):
        """Поиск по имени автора"""
        return queryset.filter(
            Q(author__user__first_name__icontains=value) |
            Q(author__user__last_name__icontains=value) |
            Q(author__user__username__icontains=value)
        )

    def filter_popular(self, queryset, name, value):
        """Фильтр популярных постов"""
        if value:
            return queryset.filter(views_count__gte=100)
        return queryset


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с постами
    """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    renderer_classes = [BrowsableAPIRenderer, JSONRenderer, CSVRenderer]
    filterset_class = PostFilter
    throttle_classes = [CustomThrottle]
    ordering_fields = [
        'created_at',
        'published_at',
        'views_count',
        'title',
        'author__user__username'
    ]
    search_fields = [
        'title',
        'content',
        'excerpt',
        'author__user__username',
        'tags__name',
    ]


    def get_serializer_context(self):
        """Передаем дополнительные флаги в контекст сериализатора"""
        context = super().get_serializer_context()

        fields = self.request.query_params.get('fields')
        if fields:
            context['fields'] = fields.split(',')

        return context

    def get_queryset(self):
        """
        Get the list of items for this view.
        This must be an iterable, and may be a queryset.
        Defaults to using `self.queryset`.

        This method should always be used rather than accessing `self.queryset`
        directly, as `self.queryset` gets evaluated only once, and those results
        are cached for all subsequent requests.

        You may want to override this if you need to provide different
        querysets depending on the incoming request.

        (Eg. return a list of items that is specific to the user)
        """
        assert self.queryset is not None, (
            "'%s' should either include a `queryset` attribute, "
            "or override the `get_queryset()` method."
            % self.__class__.__name__
        )

        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            # Ensure queryset is re-evaluated on each request.
            queryset = queryset.all()
        if author_pk := self.kwargs.get('author_pk'):
            # Фильтруем по автору, если указан author_pk
            queryset = queryset.filter(author__pk=author_pk)
        return queryset


    def list(self, request, *args, **kwargs):
        """
        GET /posts/ - список объектов
        Переопределяем для добавления кастомной логики
        """
        raise ValidationError()
        # Получаем queryset через get_queryset()
        queryset = self.filter_queryset(self.get_queryset())

        # Добавляем кастомную фильтрацию
        featured_only = request.query_params.get('featured', None)
        if featured_only == 'true':
            queryset = queryset.filter(is_featured=True)

        # Пагинация
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Сериализация
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


    def retrieve(self, request, *args, **kwargs):
        """
        GET /posts/{id}/ - получение конкретного объекта
        """
        instance = self.get_object()

        # Увеличиваем счетчик просмотров
        instance.views_count += 1
        instance.save(update_fields=['views_count'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        PUT /posts/{id}/ - полное обновление объекта
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Проверяем права на редактирование
        if instance.author.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Вы можете редактировать только свои посты'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(instance, data=request.data,
                                         partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /posts/{id}/ - частичное обновление объекта
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        DELETE /posts/{id}/ - удаление объекта
        """
        instance = self.get_object()

        # Проверяем права на удаление
        if instance.author.user != request.user and not request.user.is_superuser:
            return Response(
                {'error': 'Вы можете удалять только свои посты'},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_destroy(instance)
        return Response(
            {'message': 'Пост успешно удален'},
            status=status.HTTP_204_NO_CONTENT
        )

    def perform_update(self, serializer):
        """Кастомная логика при обновлении"""
        serializer.save()

    def perform_destroy(self, instance):
        """Кастомная логика при удалении"""
        instance.delete()

    @action(detail=False, methods=['get'], renderer_classes=[CSVRenderer])
    def export_csv(self, request):
        """
        GET /posts/export_csv/
        Экспорт всех постов в CSV
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response(
            serializer.data,
            headers={
                'Content-Disposition': 'attachment; filename="posts.csv"'
            }
        )
