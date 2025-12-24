# Excel2Web ERP (MVP)

Цель: заменить тяжёлый Excel-файл веб‑системой **PostgreSQL + FastAPI + Celery + Next.js**, сохранив логику:
- ВДЦ (факт объёмов по дням)
- ГПР (планы по операциям и распределение по месяцам)
- Люди/Техника (manhours / машино‑часы)
- БДР (P&L)
- БДДС (Cash Flow)
- Дашборды: План/Факт, Прогресс, БДР, БДДС, Manhours
- Импорт Excel (идемпотентный), ручной ввод

## Быстрый старт (Docker)

```bash
cd infra
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (Swagger: /docs)

Dev‑логин (если `SEED_DEMO=true`):
- `admin / admin123`

## Импорт

1) В UI: Dashboard → **Импорт** → выбери Project ID → загрузи `.xlsx`  
2) Статус импорта появится в таблице.  
3) Импорт идемпотентный по hash файла: тот же файл не загрузится повторно.

## Архитектура (кратко)

- `backend/app/services/etl/` — парсеры и загрузчик в БД
- `backend/app/services/reports/` — KPI и отчётные запросы
- `frontend/app/dashboard/*` — страницы дашбордов
- `infra/docker-compose.yml` — Postgres + Redis + backend + worker + frontend

## Следующий шаг

- Гант по ГПР (операции)  
- Точный план по WBS/дисциплине (не «пропорционально факту»)  
- Поллинг/WS статуса импорта  
- Экспорт отчётов в PDF/XLSX по шаблонам заказчика
# excel2web_repo
