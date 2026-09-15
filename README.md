# MetaLib VPN Bot

[![CI](https://github.com/Evr1kys/metalib-vpn-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/Evr1kys/metalib-vpn-bot/actions/workflows/ci.yml)

Сервис управления VPN-подписками. Репозиторий содержит backend, Telegram-бот, административную панель, mini app, worker и агент для VPN-серверов.

## Состав проекта

- `backend` — API, пользователи, подписки, платежи и управление серверами;
- `bot` — Telegram-интерфейс;
- `admin` — административная панель на Next.js;
- `miniapp` — Telegram Mini App;
- `worker` — фоновые задачи;
- `vpn-agent` — управление конфигурациями на VPN-серверах;
- `website` — публичные страницы сервиса.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Все ключи и пароли задаются через `.env`. Значения из `.env.example` предназначены только для локальной настройки.
