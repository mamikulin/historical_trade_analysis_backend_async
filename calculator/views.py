import json
import random
import time
import requests
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Настройка логирования
logger = logging.getLogger(__name__)

# Токен для авторизации при обратном вызове в Go-сервис
API_TOKEN = "async-calc-token-8bytes"

@csrf_exempt
@require_http_methods(["POST"])
def calculate_artifact_value(request):
    """
    Async расчет процента находок из региона для каждой м-м записи.
    Принимает: request_id, entries (список всех записей), callback_url_template
    Выполняет расчет с задержкой 5-10 секунд.
    Отправляет результаты обратно в Go-сервис для каждой записи.
    """
    try:
        data = json.loads(request.body)
        request_id = data.get('request_id')
        entries = data.get('entries', [])  # [{"artifact_id": 1, "production_center": "Рим", "quantity": 5}, ...]
        callback_url_template = data.get('callback_url')  # Шаблон с {request_id} и {artifact_id}
        
        if not request_id or entries is None or not callback_url_template:
            return JsonResponse({
                'status': 'error',
                'message': 'Missing required fields: request_id, entries, callback_url'
            }, status=400)
        
        # Если нет записей, возвращаем успех
        if not entries:
            return JsonResponse({
                'status': 'success',
                'message': 'Calculation completed for 0 entries'
            })
        
        # Запускаем расчет в фоне с задержкой 5-10 секунд
        delay = random.randint(5, 10)
        print(f'Начат расчет для заявки ID: {request_id} ({len(entries)} артефактов)')
        print(f'Задержка: {delay}s')
        time.sleep(delay)
        
        # Вычисляем общее количество всех артефактов
        total_quantity = sum(entry.get('quantity', 0) for entry in entries)
        
        if total_quantity == 0:
            return JsonResponse({
                'status': 'error',
                'message': 'Total quantity is zero'
            }, status=400)
        
        # Случайный успех/неуспех (50% вероятность) для всей заявки
        is_success = random.choice([True, False])
        print(f'Результат расчета: {"УСПЕХ" if is_success else "НЕУСПЕХ"}')
        
        # Список результатов для ответа
        results = []
        
        # Для каждой записи вычисляем процент находок из её региона
        for entry in entries:
            artifact_id = entry.get('artifact_id')
            production_center = entry.get('production_center')
            
            if not artifact_id or not production_center:
                continue
            
            # Считаем количество артефактов из того же региона
            region_quantity = sum(
                e.get('quantity', 0) for e in entries 
                if e.get('production_center') == production_center
            )
            
            if is_success:
                # Успех: вычисляем процент находок из региона
                calculated_value = round((region_quantity / total_quantity) * 100, 2)
            else:
                # Неуспех: процент = 0
                calculated_value = 0.0
            
            print(f'Артефакт {artifact_id}: количество из того же региона = {calculated_value:.2f}%')
            
            # Сохраняем результат для ответа
            results.append({
                'artifact_id': artifact_id,
                'production_center': production_center,
                'calculated_value': calculated_value,
                'success': is_success
            })
            
            # Формируем callback URL для конкретной записи
            callback_url = callback_url_template.replace('{request_id}', str(request_id)).replace('{artifact_id}', str(artifact_id))
            
            # Отправляем результат обратно в Go-сервис
            try:
                response = requests.put(
                    callback_url,
                    json={
                        'request_id': request_id,
                        'artifact_id': artifact_id,
                        'calculated_value': calculated_value
                    },
                    headers={'X-API-Token': API_TOKEN},
                    timeout=10
                )
                
                if response.status_code != 200:
                    print(f"Callback failed for artifact {artifact_id}: {response.status_code}")
            except Exception as callback_error:
                print(f"Callback error for artifact {artifact_id}: {callback_error}")
        
        print(f'Результаты отправлены для заявки ID: {request_id} ({len(entries)} артефактов)')
        
        return JsonResponse({
            'status': 'success',
            'message': f'Calculation completed after {delay}s for {len(entries)} entries',
            'overall_success': is_success,
            'results': results
        })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
