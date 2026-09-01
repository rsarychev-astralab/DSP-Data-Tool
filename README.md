# DSP Data Tool

Веб-сервис: выгрузка партнёра-DSP (Excel) → шаблон загрузки в реестр. Второй шаг по желанию: сопоставление договоров с внутренней базой (ERID, ID в OTM / OZON / VK).

**Прод:** https://dsp.belyauskas.ru:8443 (порт в адресе обязателен)

Как пользоваться интерфейсом: [ИНСТРУКЦИЯ.md](ИНСТРУКЦИЯ.md). Как выкатывать: [DEPLOY.md](DEPLOY.md).

Репозитории (один `main`):

- GitLab: https://git.astralab.ai/astra-dev/dsp-data-agent
- GitHub: https://github.com/rsarychev-astralab/DSP-Data-Tool

## Что внутри

- FastAPI + UI в `static/`
- YAML-профили маппинга в `app/profiles/`
- Справочник DSP и шаблон в `Справка/` и `Шаблон/`
- Прокси DaData (проверка юрлиц) и подсказки адресов ФЛ

## Локальный запуск

Python 3.13, зависимости из `requirements.txt`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # ключ DaData по желанию
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Открыть http://127.0.0.1:8000

Через Docker:

```bash
bash deploy/run-docker.sh
```

По умолчанию контейнер слушает http://127.0.0.1:5555 и монтирует каталог `Исходные данные`.

## Переменные окружения

См. `.env.example`. Файл `.env` в git не попадает.

| Переменная | Зачем |
|---|---|
| `DADATA_API_KEY` | вкладка проверки юрлиц |
| `DSP_BASIC_USER` + `DSP_BASIC_PASSWORD` | HTTP Basic на проде |
| `DSP_ENABLE_DOCS` | `/docs`, по умолчанию выключен |

На `127.0.0.1` / `localhost` пароль не спрашивается, даже если переменные заданы. На проде (хост не loopback) без логина закрыто всё, кроме `/health`.

В `.env` для Docker пароль **без кавычек**: `docker --env-file` берёт кавычки как часть значения. Если в пароле есть `#`, это нормально, пока строка не начинается с `#`.

## Тесты

```bash
pip install -r requirements-dev.txt
pytest -q
```

В GitLab CI тот же `pytest` на каждый push в ветку и на merge request.

## Деплой на свой VPS

Сервер тянет GitLab, затем:

```bash
git pull --ff-only origin main
bash deploy/run-docker.sh
```

Снаружи стоит nginx на `:8443`, контейнер на `127.0.0.1:5555`. Фрагмент nginx: `deploy/nginx-dsp.conf`.

GitHub Pages для этого репозитория не подходит: нужен Python и разбор `.xlsx`.
