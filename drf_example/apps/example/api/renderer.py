import csv
import io
from rest_framework import renderers
from rest_framework.parsers import BaseParser


class CSVRenderer(renderers.BaseRenderer):
    """
    Рендерер для экспорта данных в CSV формат
    """
    media_type = 'text/csv'
    format = 'csv'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Рендерим данные в CSV формат
        """
        if not data:
            return ''

        # Получаем view и request из контекста
        view = renderer_context.get('view')
        request = renderer_context.get('request')

        # Создаем CSV в памяти
        csv_buffer = io.StringIO()

        # Определяем, это список объектов или один объект
        if isinstance(data, list):
            self._render_list_to_csv(data, csv_buffer)
        elif isinstance(data, dict):
            if 'results' in data:  # Paginated response
                self._render_list_to_csv(data['results'], csv_buffer)
            else:  # Single object
                self._render_object_to_csv(data, csv_buffer)

        return csv_buffer.getvalue().encode(self.charset)

    def _render_list_to_csv(self, data_list, csv_buffer):
        """Рендерим список объектов в CSV"""
        if not data_list:
            return

        # Получаем заголовки из первого объекта
        first_item = data_list[0]
        if isinstance(first_item, dict):
            fieldnames = self._get_csv_headers(first_item)

            writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
            writer.writeheader()

            for item in data_list:
                # Обрабатываем вложенные объекты
                flattened = self._flatten_dict(item)
                writer.writerow(flattened)

    def _render_object_to_csv(self, data, csv_buffer):
        """Рендерим один объект в CSV"""
        if isinstance(data, dict):
            flattened = self._flatten_dict(data)
            writer = csv.DictWriter(csv_buffer, fieldnames=flattened.keys())
            writer.writeheader()
            writer.writerow(flattened)

    def _get_csv_headers(self, obj):
        """Получаем заголовки CSV из объекта"""
        headers = []
        for key, value in obj.items():
            if isinstance(value, dict):
                # Для вложенных объектов создаем плоские заголовки
                for nested_key in value.keys():
                    headers.append(f"{key}__{nested_key}")
            elif isinstance(value, list) and value and isinstance(value[0],
                                                                  dict):
                # Для списков объектов берем ключи первого элемента
                for nested_key in value[0].keys():
                    headers.append(f"{key}__{nested_key}")
            else:
                headers.append(key)
        return headers

    def _flatten_dict(self, obj, parent_key='', sep='__'):
        """Превращаем вложенный словарь в плоский"""
        items = []
        for key, value in obj.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):
                items.extend(
                    self._flatten_dict(value, new_key, sep=sep).items())
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    # Берем только первый элемент для примера
                    items.extend(
                        self._flatten_dict(value[0], new_key, sep=sep).items())
                else:
                    # Список простых значений объединяем через запятую
                    items.append((new_key, ', '.join(map(str, value))))
            else:
                items.append((new_key, value))

        return dict(items)


class PlainTextParser(BaseParser):
    """
    Парсер для обработки plain text данных
    """
    media_type = 'text/plain'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Парсим plain text данные
        """
        return {
            'content': stream.read().decode('utf-8')
        }
