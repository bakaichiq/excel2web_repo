# Установка и запуск

## Docker (рекомендуется)

```bash
docker compose -f infra/docker-compose.yml up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (Swagger: /docs)

## Миграции

Если база создана без alembic, сначала проставьте ревизию:

```bash
docker compose -f infra/docker-compose.yml run --rm -w /app backend \
  env PYTHONPATH=/app alembic stamp 0001_init
```

Затем примените миграции:

```bash
docker compose -f infra/docker-compose.yml run --rm -w /app backend \
  env PYTHONPATH=/app alembic upgrade head
```

## Переменные окружения

- `BACKEND_URL` — адрес backend для proxy (frontend).  
  В docker‑compose по умолчанию: `http://backend:8000`.
- `NEXT_PUBLIC_API_BASE` — адрес backend для прямых ссылок (экспорт).  
  По умолчанию: `http://localhost:8000`.

## Демоданные

Если `SEED_DEMO=true`, создаются:
- пользователь `admin / admin123`
- проект `PRJ-1`

## Типовые проблемы

1) **Internal Server Error в UI**  
   Проверьте логи backend и авторизацию (401).

2) **Proxy не находит backend**  
   Убедитесь, что `BACKEND_URL` задан в `infra/docker-compose.yml`.
