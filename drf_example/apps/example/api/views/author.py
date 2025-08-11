from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from drf_example.apps.example.api.renderer import CSVRenderer
from drf_example.apps.example.api.serializers import AuthorSerializer
from drf_example.apps.example.api.serializers.author import \
    CreateAuthorSerializer
from drf_example.apps.example.models import Author


class AuthorViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с авторами
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    ordering_fields = '__all__'
    # filterset_fields = (
    #     'birth_date',
    #     'created_at',
    #     'user',
    # )
    search_fields = ('user__username', 'user__email')
    filterset_fields = {
        'bio': ['exact', 'icontains'],
        'birth_date': ['year', 'year__gte', 'year__lte'],
    }

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(*args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateAuthorSerializer
        if self.action == 'list':
            return AuthorSerializer
        return super().get_serializer_class()


    @action(
        detail=True,
        methods=['get'],
        url_path='posts-count',
    )
    def count_posts(self, request, pk=None):
        """
        Получить лучшего автора (по количеству постов)
        """
        author = self.get_object()
        posts_count = author.posts.count()
        return Response({
            'author': author.full_name,
            'posts_count': posts_count
        }, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['get']
    )
    def best_author(self, request, *args, **kwargs):
        return Response({'best': 1}, status=status.HTTP_200_OK)