from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from drf_example.apps.example.api.serializers import TagSerializer
from drf_example.apps.example.models import Tag


class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с тегами
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
