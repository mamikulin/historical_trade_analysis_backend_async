import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse


class CalculateArtifactValueTestCase(TestCase):
    """Тесты для эндпоинта расчета процента находок из региона"""
    
    def setUp(self):
        self.client = Client()
        self.url = '/api/calculate'
    
    @patch('calculator.views.requests.put')
    @patch('calculator.views.time.sleep')
    @patch('calculator.views.random.randint')
    @patch('calculator.views.random.choice')
    def test_successful_calculation_with_multiple_entries(self, mock_choice, mock_randint, mock_sleep, mock_put):
        """Тест успешного расчета для нескольких записей"""
        # Настройка моков
        mock_randint.return_value = 5  # Задержка 5 секунд
        mock_choice.side_effect = [True, False, True]  # Успех для 1-й и 3-й записи, неуспех для 2-й
        mock_sleep.return_value = None
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response
        
        # Тестовые данные: 3 записи, 2 из Рима (10 шт), 1 из Афин (5 шт)
        # Итого: 15 артефактов, Рим = 66.67%, Афины = 33.33%
        payload = {
            'request_id': 1,
            'entries': [
                {'artifact_id': 1, 'production_center': 'Рим', 'quantity': 7},
                {'artifact_id': 2, 'production_center': 'Афины', 'quantity': 5},
                {'artifact_id': 3, 'production_center': 'Рим', 'quantity': 3},
            ],
            'callback_url': 'http://localhost:8000/api/trade-analysis/{request_id}/entries/{artifact_id}/result'
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Проверки
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('3 entries', data['message'])
        
        # Проверяем, что было 3 callback вызова
        self.assertEqual(mock_put.call_count, 3)
        
        # Проверяем первый callback (artifact_id=1, Рим, успех)
        first_call = mock_put.call_args_list[0]
        self.assertIn('trade-analysis/1/entries/1/result', first_call[0][0])
        first_data = first_call[1]['json']
        self.assertEqual(first_data['artifact_id'], 1)
        self.assertEqual(first_data['calculated_value'], 66.67)  # (10/15)*100
        
        # Проверяем второй callback (artifact_id=2, Афины, неуспех)
        second_call = mock_put.call_args_list[1]
        second_data = second_call[1]['json']
        self.assertEqual(second_data['artifact_id'], 2)
        self.assertEqual(second_data['calculated_value'], 0.0)  # Неуспех
        
        # Проверяем третий callback (artifact_id=3, Рим, успех)
        third_call = mock_put.call_args_list[2]
        third_data = third_call[1]['json']
        self.assertEqual(third_data['artifact_id'], 3)
        self.assertEqual(third_data['calculated_value'], 66.67)  # (10/15)*100
    
    def test_missing_required_fields(self):
        """Тест с отсутствующими обязательными полями"""
        payload = {
            'request_id': 1,
            # Отсутствуют entries и callback_url
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Missing required fields', data['message'])
    
    def test_invalid_json(self):
        """Тест с некорректным JSON"""
        response = self.client.post(
            self.url,
            data='invalid json {{{',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Invalid JSON', data['message'])
    
    def test_empty_entries_list(self):
        """Тест с пустым списком записей"""
        payload = {
            'request_id': 1,
            'entries': [],
            'callback_url': 'http://localhost:8000/api/trade-analysis/{request_id}/entries/{artifact_id}/result'
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        # Пустой список - валидный запрос, просто ничего не обрабатывается
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('0 entries', data['message'])
    
    @patch('calculator.views.requests.put')
    @patch('calculator.views.time.sleep')
    @patch('calculator.views.random.randint')
    @patch('calculator.views.random.choice')
    def test_all_entries_from_same_region(self, mock_choice, mock_randint, mock_sleep, mock_put):
        """Тест когда все артефакты из одного региона (процент должен быть 100%)"""
        mock_randint.return_value = 7
        mock_choice.return_value = True  # Все успешные
        mock_sleep.return_value = None
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response
        
        payload = {
            'request_id': 2,
            'entries': [
                {'artifact_id': 10, 'production_center': 'Александрия', 'quantity': 3},
                {'artifact_id': 11, 'production_center': 'Александрия', 'quantity': 7},
                {'artifact_id': 12, 'production_center': 'Александрия', 'quantity': 5},
            ],
            'callback_url': 'http://localhost:8000/api/trade-analysis/{request_id}/entries/{artifact_id}/result'
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_put.call_count, 3)
        
        # Все записи должны иметь 100% (все из Александрии)
        for call in mock_put.call_args_list:
            call_data = call[1]['json']
            self.assertEqual(call_data['calculated_value'], 100.0)
    
    @patch('calculator.views.requests.put')
    @patch('calculator.views.time.sleep')
    @patch('calculator.views.random.randint')
    def test_callback_failure_doesnt_break_processing(self, mock_randint, mock_sleep, mock_put):
        """Тест что ошибка callback не прерывает обработку остальных записей"""
        mock_randint.return_value = 5
        mock_sleep.return_value = None
        
        # Первый callback упадет, остальные успешны
        mock_put.side_effect = [
            Exception("Network error"),
            MagicMock(status_code=200),
            MagicMock(status_code=200),
        ]
        
        payload = {
            'request_id': 3,
            'entries': [
                {'artifact_id': 20, 'production_center': 'Помпеи', 'quantity': 4},
                {'artifact_id': 21, 'production_center': 'Помпеи', 'quantity': 6},
                {'artifact_id': 22, 'production_center': 'Карфаген', 'quantity': 5},
            ],
            'callback_url': 'http://localhost:8000/api/trade-analysis/{request_id}/entries/{artifact_id}/result'
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Ответ все равно успешный
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_put.call_count, 3)
