# Contributing to Lapka 🐾

We love contributions! Whether it's fixing bugs, improving documentation, or proposing new features.

## Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/lapka.git
   cd lapka
   ```
3. **Install in editable mode**:
   ```bash
   pip install -e .
   ```
4. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/amazing-feature
   ```

## Development Workflow

- Run the CLI mode to test basic logic:
  ```bash
  python -m lapka --cli
  ```
- Run the Telegram bot (requires token):
  ```bash
  export LAPKA_TELEGRAM_TOKEN="your_token"
  python -m lapka --telegram
  ```

## Code Style

- We use **Python 3.11+**.
- Keep it simple. **Less code is better.**
- Follow PEP 8 (mostly).
- Run `mypy` or `ruff` if you can (we'll add CI for validaiton later).

## Pull Request Process

1. Push your branch to GitHub:
   ```bash
   git push origin feature/amazing-feature
   ```
2. Open a **Pull Request** against the `main` branch of `make-ai-great-again/lapka`.
3. Provide a clear description of what you changed.
4. Wait for review! We try to review PRs quickly.

## Philosophy 🧘

- **Minimal dependencies**: Don't add heavy libraries unless absolutely necessary.
- **Context is expensive**: Optimize prompts and token usage.
- **Agentic**: Tools should be robust and self-correcting.

## Reporting Bugs

Please open an Issue on GitHub with:
- Steps to reproduce
- Expected behavior
- Logs (if relevant)
