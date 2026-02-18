# Lapka 🐾 — Grand Roadmap

> "Автомат Калашникова в мире AI-агентов"
> 
> Ultra-lightweight AI agent. 10-100× меньше контекста чем OpenClaw/Claude Code/Codex.
> Python. Без тяжёлых зависимостей. OpenAI-compatible API.

**Repo:** https://github.com/make-ai-great-again/lapka

---

## Phase 1 — MVP Core ⚡ `v0.1`

**Цель:** Рабочий агент в терминале + Telegram, выполняющий bash-команды и работающий с файлами.

### Что входит:
- [ ] **Agent Loop** — цикл: user msg → LLM → tool call → execute → result → LLM → ... → final answer
- [ ] **LLM Client** — OpenAI-compatible API (OpenRouter, Ollama, LM Studio, vLLM, любой)
  - Конфигурируемый `base_url` + `api_key`
  - Два профиля моделей: `model` (умная) + `compact_model` (дешёвая для compaction)
- [ ] **Codex-style Context Compaction** — автоматическое сжатие контекста:
  - Полная история в памяти → при превышении порога → structured summary через дешёвую модель
  - Новая история: `[system_prompt, compaction_summary, last_3_messages]`
  - Нет "summaries of summaries" — всегда от полной истории
- [ ] **Tools:**
  - `bash` — выполнение shell-команд (subprocess, timeout, output truncation)
  - `read_file` — чтение файлов (с диапазоном строк)
  - `write_file` — запись файлов
  - `patch_file` — точечная правка (search/replace, экономия контекста)
  - `list_dir` — содержимое директории
  - `http_request` — HTTP запросы с truncation
- [ ] **CLI коннектор** — интерактивный терминал с ANSI-цветами
- [ ] **Telegram коннектор** — бот с allowlist, typing indicator, /reset, /status
- [ ] **Конфиг** — `~/.lapka/config.json` + env vars
- [ ] **Safety** — blocklist опасных команд, Telegram allowlist по user_id

### Ключевые решения Phase 1:
- **Python 3.11+**, только `httpx` + `python-telegram-bot`
- **Микро system prompt** (200-400 токенов)
- **Tool results truncation** (head+tail, max 2000 chars)
- **Estimated tokens** через `len(text) / 3.5`

---

## Phase 2 — Sessions & Memory 🧠 `v0.2`

**Цель:** Persistent sessions, multi-session, resume.

- [ ] Persistent sessions на диск (`~/.lapka/sessions/`)
- [ ] Resume session по ID (`lapka --session abc123`)
- [ ] Multi-session support (разные задачи параллельно)
- [ ] Session export/import (JSON)
- [ ] `/sessions` команда в Telegram (список активных сессий)
- [ ] Token usage statistics per session
- [ ] Auto-save checkpoint при каждом compaction

---

## Phase 3 — Computer Use 🖥️ `v0.3`

**Цель:** Агент видит экран и может кликать/печатать.

- [ ] `screenshot` tool — `screencapture` на macOS
- [ ] `click` tool — клик мышью через `cliclick` или AppleScript
- [ ] `type_text` tool — ввод текста через AppleScript
- [ ] `find_on_screen` tool — поиск элемента на скриншоте через vision-модель
- [ ] Интеграция vision-модели (screenshot → описание → action)
- [ ] macOS Accessibility API для точного управления UI

---

## Phase 4 — Swarm / Multi-Agent 🐝 `v0.4`

**Цель:** Координация нескольких агентов.

- [ ] Coordinator agent → worker agents
- [ ] Разные роли (coder, reviewer, researcher)
- [ ] Shared workspace через файловую систему
- [ ] Agent-to-agent messaging (через файлы-очереди)
- [ ] Parallel task execution
- [ ] Cost budget per swarm session

---

## Phase 5 — Integrations & Polish 🔌 `v0.5`

**Цель:** Коннекторы к сервисам, production-ready.

- [ ] **Docker sandbox** — опциональная изоляция выполнения команд
- [ ] **Webhook коннектор** — HTTP API для интеграций
- [ ] **GitHub integration** — PR review, issue triage
- [ ] **Cron / scheduled tasks** — периодические задачи
- [ ] **MCP support** — Model Context Protocol 
- [ ] **Skills/plugins** — загружаемые наборы инструментов
- [ ] **Web UI** — минимальный веб-интерфейс (single HTML file)

---

## Философия проекта

0. **Контекст — самый дорогой ресурс.** Каждая доработка должна оцениваться через призму: «сколько токенов это стоит?». System prompt ≤ 200 токенов. Tool results — compress. Промпты не растут — сжимаются.
1. **Меньше = лучше.** Каждый токен на счету. Каждая зависимость — обуза.
2. **OpenAI-compatible.** Один API для всех моделей: облако и локал.
3. **Compaction, не truncation.** Не теряем контекст — сжимаем его.
4. **Один файл = одна ответственность.** 15 файлов, каждый < 300 строк.
5. **Работает из коробки.** `pip install lapka && lapka --cli`

---

## Архитектура (кратко)

```
User (CLI/Telegram)
    │
    ▼
Agent Loop (agent.py)
    ├── LLM Client (llm.py) ──→ OpenAI-compatible API
    ├── Tool Registry (tools/)
    │   ├── bash.py
    │   ├── files.py
    │   └── http.py
    └── Context Manager (context.py)
        └── Codex-style Compaction
```
