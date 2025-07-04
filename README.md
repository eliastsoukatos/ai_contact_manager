# AI Contact Manager

AI Contact Manager is a modern contact management toolkit designed for sales and growth teams. It combines a polished desktop interface with powerful AI services to streamline lead enrichment, outreach automation and CRM integration.

## Key Features

- **Smart CSV Imports** – Quickly load large contact lists into a SQLite or PostgreSQL database with automatic header mapping and de-duplication.
- **AI Enrichment** – Generate company aliases and fill missing data using OpenAI, Groq or Perplexity models. Background threads keep the UI responsive during long runs.
- **Flexible Exports** – Filter, paginate and export exactly the contacts you need in clean CSV format.
- **Go Search Backend** – A lightweight Go service provides high‑performance querying so thousands of contacts remain snappy.
- **PyQt5 Interface** – A simple but effective desktop app for reviewing records, running prompts and adjusting settings.

## Integrations

AI Contact Manager works with a variety of external services and CRMs:

- **OpenAI / Groq / Perplexity** – Multiple LLM providers supported through pluggable APIs.
- **PostgreSQL** – Recommended production database with an included migration helper.
- **CSV/Excel** – Easily move data between your favorite sales tools.

## Tech Stack

- **Python** – Data processing, GUI and all automation scripts.
- **Go** – High‑speed search backend accessed over HTTP.
- **PyQt5** – Cross‑platform desktop UI.

## Benefits

- Consolidates contact data from disparate sources.
- Automates tedious enrichment work so reps can focus on selling.
- Keeps data fresh with timezone calculations and call‑time helpers.
- Works great as a companion to your existing CRM.

## Folder Overview

- `ai/` – AI prompts and LLM management helpers.
- `config/` – Simple persistent settings.
- `go_backend/` – Source code for the Go search service.
- `ui/` – Qt widgets and desktop interface pieces.
- `tests/` – Automated tests for core functionality.
- `docs/` – Project documentation.
- `examples/` – Usage examples.
- `data/` – Sample datasets.

## Getting Started

1. Install Python 3.8+, Go and PostgreSQL.
2. Install dependencies from `requirements.txt`.
3. Build and run the Go backend with `go build -o go_backend go_backend/main.go`.
4. Launch the desktop app using `python main.py`.
5. Explore the documentation in the `docs/` folder for more details.

## Contributing

Pull requests are welcome! Please see `CONTRIBUTING.md` for guidelines.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
