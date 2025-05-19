# QuestForge Project Intelligence

This file captures key patterns, decisions, and project-specific knowledge for the QuestForge application. It serves as a learning journal to help maintain consistency and apply best practices throughout development.

## Architecture & Patterns

- **Flask Application Factory Pattern**: Used in `questforge/__init__.py` to create modular, testable Flask applications.
- **Flask Blueprints**: Organized by domain (Auth, Game, Template, Campaign API) for better code organization and maintainability.
- **SQLAlchemy ORM**: Used with Flask-Migrate for database modeling and migrations.
- **Flask-SocketIO**: Implements real-time communication between players and the game state.
- **Service Layer Pattern**: Business logic is encapsulated in service modules (`ai_service.py`, `campaign_service.py`, `game_state_service.py`, `socket_service.py`).
- **State Management**: `GameState` model tracks turn-by-turn state changes during gameplay. `GameState.state_data` is the primary store for dynamic game information.
- **Delayed Campaign Generation**: Campaign creation is triggered via SocketIO from the lobby (Phase 2 focus).
- **AI Character Name Generation**: Players can optionally provide a `character_name` in the lobby. If blank, the AI generates one based on `character_description` during campaign generation (`campaign_service.py`). The definitive name is used consistently in AI prompts and UI display.
- **Model-View Separation**: Templates (Jinja2) handle presentation, while Python handles business logic.
- **Multi-Stage Plot Point Completion Strategy (v2)**: Implemented to improve reliability of plot progression.
    - **Documentation**: See `memory-bank/plot_point_completion_strategy_v2.md`.
    - **Core Idea**: Decomposes plot point evaluation into multiple, focused stages.
    - **Atomic Plot Points**: Campaigns should be designed with granular, single-condition plot points.
    - **Stage 1 (Narrative & General State)**: `ai_service.get_response` (using `prompt_builder.build_response_prompt`) handles narrative generation and broad updates to `GameState.state_data` (location, inventory, NPC status, world objects). It *does not* determine plot completion.
    - **Stage 2 (System Plausibility Check)**: `socket_service.handle_player_action` performs a heuristic check (e.g., keyword matching) against pending atomic plot points to identify plausible candidates for completion based on Stage 1 output.
    - **Stage 3 (Focused AI Completion Analysis)**: For each plausible plot point, `ai_service.check_atomic_plot_completion` (using `prompt_builder.build_plot_completion_check_prompt`) makes a targeted AI call. This call receives the specific plot point, full current game state, player action, and Stage 1 narrative, returning a `completed: true/false` status and `confidence_score`.
    - **Stage 4 (System Aggregation & Update)**: `socket_service.handle_player_action` aggregates Stage 3 results. Plot points are marked completed in `GameState.state_data['completed_plot_points']` if `completed: true` and `confidence_score` meets a threshold (e.g., `PLOT_COMPLETION_CONFIDENCE_THRESHOLD` in config, default 0.75). `turns_since_plot_progress` is reset if a *newly completed required* plot point is confirmed.
    - **State-Aware Evaluation**: Plot completion is judged against the full, current `GameState.state_data`.
    - **Rich `state_data`**: Stage 1 AI is prompted for detailed updates to `GameState.state_data` to provide sufficient context for Stage 3.
- **Dynamic Gameplay Difficulty Adjustment**:
    - **Storage**: `Game.current_difficulty` stores the active difficulty ('Easy', 'Normal', 'Hard'), initialized at game creation and updatable by the creator during gameplay.
    - **UI Interaction**: A dropdown in `play.html` (visible to creator) allows changing `current_difficulty`. Changes emit a `change_difficulty` SocketIO event.
    - **Backend Update**: `socket_service.handle_change_difficulty` updates `Game.current_difficulty` in the database.
    - **AI Narrative Impact**: `socket_service.handle_player_action` passes `current_difficulty` to `ai_service.get_response`.
    - **Prompt Modification**: `prompt_builder.build_response_prompt` uses `current_difficulty` to append specific instructions to the AI, guiding its response style (e.g., forgiveness, strictness) to player actions, especially if deemed "unreasonable" by the AI. This affects narrative and consequences but not plot point completion logic.
    - **Distinction**: This dynamic adjustment is separate from the initial "Explicit Difficulty Prompting" used for campaign generation.
- **Historical Game Summary**:
    - **Purpose**: To provide the AI with a token-efficient, persistent memory of significant game events, improving narrative coherence over longer play sessions.
    - **Mechanism**:
        - `GameState.state_data['historical_summary']`: A list storing concise, AI-generated summaries of key events from each turn. Limited by `MAX_HISTORICAL_SUMMARIES` (from `config.py`).
        - `ai_service.generate_historical_summary()`: Called by `socket_service.handle_player_action()` after the Stage 1 AI response. Uses `OPENAI_MODEL_MAIN` and `prompt_builder.build_summary_prompt()` to create a single-sentence summary of the turn's player action, narrative result, and associated state changes.
        - `context_manager.build_context()`: Prepends the `historical_summary` (if available and not empty) as a numbered list to the context provided to the main game AI (`OPENAI_MODEL_LOGIC`), placing it before the "Recent Events (Game Log)" section.
    - **Impact**: Aims to give the AI a broader understanding of the game's progression beyond the immediate last few turns, potentially leading to more contextually aware and consistent narrative generation.

## Development Workflow & Conventions

- **Memory Bank System**: Used for context persistence (`memory-bank/` directory).
- **Specification-Driven**: `questforge-spec.md` serves as the primary specification document.
- **Phased Development**: Work is organized into phases as outlined in `progress.md`.
- **API Cost Tracking**: `ApiUsageLog` model and service integration tracks AI API usage and costs.
- **AI Response Validation**: `Template.validate_ai_response` ensures AI responses meet expected format/structure.
- **Database Migrations**: All schema changes are managed through Flask-Migrate.
- **Logging**: Structured logging with rotation is used throughout the application.
- **Explicit Difficulty Prompting (Initial Campaign Generation)**: The "difficulty" setting selected during game creation (from `Template` or `Game.template_overrides`) is translated into explicit instructions within the AI campaign generation prompt (`prompt_builder.build_campaign_prompt`). This aims to make the initial difficulty level impactful by guiding the AI on aspects like resource availability, challenge complexity, NPC behavior, and plot point clarity for the generated campaign. (Effectiveness to be validated through testing). This is distinct from the Dynamic Gameplay Difficulty Adjustment.

## Tooling & Configuration

- **Tech Stack**: Python Flask, SQLAlchemy, Flask-SocketIO, Jinja2, MySQL/MariaDB.
- **Log Rotation**: Configured with `RotatingFileHandler` in `questforge/__init__.py` (5MB limit, 3 backups).
- **External AI Integration**: Implemented in `ai_service.py` with configurable model selection.
- **Pricing Configuration**: `OPENAI_PRICING` dictionary in `config.py` for cost calculation.
- **Development Server**: Flask development server for local testing.
- **Production Deployment**: Configured for Gunicorn with Nginx (see `gunicorn_config.py`).
