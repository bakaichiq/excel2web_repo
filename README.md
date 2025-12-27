# Excel2Web ERP

Фаза 1: замена тяжёлой Excel‑модели веб‑системой **PostgreSQL + FastAPI + Celery + Next.js** с базовой аналитикой и управляемым импортом.

## Возможности

- Импорт Excel (ВДЦ, ГПР, Люди/Техника, БДР, БДДС)
- Версионные импорты и сравнение версий
- План/Факт и KPI, прогресс по группам
- БДР/БДДС и Manhours
- ГПР с диаграммой Ганта, зависимостями и критическим путём
- Ручной ввод факта и финансовых записей
- Роли пользователей и JWT‑аутентификация

## Быстрый старт (Docker)

```bash
docker compose -f infra/docker-compose.yml up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (Swagger: /docs)

Dev‑логин (если `SEED_DEMO=true`):
- `admin / admin123`

## Миграции

Если база уже создана без alembic:

```bash
docker compose -f infra/docker-compose.yml run --rm -w /app backend \
  env PYTHONPATH=/app alembic stamp 0001_init

docker compose -f infra/docker-compose.yml run --rm -w /app backend \
  env PYTHONPATH=/app alembic upgrade head
```

Если база новая:

```bash
docker compose -f infra/docker-compose.yml run --rm -w /app backend \
  env PYTHONPATH=/app alembic upgrade head
```

## Импорт Excel

1) В UI: Dashboard → **Импорт** → выбери Project ID → загрузи `.xlsx`  
2) Статус импорта появится в таблице.  
3) Каждый импорт хранится как версия (можно сравнивать).

Формат Excel описан в `docs/IMPORT_FORMAT.md`.

## Архитектура (кратко)

- `backend/app/services/etl/` — парсеры и загрузчик в БД
- `backend/app/services/reports/` — KPI и отчётные запросы
- `frontend/app/dashboard/*` — страницы дашбордов
- `infra/docker-compose.yml` — Postgres + Redis + backend + worker + frontend

## Документация

- `docs/ARCHITECTURE.md` — архитектура и слои
- `docs/SETUP.md` — локальный запуск и миграции
- `docs/IMPORT_FORMAT.md` — формат Excel для импорта
- `docs/VERSIONS.md` — версии импорта и сравнение
- `docs/ROADMAP.md` — фазы развития проекта
