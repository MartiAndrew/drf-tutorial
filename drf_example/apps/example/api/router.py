from rest_framework.routers import APIRootView, DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter

from drf_example.apps.example.api.views import TagViewSet, PostViewSet, AuthorViewSet
from drf_example.custom_router import EnhancedAPIRouter


class HubAPIRootView(APIRootView):
    """Корневой view для апи."""

    __doc__ = 'Приложение хаб'
    name = 'hub'

# Основной роутер
router = EnhancedAPIRouter()
router.APIRootView = HubAPIRootView

# Регистрация основных ViewSet'ов
router.register('tags', TagViewSet, 'tags')
router.register('posts', PostViewSet, 'posts')
router.register('authors', AuthorViewSet, 'authors')

# Создание nested router для постов авторов
author_posts_router = NestedSimpleRouter(
    router,
    r'authors',
    lookup='author'
)
# ВАЖНО: Обязательно указываем basename для nested router
author_posts_router.register(r'posts', PostViewSet, basename='author-posts')

# Регистрируем nested router в основном роутере под пустым префиксом
# Это позволит nested URLs работать как /authors/{id}/posts/ вместо /prefix/authors/{id}/posts/
router.register('', author_posts_router, 'nested')