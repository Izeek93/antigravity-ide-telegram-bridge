<div align="center">

# 🛰 Antigravity IDE Telegram Bridge
### *Двусторонний агентный мост между Telegram и Antigravity IDE*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![CUDA Acceleration](https://img.shields.io/badge/CUDA-Enabled-76B900.svg?style=flat&logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-zone)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue.svg?style=flat)](https://github.com/)
[![Version](https://img.shields.io/badge/release-v1.0.0--MVP-green.svg?style=flat)](https://github.com/Izeek93/antigravity-ide-telegram-bridge/releases)

---

**Antigravity IDE Telegram Bridge** — это автономная система двусторонней синхронизации активной сессии разработчика в **Antigravity IDE** с мессенджером **Telegram**. Включает гибкий голосовой ввод/вывод (STT/TTS), прямой опрос квот моделей по защищенному RPC, мониторинг 1M контекстного окна, захват экранов и автоматический контроль памяти.

</div>

---

## 🌟 Ключевые возможности

```
                                  ┌──────────────────────────────┐
                                  │   Telegram App (Пользователь) │
                                  └──────────────┬───────────────┘
                                                 │ 🎙 Голос / 💬 Текст / 📸 Фото
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        🛰 ANTIGRAVITY IDE TELEGRAM BRIDGE                              │
│                                                                                        │
│  ┌────────────────────────┐   ┌────────────────────────┐   ┌────────────────────────┐  │
│  │ 🎙 Pluggable STT Engine│   │ 🗣 Pluggable TTS Engine│   │ ⏳ Live RPC Quota Probe│  │
│  │ (Faster-Whisper / API) │   │ (Local / Cloud TTS)    │   │ (LanguageServer gRPC)  │  │
│  └────────────────────────┘   └────────────────────────┘   └────────────────────────┘  │
│                                                                                        │
│  ┌────────────────────────┐   ┌────────────────────────┐   ┌────────────────────────┐  │
│  │ 📸 Desktop Screenshot  │   │ 📚 1M Context Tracker  │   │ 🛡 Auto-Idle Watchdog  │  │
│  │ (Multi-monitor capture)│   │ (Active Token Usage)   │   │ (VRAM & RAM Optimizer) │  │
│  └────────────────────────┘   └────────────────────────┘   └────────────────────────┘  │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │ ⚡ FIFO Queue & Loopback RPC
                                         ▼
                                  ┌──────────────────────────────┐
                                  │   Antigravity IDE Backend    │
                                  │ (Google AI Pro Active Session│
                                  └──────────────────────────────┘
```

### 1. 🎙 Модульный голосовой стек (Pluggable Audio Pipeline)
- **STT (Распознавание речи):** Автоматическая расшифровка голосовых сообщений из Telegram через локальный `Faster-Whisper` (GPU / CPU) или облачные провайдеры.
- **TTS (Синтез речи):** Модульный голосовой движок с поддержкой локальных моделей синтеза речи, Edge-TTS или системных генераторов.
- **Чистый текстовый режим:** Возможность работы без аудио — исключительно через текстовые и графические сообщения.

### 2. ⏳ Живой опрос квот Antigravity IDE (Live RPC Quotas)
- Прямое подключение к локальному процессу `LanguageServerService` (`language_server_windows_x64.exe`) по защищенному gRPC/HTTPS протоколу.
- **5-часовое скользящее окно моделей:** точный процент остатка и расхода для Gemini и Claude/GPT в реальном времени.
- **Таймер сброса:** отображение точного обратного отсчёта и местного времени восстановления лимитов.

### 3. 📚 Мониторинг 1M Context Window (Контекстного окна)
- Автоматический подсчёт занятых токенов в активной сессии диалога IDE.
- Прозрачный контроль расхода миллионного контекста (занято / свободно / процент).

### 4. 📸 Захват рабочего стола и обмен файлами
- Команда `/screen` мгновенно делает снимок активного рабочего стола (с поддержкой мультимониторных конфигураций) и отправляет фото в Telegram.
- Приём скриншотов и документов из Telegram прямо в рабочее пространство IDE.

### 5. 🛡 Авто-контроль памяти (Auto-Idle Watchdog)
- Автоматическое отслеживание простоя фоновых процессов генерации.
- Полная выгрузка тяжелых локальных сервисов и освобождение VRAM при неактивности.

---

## 📋 Команды нативного меню `[ Menu ☰ ]`

| Команда | Описание |
| :--- | :--- |
| **`/screen`** | 📸 Мгновенный захват и отправка скриншота рабочего стола |
| **`/voice`** | 🔊 Включение / отключение голосового сопровождения ответов |
| **`/limits`** | ⏳ Живые квоты Antigravity IDE, 1M контекст и телеметрия GPU/RAM |
| **`/tasks`** | ⚙️ Фоновые задачи, терминалы и процессы |
| **`/status`** | 📊 Статус подключения моста к активной сессии IDE |
| **`/help`** | ℹ️ Справка и документация возможностей |

---

## 🚀 Быстрый старт и установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/Izeek93/antigravity-ide-telegram-bridge.git
cd antigravity-ide-telegram-bridge
```

### 2. Создание виртуального окружения и установка зависимостей

```bash
python -m venv venv
venv\Scripts\activate     # На Windows
# source venv/bin/activate # На Linux

pip install -r requirements.txt
```

### 3. Настройка конфигурации (`.env`)

Скопируйте шаблон `.env.example` в `.env` и укажите токен вашего бота:

```bash
cp .env.example .env
```

Отредактируйте `.env`:
```ini
# Токен бота от @BotFather:
TG_BOT_TOKEN="YOUR_BOT_TOKEN"

# Безопасность: ваш логин и ID в Telegram:
ALLOWED_USERNAMES="your_username"
ALLOWED_CHAT_IDS="123456789"
```

### 4. Запуск моста

```bash
python tg_bridge.py
```

После запуска в Telegram станет доступно нативное меню `[ Menu ☰ ]`, а любые текстовые и голосовые сообщения будут мгновенно передаваться агенту в Antigravity IDE!

---

## 🔒 Безопасность (Zero-Leak Policy)

Проект строго следует политике конфиденциальности:
- Все персональные данные, ключи и токены хранятся исключительно в изолированном локальном файле `.env`.
- Файл `.env` внесён в `.gitignore` и **никогда не попадает в Git**.
- В репозитории публикуются только обезличенные шаблоны (`.env.example`, `secrets.example.json`).

---

## 💖 Поддержка проекта

Если вам нравится **Antigravity IDE Telegram Bridge**, вы можете поддержать разработку и автора:

- 🚀 **[Boosty (Эксклюзивный контент и донаты)](https://boosty.to/izeek)**
- 💳 **[ЮMoney (Прямой перевод по СБП и картам)](https://yoomoney.ru/to/410011192281528)**

---

## 📄 Лицензия

MIT License © 2026. Разработано для экосистемы Google Antigravity.
