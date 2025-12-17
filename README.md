# Async Calculation Service

Django-сервис для асинхронных расчетов значений артефактов в заявках.

## Запуск

### Локально
```bash
pip install -r requirements.txt
python manage.py runserver 8000
```

### Docker
```bash
docker build -t async-calc-service .
docker run -p 8000:8000 async-calc-service
```

## API

### POST /api/calculate
Запускает расчет с задержкой 5-10 секунд и отправляет результат обратно в Go-сервис.

**Request:**
```json
{
  "request_id": 123,
  "artifact_id": 456,
  "quantity": 10,
  "callback_url": "http://localhost:8081/api/trade-analysis/123/entries/456/result"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Calculation completed after 7s",
  "calculated_value": 1234.56
}
```

## Токен авторизации

Сервис использует токен `async-calc-token-8bytes` в заголовке `X-API-Token` при отправке результатов обратно в Go-сервис.
