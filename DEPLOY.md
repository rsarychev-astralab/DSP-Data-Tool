# Деплой с полной работоспособностью

GitHub Pages **не подходит**: нет Python и обработки `.xlsx`.

Нужен один сервис, где крутятся **и API, и интерфейс** (как на localhost). Репозиторий уже так устроен: `uvicorn app.main:app`.

## Рекомендация: Render.com (проще всего)

1. Залейте репозиторий на **GitHub** (`git push`).
2. [render.com](https://render.com) → **New → Web Service** → подключите репозиторий.
3. Render подхватит `render.yaml` или укажите вручную:
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health check:** `/health`
4. После деплоя откройте выданный URL — форма, преобразование и скачивание работают как локально.

**Ограничения free-тарифа:** сервис «засыпает» без запросов; первый запрос после сна — пауза ~30–60 с. Большие файлы (десятки тысяч строк) — обработка 10–60 s; укладывайтесь в таймаут платформы.

## Альтернативы (тоже полный стек)

| Платформа | Плюсы |
|-----------|--------|
| **Fly.io** | Docker, ближе к продакшену |
| **Railway** | Быстрый старт из GitHub |
| **Свой VPS** | `docker build` + `docker run -p 8000:8000` |

## Docker локально (проверка перед облаком)

```bash
cd "/Users/lucsijsotrudniknasvete/Documents/DSP Data Agent"
docker build -t dsp-transform .
docker run --rm -p 8000:8000 dsp-transform
```

Откройте http://127.0.0.1:8000

## GitHub Pages

Использовать только если позже вынесете фронт отдельно и подключите **внешний URL API** + CORS. Для «всё в одном» Pages не нужен.

## Что должно быть в git

Уже в репозитории: `app/`, `static/`, `Справка/DSP.xlsx`, `Шаблон/…xlsx`, `requirements.txt`.

Не нужны в git: выгрузки в `Исходные данные/`, результаты в `Результат обработки/` (см. `.gitignore`).
