import logging
from datetime import datetime
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.db import IntegrityError
from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import (
    APIException, ValidationError, PermissionDenied,
    NotFound, MethodNotAllowed, ParseError,
    AuthenticationFailed, NotAuthenticated,
    Throttled, UnsupportedMediaType
)
import uuid


class BlogAPIException(APIException):
    """
    Базовое исключение для Blog API
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Произошла ошибка сервера'
    default_code = 'server_error'

    def __init__(self, detail=None, code=None, status_code=None):
        super().__init__(detail, code)
        if status_code:
            self.status_code = status_code


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Кастомный обработчик исключений для стандартизации ответов
    """
    # Сначала вызываем стандартный обработчик DRF
    response = drf_exception_handler(exc, context)

    # Получаем дополнительную информацию о контексте
    view = context.get('view')
    request = context.get('request')

    # Генерируем уникальный ID ошибки для трекинга
    error_id = str(uuid.uuid4())[:8]

    # Логируем ошибку
    log_exception(exc, context, error_id)

    if response is not None:
        # Стандартизируем существующий ответ DRF
        custom_response_data = build_error_response(
            exc, response.data, request, error_id
        )
        response.data = custom_response_data

        # Добавляем дополнительные заголовки
        add_error_headers(response, exc)

    else:
        # Обрабатываем исключения, которые DRF не обработал
        if isinstance(exc, DjangoValidationError):
            response = handle_django_validation_error(exc, request, error_id)
        elif isinstance(exc, IntegrityError):
            response = handle_integrity_error(exc, request, error_id)
        elif isinstance(exc, Http404):
            response = handle_http_404(exc, request, error_id)
        else:
            response = handle_unexpected_error(exc, request, error_id)

    return response


def build_error_response(exc, original_data, request, error_id):
    """
    Строит стандартизированный ответ об ошибке
    """
    # Базовая структура ошибки
    error_response = {
        'error': True,
        'error_id': error_id,
        'timestamp': datetime.now().isoformat(),
        'path': request.path if request else None,
        'method': request.method if request else None,
    }

    # Определяем тип ошибки и добавляем специфическую информацию
    if isinstance(exc, ValidationError):
        error_response.update({
            'error_type': 'validation_error',
            'message': 'Ошибка валидации данных',
            'details': format_validation_errors(original_data),
            'code': getattr(exc, 'default_code', 'validation_error')
        })

    elif isinstance(exc, PermissionDenied):
        error_response.update({
            'error_type': 'permission_denied',
            'message': str(exc.detail) if hasattr(exc,
                                                  'detail') else 'Доступ запрещен',
            'code': getattr(exc, 'default_code', 'permission_denied'),
            'help': 'Проверьте права доступа или войдите в систему'
        })

    elif isinstance(exc, NotAuthenticated):
        error_response.update({
            'error_type': 'authentication_required',
            'message': 'Требуется аутентификация',
            'code': 'not_authenticated',
            'help': 'Передайте действительный токен аутентификации'
        })

    elif isinstance(exc, AuthenticationFailed):
        error_response.update({
            'error_type': 'authentication_failed',
            'message': str(exc.detail) if hasattr(exc,
                                                  'detail') else 'Ошибка аутентификации',
            'code': getattr(exc, 'default_code', 'authentication_failed'),
            'help': 'Проверьте корректность учетных данных'
        })

    elif isinstance(exc, NotFound):
        error_response.update({
            'error_type': 'not_found',
            'message': str(exc.detail) if hasattr(exc,
                                                  'detail') else 'Ресурс не найден',
            'code': getattr(exc, 'default_code', 'not_found'),
            'help': 'Проверьте правильность URL и параметров запроса'
        })

    elif isinstance(exc, MethodNotAllowed):
        error_response.update({
            'error_type': 'method_not_allowed',
            'message': f'Метод {exc.detail} не разрешен',
            'code': 'method_not_allowed',
            'allowed_methods': getattr(exc, 'detail', [])
        })

    elif isinstance(exc, Throttled):
        error_response.update({
            'error_type': 'rate_limit_exceeded',
            'message': 'Превышен лимит запросов',
            'code': 'throttled',
            'retry_after': exc.wait,
            'help': f'Повторите запрос через {exc.wait} секунд'
        })

    elif isinstance(exc, ParseError):
        error_response.update({
            'error_type': 'parse_error',
            'message': 'Ошибка парсинга данных',
            'code': 'parse_error',
            'details': str(exc.detail) if hasattr(exc, 'detail') else None,
            'help': 'Проверьте формат передаваемых данных'
        })

    elif isinstance(exc, UnsupportedMediaType):
        error_response.update({
            'error_type': 'unsupported_media_type',
            'message': 'Неподдерживаемый тип контента',
            'code': 'unsupported_media_type',
            'help': 'Проверьте заголовок Content-Type'
        })

    elif isinstance(exc, BlogAPIException):
        # Наши кастомные исключения
        error_response.update({
            'error_type': 'business_error',
            'message': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
            'code': getattr(exc, 'default_code', 'business_error'),
        })

        # Добавляем специфическую информацию для rate limit
    else:
        # Общая ошибка
        error_response.update({
            'error_type': 'api_error',
            'message': str(original_data.get('detail', 'Произошла ошибка API')),
            'code': getattr(exc, 'default_code', 'api_error')
        })

    return error_response


def format_validation_errors(validation_errors):
    """
    Форматирует ошибки валидации в понятный вид
    """
    if isinstance(validation_errors, dict):
        formatted_errors = {}
        for field, errors in validation_errors.items():
            if isinstance(errors, list):
                formatted_errors[field] = [str(error) for error in errors]
            else:
                formatted_errors[field] = [str(errors)]
        return formatted_errors
    elif isinstance(validation_errors, list):
        return [str(error) for error in validation_errors]
    else:
        return [str(validation_errors)]


def add_error_headers(response, exc):
    """
    Добавляет дополнительные заголовки к ответу об ошибке
    """
    if isinstance(exc, Throttled):
        response['Retry-After'] = exc.wait

    # Добавляем заголовок для CORS
    response['Access-Control-Expose-Headers'] = 'Retry-After'


def handle_django_validation_error(exc, request, error_id):
    """
    Обработка Django ValidationError
    """
    logger.warning(f"Django validation error [{error_id}]: {str(exc)}")

    return Response({
        'error': True,
        'error_id': error_id,
        'error_type': 'validation_error',
        'message': 'Ошибка валидации данных',
        'details': exc.message_dict if hasattr(exc, 'message_dict') else [
            str(exc)],
        'code': 'django_validation_error',
        'timestamp': datetime.now().isoformat(),
        'path': request.path if request else None,
    }, status=status.HTTP_400_BAD_REQUEST)


def handle_integrity_error(exc, request, error_id):
    """
    Обработка ошибок целостности БД
    """
    logger.error(f"Database integrity error [{error_id}]: {str(exc)}")

    # Определяем тип ошибки целостности
    error_message = str(exc).lower()
    if 'unique' in error_message or 'duplicate' in error_message:
        message = 'Объект с такими данными уже существует'
        code = 'duplicate_entry'
        status_code = status.HTTP_409_CONFLICT
    elif 'foreign key' in error_message:
        message = 'Нарушение связей между объектами'
        code = 'foreign_key_violation'
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        message = 'Нарушение целостности данных'
        code = 'integrity_error'
        status_code = status.HTTP_400_BAD_REQUEST

    return Response({
        'error': True,
        'error_id': error_id,
        'error_type': 'integrity_error',
        'message': message,
        'code': code,
        'help': 'Проверьте уникальность данных и корректность ссылок',
        'timestamp': datetime.now().isoformat(),
        'path': request.path if request else None,
    }, status=status_code)


def handle_http_404(exc, request, error_id):
    """
    Обработка 404 ошибок
    """
    logger.warning(
        f"HTTP 404 error [{error_id}]: {request.path if request else 'Unknown path'}")

    return Response({
        'error': True,
        'error_id': error_id,
        'error_type': 'not_found',
        'message': 'Запрашиваемый ресурс не найден',
        'code': 'not_found',
        'help': 'Проверьте правильность URL',
        'timestamp': datetime.now().isoformat(),
        'path': request.path if request else None,
    }, status=status.HTTP_404_NOT_FOUND)


def handle_unexpected_error(exc, request, error_id):
    """
    Обработка неожиданных ошибок
    """
    logger.error(f"Unexpected error [{error_id}]: {str(exc)}", exc_info=True)

    return Response({
        'error': True,
        'error_id': error_id,
        'error_type': 'server_error',
        'message': 'Внутренняя ошибка сервера',
        'code': 'internal_server_error',
        'help': 'Обратитесь к администратору системы',
        'timestamp': datetime.now().isoformat(),
        'path': request.path if request else None,
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def log_exception(exc, context, error_id):
    """
    Логирование исключений с контекстом
    """
    view = context.get('view')
    request = context.get('request')

    # Собираем контекстную информацию
    log_context = {
        'error_id': error_id,
        'exception_type': type(exc).__name__,
        'view': f"{view.__class__.__module__}.{view.__class__.__name__}" if view else None,
        'action': getattr(view, 'action', None) if view else None,
        'user': str(request.user) if request and hasattr(request,
                                                         'user') else None,
        'path': request.path if request else None,
        'method': request.method if request else None,
        'ip': get_client_ip(request) if request else None,
    }

    # Уровень логирования в зависимости от типа ошибки
    if isinstance(exc, (ValidationError, PermissionDenied, NotFound,
                        NotAuthenticated)):
        logger.warning(f"API warning [{error_id}]: {str(exc)}",
                       extra=log_context)
    elif isinstance(exc, BlogAPIException):
        logger.error(f"Business logic error [{error_id}]: {str(exc)}",
                     extra=log_context)
    else:
        logger.error(f"API error [{error_id}]: {str(exc)}", extra=log_context,
                     exc_info=True)


def get_client_ip(request):
    """
    Получение IP-адреса клиента
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip