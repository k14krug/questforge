# QuestForge Project Intelligence

This file captures key patterns, decisions, and project-specific knowledge for the QuestForge application. It serves as a learning journal to help maintain consistency and apply best practices throughout development.

## Architecture & Patterns

- **Flask Application Factory Pattern**: Used in `questforge/__init__.py` to create modular, testable Flask applications.
- **Flask Blueprints**: Organized by domain (Auth, Game, Template, Campaign API) for better code organization and maintainability.
- **SQLAlchemy ORM**: Used with Flask-Migrate for database modeling and migrations.
- **Flask-SocketIO**: Implements real-time communication between players and the game state.
- **Service Layer Pattern**: Business logic is encapsulated in service modules (`ai_service.py`, `campaign_service.py`, `game_state_service.py`, `socket_service.py`).
- **State Management**: `GameState` model tracks turn-by-turn state changes during gameplay.
- **Delayed Campaign Generation**: Campaign creation is triggered via SocketIO from the lobby (Phase 2 focus).
- **Model-View Separation**: Templates (Jinja2) handle presentation, while Python handles business logic.

## Development Workflow & Conventions

- **Memory Bank System**: Used for context persistence (`memory-bank/` directory).
- **Specification-Driven**: `questforge-spec.md` serves as the primary specification document.
- **Phased Development**: Work is organized into phases as outlined in `progress.md`.
- **API Cost Tracking**: `ApiUsageLog` model and service integration tracks AI API usage and costs.
- **AI Response Validation**: `Template.validate_ai_response` ensures AI responses meet expected format/structure.
- **Database Migrations**: All schema changes are managed through Flask-Migrate.
- **Logging**: Structured logging with rotation is used throughout the application.

## Tooling & Configuration

- **Tech Stack**: Python Flask, SQLAlchemy, Flask-SocketIO, Jinja2, MySQL/MariaDB.
- **Log Rotation**: Configured with `RotatingFileHandler` in `questforge/__init__.py` (5MB limit, 3 backups).
- **External AI Integration**: Implemented in `ai_service.py` with configurable model selection.
- **Pricing Configuration**: `OPENAI_PRICING` dictionary in `config.py` for cost calculation.
- **Development Server**: Flask development server for local testing.
- **Production Deployment**: Configured for Gunicorn with Nginx (see `gunicorn_config.py`).
