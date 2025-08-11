from collections import OrderedDict
from typing import Any

from django.urls import NoReverseMatch, include, re_path
from django.urls import reverse as django_reverse
from rest_framework import reverse
from rest_framework.routers import DefaultRouter, SimpleRouter, APIRootView
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSetMixin


class EnhancedAPIRouter(DefaultRouter):
    """
    Улучшенный роутер для Django REST Framework.

    Поддерживает регистрацию как ViewSet'ов, так и других роутеров
    (включая NestedSimpleRouter) с современной типизацией и дополнительными возможностями.

    Примеры использования:
        # Регистрация ViewSet
        router.register('users', UserViewSet)

        # Регистрация другого роутера
        router.register('blog', blog_router, 'blog')

        # Регистрация nested router
        nested_router = NestedSimpleRouter(router, 'users', lookup='user')
        nested_router.register('posts', PostViewSet, basename='user-posts')
        router.register('', nested_router, 'nested')

        # Явные методы для ясности
        router.register_viewset('products', ProductViewSet)
        router.register_router('admin', admin_router, 'admin')
    """

    def __init__(self, *args, **kwargs):
        """
        Инициализация роутера.

        Args:
            auto_basename: Автоматически генерировать basename для роутеров
            strict_checking: Использовать строгую проверку типов
        """
        self.auto_basename = kwargs.pop('auto_basename', True)
        self.strict_checking = kwargs.pop('strict_checking', False)
        super().__init__(*args, **kwargs)

    def register(
        self,
        prefix: str,
        viewset_or_router: type[
                               ViewSetMixin] | SimpleRouter | DefaultRouter | Any,
        basename: str | None = None
    ) -> None:
        """
        Регистрирует ViewSet или роутер.

        Args:
            prefix: URL префикс
            viewset_or_router: ViewSet класс или экземпляр роутера
            basename: Базовое имя для URL patterns
        """
        if self._is_router(viewset_or_router):
            # Автоматически генерируем basename если не указан
            if basename is None and self.auto_basename:
                basename = prefix.replace('/', '_') if prefix else 'nested'
            elif basename is None:
                basename = prefix if prefix else 'nested'

        # Используем стандартную регистрацию для ViewSet'ов
        # или сохраняем роутер в registry для последующей обработки
        super().register(prefix, viewset_or_router, basename)

    def register_viewset(
        self,
        prefix: str,
        viewset: type[ViewSetMixin],
        basename: str | None = None
    ) -> None:
        """
        Явно регистрирует ViewSet (для ясности кода).

        Args:
            prefix: URL префикс
            viewset: ViewSet класс для регистрации
            basename: Базовое имя для URL patterns
        """
        if self._is_router(viewset):
            raise ValueError(f"Expected ViewSet, got router: {viewset}")
        super().register(prefix, viewset, basename)

    def register_router(
        self,
        prefix: str,
        router: SimpleRouter | DefaultRouter | Any,
        namespace: str | None = None
    ) -> None:
        """
        Явно регистрирует роутер.

        Args:
            prefix: URL префикс для роутера
            router: Роутер для регистрации
            namespace: Namespace для URL patterns
        """
        if not self._is_router(router):
            raise ValueError(f"Expected router, got: {router}")

        if namespace is None:
            namespace = prefix.replace('/',
                                       '_') if self.auto_basename and prefix else prefix or 'nested'

        super().register(prefix, router, namespace)

    def _is_router(self, obj: Any) -> bool:
        """
        Проверяет, является ли объект роутером.

        Args:
            obj: Объект для проверки

        Returns:
            True если объект является роутером
        """
        if self.strict_checking:
            # Проверяем известные типы роутеров
            router_types = [SimpleRouter, DefaultRouter]

            # Безопасно проверяем NestedSimpleRouter если доступен
            try:
                from rest_framework_nested.routers import NestedSimpleRouter
                router_types.append(NestedSimpleRouter)
            except ImportError:
                pass

            return isinstance(obj, tuple(router_types))

        # Duck typing - проверяем наличие необходимых атрибутов роутера
        return (
            hasattr(obj, 'urls') and
            hasattr(obj, 'registry') and
            not self._is_viewset_class(obj)
        )

    def _is_viewset_class(self, obj: Any) -> bool:
        """
        Проверяет, является ли объект классом ViewSet'а.

        Args:
            obj: Объект для проверки

        Returns:
            True если объект является классом ViewSet'а
        """
        return (
            isinstance(obj, type) and (
            issubclass(obj, APIView) or
            issubclass(obj, ViewSetMixin)
        )
        )

    def _is_viewset(self, obj: Any) -> bool:
        """
        Проверяет, является ли объект ViewSet'ом (класс или экземпляр).

        Args:
            obj: Объект для проверки

        Returns:
            True если объект является ViewSet'ом
        """
        # Проверяем класс ViewSet'а
        if self._is_viewset_class(obj):
            return True

        # Для экземпляров проверяем наличие метода as_view
        return hasattr(obj, 'as_view') and callable(getattr(obj, 'as_view'))

    def _is_nested_router(self, obj: Any) -> bool:
        """
        Проверяет, является ли объект NestedSimpleRouter.

        Args:
            obj: Объект для проверки

        Returns:
            True если объект является NestedSimpleRouter
        """
        try:
            from rest_framework_nested.routers import NestedSimpleRouter
            return isinstance(obj, NestedSimpleRouter)
        except ImportError:
            return False

    def get_urls(self) -> list[Any]:
        """Генерирует список URL паттернов."""
        ret = []

        for prefix, viewset_or_router, basename in self.registry:
            if self._is_router(viewset_or_router):
                # Обрабатываем роутер
                router_urls = self._get_router_urls(prefix, viewset_or_router,
                                                    basename)
                ret.extend(router_urls)
            elif self._is_viewset(viewset_or_router):
                # Обрабатываем ViewSet
                viewset_urls = self._get_viewset_urls(prefix, viewset_or_router,
                                                      basename)
                ret.extend(viewset_urls)
            else:
                # Неизвестный тип - выводим предупреждение
                self._handle_unknown_type(prefix, viewset_or_router, basename,
                                          ret)

        # Добавляем корневое view если нужно
        if self.include_root_view:
            root_view = self.get_api_root_view(api_urls=ret)
            root_url = re_path(r'^$', root_view, name=self.root_view_name)
            ret.append(root_url)

        return ret

    def _get_router_urls(self, prefix: str, router: Any, basename: str) -> list[
        Any]:
        """
        Генерирует URL паттерны для роутера.

        Args:
            prefix: URL префикс
            router: Роутер
            basename: Базовое имя

        Returns:
            Список URL паттернов
        """
        if self._is_nested_router(router):
            # NestedSimpleRouter уже содержит полный путь
            if prefix:
                # Если есть префикс, добавляем его
                return [
                    re_path(
                        f'{prefix}/',
                        include(router.urls),
                    )
                ]
            else:
                # Без префикса - используем как есть
                return [
                    re_path(
                        r'',
                        include(router.urls),
                    )
                ]
        else:
            # Обычный роутер
            if prefix:
                return [
                    re_path(
                        f'{prefix}/',
                        include((router.urls, basename), namespace=basename),
                    )
                ]
            else:
                # Роутер без префикса
                return [
                    re_path(
                        r'',
                        include((router.urls, basename), namespace=basename),
                    )
                ]

    def _get_viewset_urls(self, prefix: str, viewset: Any, basename: str) -> \
    list[Any]:
        """
        Генерирует URL паттерны для ViewSet'а.

        Args:
            prefix: URL префикс
            viewset: ViewSet класс
            basename: Базовое имя

        Returns:
            Список URL паттернов
        """
        ret = []
        lookup = self.get_lookup_regex(viewset)
        routes = self.get_routes(viewset)

        if routes is None:
            return ret

        for route in routes:
            # Только действия, которые существуют в ViewSet
            mapping = self.get_method_map(viewset, route.mapping)
            if not mapping:
                continue

            # Строим URL паттерн
            regex = route.url.format(
                prefix=prefix,
                lookup=lookup,
                trailing_slash=self.trailing_slash,
            )

            # Убираем лишний слэш в начале если нет prefix
            if not prefix and regex.startswith('^/'):
                regex = f'^{regex[2:]}'

            # Инициализируем kwargs для view
            initkwargs = route.initkwargs.copy()
            initkwargs.update({
                'basename': basename,
                'detail': route.detail,
            })

            # Создаем view и URL паттерн
            view = viewset.as_view(mapping, **initkwargs)
            name = route.name.format(basename=basename)
            ret.append(re_path(regex, view, name=name))

        return ret

    def _handle_unknown_type(self, prefix: str, obj: Any, basename: str,
                             ret: list[Any]) -> None:
        """
        Обрабатывает неизвестный тип объекта.

        Args:
            prefix: URL префикс
            obj: Неизвестный объект
            basename: Базовое имя
            ret: Список для добавления URL паттернов
        """
        print(f"Warning: Unknown type for '{prefix}': {type(obj)}")

        # Пытаемся обработать как ViewSet
        try:
            if hasattr(obj, 'as_view'):
                viewset_urls = self._get_viewset_urls(prefix, obj, basename)
                ret.extend(viewset_urls)
                print(f"Successfully processed '{prefix}' as ViewSet")
        except Exception as e:
            print(f"Error processing '{prefix}': {e}")

    def get_routes(self, viewset: Any) -> list[Any] | None:
        """
        Получает маршруты для ViewSet'а.

        Args:
            viewset: ViewSet для получения маршрутов

        Returns:
            Список маршрутов или None для роутеров
        """
        # Для роутеров не генерируем маршруты
        if self._is_router(viewset):
            return None

        # Для ViewSet'ов используем стандартную логику
        return super().get_routes(viewset)

    def get_api_root_view(self, api_urls: list[Any] | None = None) -> type[
        APIView]:
        """
        Возвращает корневое API view с поддержкой вложенных роутеров.

        Args:
            api_urls: Список URL паттернов

        Returns:
            Класс корневого view
        """
        api_root_dict = OrderedDict()
        list_name = self.routes[0].name

        for prefix, viewset_or_router, basename in self.registry:
            if self._is_router(viewset_or_router):
                # Для роутеров создаем ссылку на их корневое view
                if hasattr(viewset_or_router, 'root_view_name'):
                    root_view_name = viewset_or_router.root_view_name
                else:
                    root_view_name = 'api-root'

                if prefix:
                    api_root_dict[prefix] = f'{basename}:{root_view_name}'
                # Пропускаем роутеры без префикса в корневом view
            elif self._is_viewset(viewset_or_router):
                # Для ViewSet'ов используем стандартную логику
                if prefix:  # Показываем только ViewSet'ы с префиксом
                    api_root_dict[prefix] = list_name.format(basename=basename)

        return self.APIRootView.as_view(api_root_dict=api_root_dict)

    def get_lookup_regex(self, viewset, lookup_prefix='') -> str:

        try:
            return super().get_lookup_regex(viewset, lookup_prefix=lookup_prefix)
        except Exception:
            # Fallback для нестандартных ViewSet'ов
            return r'(?P<pk>[^/.]+)'


def enhanced_reverse(
    viewname: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    request: Any = None,
    format: str | None = None,
    **extra: Any,
) -> str:
    """
    Улучшенная функция reverse с автоматическим namespace.

    Аналогична django.urls.reverse, но автоматически пытается
    добавить namespace если обычный reverse не работает.

    Args:
        viewname: Имя view для reverse
        args: Позиционные аргументы
        kwargs: Именованные аргументы
        request: HTTP запрос для получения полного URL
        format: Формат ответа
        **extra: Дополнительные параметры

    Returns:
        URL строка

    Raises:
        NoReverseMatch: Если URL не может быть найден
    """
    if format is not None:
        kwargs = kwargs or {}
        kwargs['format'] = format

    try:
        url = django_reverse(viewname, args=args, kwargs=kwargs, **extra)
    except NoReverseMatch as exception:
        # Пытаемся добавить namespace из request
        if request and hasattr(request, '_request'):
            resolver_match = getattr(request._request, 'resolver_match', None)
            if (resolver_match and
                hasattr(resolver_match, 'namespace') and
                resolver_match.namespace):
                namespaced_viewname = f'{resolver_match.namespace}:{viewname}'
                try:
                    url = django_reverse(namespaced_viewname, args=args,
                                         kwargs=kwargs, **extra)
                except NoReverseMatch:
                    raise exception
            else:
                raise exception
        else:
            raise exception

    if request:
        return request.build_absolute_uri(url)
    return url


reverse._reverse = enhanced_reverse


class CustomAPIRootView(APIRootView):
    """Кастомное корневое API view."""

    __doc__ = 'Enhanced API Root View'
    name = 'API'

    def get_view_name(self) -> str:
        """Возвращает имя view."""
        return str(self.name)