# QuestForge System Specification

## Overview

QuestForge is a Flask-based web application designed for hosting AI-powered, multiplayer text-based adventure games. It allows users to create, join, and play games where an AI acts as the game master, managing the narrative and responding to player actions in real-time. The system is intended for deployment on a home network (e.g., Raspberry Pi).

## Core Requirements

### Deployment Environment
- Raspberry Pi running on a home network 
- Python Flask application with virtualenvwrapper
- Systemd service management 
- Nginx as reverse proxy 
- Local DNS routing 
- MySQL/MariaDB database

### User Experience
- Multiple users can access the system simultaneously from different devices
- Users can create new games or join existing ones
- Real-time updates showing player actions and AI responses (Partially implemented, core gameplay loop pending)
- Persistent game state across sessions

### Game System
- Template-based game creation
- Customizable game parameters via template question flow
- AI-generated campaign structure (Integration pending)
- Structured narrative with clear objectives and conclusion (Dependent on AI generation)
- Persistent game state that maintains narrative coherence

## System Architecture

### Component Overview 

1.  **User Authentication Module:** (`questforge/views/auth.py`, `questforge/models/user.py`)
    *   User registration and login
    *   Session management 
    *   Password hashing (`questforge/extensions/bcrypt.py`)
2.  **Game Management Module:** (`questforge/views/game.py`, `questforge/models/game.py`)
    *   Game creation interface (from template)
    *   Game listing/joining 
    *   Game state persistence (`questforge/models/game_state.py`)
3.  **Template Module:** (`questforge/views/template.py`, `questforge/models/template.py`)
    *   CRUD operations for game templates
    *   Template-specific question flows (`question_flow` JSON field)
    *   Initial game state definition (`initial_state` JSON field)
    *   AI interaction configuration (`ai_service_endpoint`, retry logic fields)
4.  **Campaign Structure Module:** (`questforge/models/campaign.py`, `questforge/services/campaign_service.py`, `questforge/views/campaign_api.py`)
    *   Stores AI-generated campaign structure (`Campaign` model).
    *   Narrative arc with key plot points
    *   Objectives and conclusion conditions
    *   Key locations and characters
    *   Service layer for managing campaign creation/updates.
    *   API endpoint for interactions (e.g., fetching questions).
5.  **Game State Tracking Module:** (`questforge/models/game_state.py`, `questforge/services/game_state_service.py`)
    *   Tracks progress, locations, characters, decisions etc. within a specific game instance.
    *   Service layer for managing state updates.
6.  **AI Game Master Module:** (`questforge/services/ai_service.py`)
    *   Service stub/structure exists.
    *   Integration with LLM API.
    *   Context management and prompt building logic for maintaining narrative coherence
7.  **Real-time Communication Module:** (`questforge/extensions/socketio.py`, `questforge/services/socket_service.py`)
    *   WebSocket connections via Flask-SocketIO.
    *   Service layer for handling SocketIO events (join, actions, updates).
    *   Room-based messaging (using game IDs) with gameplay broadcast.
8.  **Main Application Routes:** (`questforge/views/main.py`)
    *   Handles general site navigation (home, about, etc.).

### Technical Architecture 

```
/questforge
  app.py             # Main application entry point using factory
  config.py          # Configuration settings
  manage.py          # Management script (Flask-Script/Flask-Cli) for migrations, etc.
  requirements.txt   # Project dependencies
  setup.py           # Python package setup
  .gitignore
  questforge-spec.md # This file (Application specification)
  /instance          # Instance folder for config, db etc.
  /memory-bank       # Project documentation and intelligence
    .clinerules
    activeContext.md
    game_creation_process.md
    progress.md
    projectbrief.md
    template_creation_process.md
    template_model.md
    # ... other context files
  /migrations        # Alembic/Flask-Migrate migration files
    versions/
    script.py.mako
    env.py
  /questforge        # Main application package
    __init__.py      # Application factory (create_app)
    /static
      /css
      /js
    /templates
      /auth
      /game
      /template
      /main
      /partials
      base.html
    /models          # SQLAlchemy models
      __init__.py
      user.py
      game.py
      template.py
      campaign.py
      game_state.py
    /views           # Flask Blueprints
      __init__.py    
      auth.py
      game.py
      template.py
      main.py         
      forms.py        # Flask-WTF forms
    /services        # Business logic and helpers
      __init__.py
      ai_service.py
      campaign_service.py
      game_state_service.py
      socket_service.py
    /extensions      # Flask extension initialization
      __init__.py
      database.py     
      socketio.py
      bcrypt.py
  /tests             # Unit and integration tests
    # ... test files
```

## Database Schema (Current Models - `questforge/models/`)

### Users (`user.py`)
```python
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) # Hashed via Bcrypt
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    # Relationships: templates (created_by), games (created_by), potentially game_players association
```

### Templates (`template.py`)
```python
class Template(db.Model):
    __tablename__ = 'templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    question_flow = db.Column(db.JSON) # Defines setup questions
    default_rules = db.Column(db.JSON) # Template-specific game rules (Usage TBD)
    initial_state = db.Column(db.JSON, nullable=False) # Structure for initial Campaign/GameState
    ai_service_endpoint = db.Column(db.String(255)) # Endpoint for AI service
    ai_last_response = db.Column(db.JSON) # For debugging
    ai_last_updated = db.Column(db.DateTime)
    ai_retry_count = db.Column(db.Integer, default=0)
    ai_max_retries = db.Column(db.Integer, default=3)
    ai_retry_delay = db.Column(db.Integer, default=5) # seconds
    version = db.Column(db.String(20), default='1.0.0')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    # Relationships: user (creator), games
    # Methods: generate_ai_content, validate_ai_response (as per template_model.md)
```

### Games (`game.py`)
```python
class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('templates.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending') # e.g., pending, active, completed
    # Relationships: template, creator (user), campaign, game_state, players (many-to-many via association table)
```

### Campaigns (`campaign.py`)
```python
class Campaign(db.Model):
    __tablename__ = 'campaigns'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), unique=True) # One-to-one with Game
    # Fields to store AI-generated structure, populated from Template.initial_state and AI response
    campaign_data = db.Column(db.JSON, nullable=False) # General structure/narrative
    objectives = db.Column(db.JSON, nullable=False)
    conclusion_conditions = db.Column(db.JSON, nullable=False)
    key_locations = db.Column(db.JSON, nullable=False)
    key_characters = db.Column(db.JSON, nullable=False)
    major_plot_points = db.Column(db.JSON, nullable=False)
    possible_branches = db.Column(db.JSON, nullable=False) # Narrative branches
    # Relationships: game, game_state
```

### GameStates (`game_state.py`)
```python
class GameState(db.Model):
    __tablename__ = 'game_states'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), unique=True) # One-to-one with Game
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id')) # Link to the structure
    current_location = db.Column(db.String(100), nullable=True)
    completed_objectives = db.Column(db.JSON, default='[]')
    discovered_locations = db.Column(db.JSON, default='[]')
    encountered_characters = db.Column(db.JSON, default='[]')
    completed_plot_points = db.Column(db.JSON, default='[]')
    current_branch = db.Column(db.String(50), default='main') # Tracks narrative branch
    player_decisions = db.Column(db.JSON, default='[]') # History of significant decisions
    campaign_complete = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationships: game, campaign
```

### Association Tables 
*   `game_players`: Links `games` and `users` (Many-to-Many)


## Module Breakdown (Flask Blueprints - `questforge/views/`)

*   **Auth Blueprint (`auth.py`):** Handles user login, registration, logout, profile (likely).
*   **Game Blueprint (`game.py`):** Handles game creation initiation, listing, joining, potentially viewing game state/history.
*   **Template Blueprint (`template.py`):** Handles CRUD operations for templates (create, list, view, edit).
*   **Campaign API Blueprint (`campaign_api.py`):** Handles API requests related to campaign generation (e.g., fetching question flow based on template, triggering AI generation via service).
*   **Main Blueprint (`main.py`):** Handles static pages and main navigation routes (e.g., home, about).

## Helper Modules (`questforge/services/`)

*   **AI Service (`ai_service.py`):** Intended to manage all interactions with the LLM API (generation, response processing). 
*   **Campaign Service (`campaign_service.py`):** Manages creation and updating of `Campaign` data, orchestrating calls to `ai_service.py`. 
*   **Game State Service (`game_state_service.py`):** Manages CRUD operations and updates for `GameState` records.
*   **Socket Service (`socket_service.py`):** Manages real-time communication logic, handling SocketIO events and broadcasting updates. 
*   **Context Manager (`context_manager.py`):** Manage AI context window.
    **Functions:**
    * `build_context(game_id, history_length=10)`: Build context for AI request
    * `compress_history(history)`: Compress long history entries
    * `prioritize_content(content, max_tokens)`: Prioritize important context elements
*   **Prompt Builder (`prompt_builder.py`):** Build prompts for different AI interactions
    **Functions:**
    - `build_campaign_prompt(template, inputs)`: Build prompt for campaign generation
    - `build_response_prompt(state, action)`: Build prompt for AI response
    - `build_analysis_prompt(state, action, response)`: Build prompt for state analysis

## Workflow Processes 

*   **Template Creation:** See `memory-bank/template_creation_process.md`.
*   **Game Creation:** See `memory-bank/game_creation_process.md`. 
*   **Gameplay Process:** 
    1. User joins game via UI.
    2. `socket_service.py` handles join event, adds user to game room.
    3. UI displays current game state (fetched via `game_state_service.py`).
    4. User submits action via UI -> SocketIO event.
    5. `socket_service.py` receives action.
    6. Action is processed (potentially involving `ai_service.py` to get response).
    7. `game_state_service.py` updates `GameState` based on action/response.
    8. `socket_service.py` broadcasts update (action, response, new state) to game room.
    9. UI updates for all players.
    10. Repeat.

## Flask Extensions and Dependencies

### Core Extensions
*   **Flask-SQLAlchemy:** (`questforge/extensions/database.py`)
*   **Flask-Migrate:** (`manage.py`, `/migrations`)
*   **Flask-SocketIO:** (`questforge/extensions/socketio.py`, `questforge/services/socket_service.py`)
*   **Flask-Login:** (`questforge/views/auth.py`)
*   **Flask-WTF:** (`questforge/views/forms.py`)
*   **Flask-Bcrypt:** (`questforge/extensions/bcrypt.py`)

### Additional Dependencies 
*   `python-dotenv`
*   `requests` (for AI API)
*   `eventlet` or `gevent` (for SocketIO async)
*   `pymysql` (or other MySQL adapter)
*   `cryptography`

## Development and Production Setup

*   Development setup using `flask run`, virtualenv, `.env`.
*   Production setup using Gunicorn, Systemd, Nginx, `.env.prod`.

## Security Considerations

*   Password hashing (Bcrypt confirmed).
*   CSRF protection (Flask-WTF).
*   Input validation (Partially implemented, needs expansion).
*   SQLAlchemy ORM helps prevent SQL injection.
*   Network security via Nginx (if deployed as planned).

## Remaining Work

This section outlines the necessary work to achieve a functional Minimum Viable Product (MVP) and potential future enhancements.

**Phase 1: Core AI & Campaign Generation (High Priority)**

*   **AI Service Implementation (`ai_service.py`):**
    *   Integrate with a specific LLM API (configure API keys, request/response handling). (Completed)
    *   Implement `generate_campaign` function: Build prompt (using `prompt_builder.py`), send to LLM, parse response into Campaign structure. (Completed)
    *   Implement `get_response` function: Build context-aware prompt (using `context_manager.py`), send player action to LLM, parse narrative response and identify state changes. (Completed)
    *   Implement robust error handling (API errors, timeouts, rate limits, content filtering). (Completed)
    *   Add logging for AI interactions. (Completed)
*   **Campaign Service Implementation (`campaign_service.py`):**
    *   Implement `create_campaign`: Orchestrate AI call via `ai_service.generate_campaign`, validate response (`Template.validate_ai_response`), save `Campaign` data. (Completed)
    *   Implement `update_campaign_state`: Apply state changes derived from AI responses or game logic to the `GameState`. (Completed)
    *   Implement `check_conclusion`: Logic to evaluate game end conditions based on `Campaign.conclusion_conditions`. (Completed)
*   **Prompt Engineering (`prompt_builder.py`):**
    *   Create `questforge/utils/prompt_builder.py`. (Completed)
    *   Implement `build_campaign_prompt`: Construct effective prompts for initial campaign generation. (Completed - Initial Implementation, ongoing refinement)
    *   Implement `build_response_prompt`: Construct prompts for in-game actions using history, state, and action. (Completed - Initial Implementation, ongoing refinement)
*   **Context Management (`context_manager.py`):**
    *   Create `questforge/utils/context_manager.py`. (Completed)
    *   Implement `build_context`: Gather relevant game data for the AI context window. (Completed - Initial Implementation, ongoing refinement)
    *   Implement strategies for context compression/prioritization if needed. (Completed - Initial Implementation, ongoing refinement)
*   **AI Response Validation (`Template.validate_ai_response`):**
    *   Enhance validation to ensure required campaign elements are present and correctly formatted in the AI response. (Completed)
*   **Game Creation Flow Integration (`game.py`, `campaign_api.py`):**
    *   Connect the game creation view to `campaign_service.create_campaign`. (Completed)
    *   Handle errors during AI generation and provide user feedback. (Completed)

**Phase 2: Core Gameplay Loop (High Priority)**

*   **Socket Service Enhancements (`socket_service.py`):**
    *   Implement `handle_action` event: Process player action, call `ai_service.get_response`. (Completed)
    *   Trigger `game_state_service.update_state` based on AI response/game logic. (Completed)
    *   Implement broadcasting (`emit`) of game updates (action, narrative, state changes) to the correct game room. (Completed)
    *   Refine player join/leave event handling and broadcasts. (Completed)
*   **Game State Service (`game_state_service.py`):**
    *   Ensure `update_state` correctly modifies `GameState` fields. (Completed)
    *   Ensure `get_state` provides necessary data for UI and AI context. (Completed)
*   **Gameplay UI (`templates/game/play.html`):**
    *   Develop the main game interface: Display narrative history, current status (location, objectives), player action input. (Completed)
    *   Implement JavaScript (`static/js/socketClient.js` or dedicated file) for SocketIO connection, sending actions, receiving/displaying updates. (Completed)
*   **Game View (`game.py`):**
    *   Implement route to render `play.html`, passing initial game data. (Completed)
    *   Finalize game joining logic and redirection to the play view. (Completed)

**Phase 3: Validation & UI Polish (Medium Priority)**

*   **Template Question Flow Validation:**
    *   Implement server-side validation of user answers during game creation against rules defined in the template. (Completed)
    *   Add clear UI feedback on `templates/game/create.html` for validation errors. (Completed)
*   **Template Management UI Polish:**
    *   Improve usability of `templates/template/list.html`, `create.html`, `edit.html`.
    *   Consider adding a user-friendly JSON editor/validator for template JSON fields.
*   **General UI/UX:**
    *   Review and improve user feedback (flash messages, loading indicators).
    *   Ensure consistent styling and basic responsiveness.

**Phase 4: Testing & Deployment Prep (Medium Priority - Ongoing)**

*   **Testing:**
    *   Write unit tests for `prompt_builder.py` and `context_manager.py`.
    *   Write integration tests for `ai_service.py` (using mocks).
    *   Write integration tests for the game creation flow (including mocked AI).
    *   Write tests for SocketIO event handlers and gameplay updates.
    *   Increase overall test coverage.
*   **Deployment:**
    *   Verify production configuration (`config.py`, `.env.prod`).
    *   Create and test Systemd service file.
    *   Create and test Nginx configuration.

**Potential Future Enhancements (Low Priority / Post-MVP):**

*   Template versioning system.
*   More sophisticated AI interactions (NPC memory, personalities).
*   Admin interface.
*   Image/Audio generation.
*   Advanced game mechanics (inventory, combat, skills).

## MySQL-specific Considerations

*   JSON field handling (Serialization/deserialization).
*   UTF-8 character set configuration.
