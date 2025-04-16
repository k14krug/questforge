# QuestForge System Specification

## Overview

QuestForge is a Flask-based web application designed to provide a personalized, AI-driven tabletop role-playing game experience. The application allows a game creator to define a high-level template (genre, theme, core conflict) and then have the AI generate a complete campaign structure, including locations, characters, and plot points. Players can then join the game and experience a unique adventure guided by the AI Game Master. The core intent is to minimize the amount of pre-defined content required from the game creator, empowering the AI to take on the bulk of the world-building and narrative design. The system is intended for deployment on a home network (e.g., Raspberry Pi).

## Core Requirements

### Intent and Design Goals
*   **AI-Driven Storytelling:** The core intent is for the AI to generate the majority of the campaign content (locations, characters, plot points, objectives) based on high-level guidance from the template and player choices. The game creator should not need to pre-define detailed campaign elements.
*   **Personalized Experience:** The AI should tailor the campaign to the specific players who join the game, incorporating their character descriptions and choices into the generated world.
*   **Easy Template Creation:** Creating new templates should be simple and intuitive, focusing on high-level creative concepts rather than technical details.
*   **Enjoyable Gameplay:** The game experience should be engaging and immersive, with the AI acting as a responsive and creative Game Master.

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
- Players can define their characters with a description before the game starts.

### Game System
- Template-based game creation (simplified templates with high-level guidance)
- AI-generated campaign structure (generated *after* players join, incorporating their character details)
- Structured narrative with clear objectives and conclusion (AI-driven)
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
    *   Simplified template structure with high-level guidance fields (genre, core conflict, etc.)
    *   AI interaction configuration (`ai_service_endpoint`, retry logic fields)
4.  **Character Definition Module:** (Lobby UI, `socket_service.py`, `game_players` table)
    *   Allows players to define their character descriptions before the game starts.
    *   Stores character descriptions in the `game_players` table.
5.  **Campaign Structure Module:** (`questforge/models/campaign.py`, `questforge/services/campaign_service.py`, `questforge/views/campaign_api.py`)
    *   Stores AI-generated campaign structure (`Campaign` model).
    *   Narrative arc with key plot points
    *   Objectives and conclusion conditions
    *   Key locations and characters
    *   Service layer for managing campaign creation/updates.
    *   API endpoint for interactions (e.g., fetching questions).
6.  **Game State Tracking Module:** (`questforge/models/game_state.py`, `questforge/services/game_state_service.py`)
    *   Tracks progress, locations, characters, decisions etc. within a specific game instance.
    *   Service layer for managing state updates.
7.  **AI Game Master Module:** (`questforge/services/ai_service.py`)
    *   Service stub/structure exists.
    *   Integration with LLM API.
    *   Context management and prompt building logic for maintaining narrative coherence
8.  **Real-time Communication Module:** (`questforge/extensions/socketio.py`, `questforge/services/socket_service.py`)
    *   WebSocket connections via Flask-SocketIO.
    *   Service layer for handling SocketIO events (join, actions, updates).
    *   Room-based messaging (using game IDs) with gameplay broadcast.
9.  **Main Application Routes:** (`questforge/views/main.py`)
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

### Templates (`template.py`) - *Planned Redesign*
```python
class Template(db.Model):
    __tablename__ = 'templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text) # Optional: General description
    category = db.Column(db.String(50)) # Optional: For organization

    # High-level Guidance Fields (New)
    genre = db.Column(db.String(50), nullable=False) # Required: e.g., Fantasy, Sci-Fi
    core_conflict = db.Column(db.Text, nullable=False) # Required: Short description of main goal/problem
    theme = db.Column(db.String(50)) # Optional: e.g., Exploration, Mystery
    desired_tone = db.Column(db.String(50)) # Optional: e.g., Humorous, Grim
    world_description = db.Column(db.Text) # Optional: Freeform notes on world, magic, tech
    scene_suggestions = db.Column(db.Text) # Optional: Ideas for scene types/encounters
    player_character_guidance = db.Column(db.Text) # Optional: Notes for players creating characters
    difficulty = db.Column(db.String(20)) # Optional: e.g., Easy, Medium, Hard
    estimated_length = db.Column(db.String(20)) # Optional: e.g., Short, Medium, Long

    # Removed Fields:
    # question_flow = db.Column(db.JSON)
    # default_rules = db.Column(db.JSON)
    # initial_state = db.Column(db.JSON)

    # AI Interaction Fields (Kept)
    ai_service_endpoint = db.Column(db.String(255)) # Endpoint for AI service
    ai_last_response = db.Column(db.JSON) # For debugging/logging
    ai_last_updated = db.Column(db.DateTime) # For debugging/logging
    ai_retry_count = db.Column(db.Integer, default=0) # For debugging/logging
    ai_max_retries = db.Column(db.Integer, default=3) # Configurable retry logic
    ai_retry_delay = db.Column(db.Integer, default=5) # Configurable retry logic (seconds)

    # Metadata (Kept)
    version = db.Column(db.String(20), default='1.0.0')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships: user (creator), games
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
    # Fields to store AI-generated structure
    campaign_data = db.Column(db.JSON, nullable=True) # General structure/narrative generated by AI
    objectives = db.Column(db.JSON, nullable=True) # AI-generated objectives
    conclusion_conditions = db.Column(db.JSON, nullable=True) # AI-generated conclusion conditions
    key_locations = db.Column(db.JSON, nullable=True) # AI-generated key locations
    key_characters = db.Column(db.JSON, nullable=True) # AI-generated key characters
    major_plot_points = db.Column(db.JSON, nullable=True) # AI-generated plot points
    possible_branches = db.Column(db.JSON, nullable=True) # AI-generated narrative branches
    # Relationships: game, game_state
```

### GameStates (`game_state.py`)
```python
class GameState(db.Model):
    __tablename__ = 'game_states'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), unique=True) # One-to-one with Game
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id')) # Link to the structure
    current_location = db.Column(db.String(100), nullable=True) # Set by AI initially and during play
    state_data = db.Column(db.JSON, nullable=True) # Stores current player-specific state (health, inventory, etc.) - Set by AI
    game_log = db.Column(db.Text, nullable=True) # Narrative log
    available_actions = db.Column(db.JSON, nullable=True) # List of actions provided by AI
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
*   `game_players`: Links `games` and `users` (Many-to-Many). **Planned Addition:** `character_description` (Text) column to store player-defined character details for the specific game.


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

## Workflow Processes (Planned Redesign)

*   **Template Creation:** User defines high-level guidance (genre, core conflict, etc.) via simplified form. See `memory-bank/template_creation_process.md` (Needs update).
*   **Game Creation & Start:**
    1.  User selects a template and provides a game name.
    2.  `/api/games/create` endpoint creates the basic `Game` record and associates the creator.
    3.  User is redirected to the game lobby (`/game/<id>/lobby`).
    4.  Other players join the lobby.
    5.  Players define their character descriptions in the lobby UI (saved via SocketIO to `game_players` table).
    6.  Players indicate readiness.
    7.  When all players are ready, a "Start Game" event is triggered (e.g., via SocketIO).
    8.  Backend handler fetches the template, player descriptions.
    9.  Backend calls `ai_service.generate_campaign` with template info and character descriptions.
    10. AI generates campaign structure (objectives, locations, characters, plot points) and initial game state (description, starting state, initial goals).
    11. Backend saves the generated `Campaign` and `GameState` records.
    12. Backend redirects players or sends event to load the main game interface (`/game/<id>/play`).
*   **Gameplay Process:**
    1. UI displays current game state (narrative log, available actions) from `GameState`.
    2. Player submits action via UI -> SocketIO event.
    3. `socket_service.py` receives action.
    4. Backend builds context using `context_manager.py` (including relevant `Campaign` data and `GameState`).
    5. Backend calls `ai_service.get_response` with context and player action.
    6. AI returns narrative outcome, state changes, and new available actions.
    7. `game_state_service.py` updates `GameState` based on AI response.
    8. `socket_service.py` broadcasts update (narrative, new actions) to game room.
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

## Remaining Work (Redesign Plan)

This section outlines the necessary work based on the planned redesign to shift towards AI-driven campaign generation.

**Phase 1: Template Redesign & Character Definition**
*   **Template Model (`models/template.py`):**
    *   Remove `question_flow`, `default_rules`, `initial_state` columns.
    *   Add new columns for high-level guidance: `genre` (String, nullable=False), `core_conflict` (Text, nullable=False), `theme` (String), `desired_tone` (String), `world_description` (Text), `scene_suggestions` (Text), `player_character_guidance` (Text), `difficulty` (String), `estimated_length` (String).
*   **Template Form (`views/forms.py`):**
    *   Remove fields corresponding to removed model columns.
    *   Add new fields (SelectField for dropdowns, TextAreaField, StringField) for the new guidance attributes. Define choices for dropdowns.
*   **Template Views (`views/template.py`):**
    *   Update `create_template` and `edit_template` to handle the new form fields and save/update the corresponding `Template` model attributes.
*   **Database Migration:**
    *   Generate and apply a database migration to reflect the changes to the `templates` table. (Note: Existing template data will be lost or require manual migration).
*   **Character Definition - Database:**
    *   Add `character_description` (Text, nullable=True) column to the `game_players` association table (requires defining or modifying the association object/table definition if not using standard many-to-many).
    *   Generate and apply a database migration for this change.
*   **Character Definition - Lobby UI (`templates/game/lobby.html`):**
    *   Add an editable text area for each player in the lobby.
    *   Implement logic (likely in the view rendering the lobby or via JavaScript) to pre-fill the text area for Player 1 ("Human Male") and Player 2 ("Human Female") if their description is currently null/empty.
    *   Add a "Save Description" button or similar mechanism for each player's text area.
*   **Character Definition - Backend (`socket_service.py`):**
    *   Create a new SocketIO event handler (e.g., `handle_update_character_description`).
    *   This handler receives `game_id`, `user_id`, and `description`.
    *   It finds the corresponding `GamePlayer` record and updates the `character_description` field.
    *   Consider emitting an update to the lobby to show saved descriptions to others.

**Phase 2: Delayed Campaign Generation**
*   **Game Creation API (`views/campaign_api.py` or `views/game.py`):**
    *   Modify the `/api/games/create` endpoint (or equivalent) to *only* create the `Game` record and the creator's `GamePlayer` association. Remove the call to `campaign_service.create_campaign`.
*   **Lobby Logic (`socket_service.py` / `game.py`):**
    *   Implement logic triggered when all players are ready (e.g., a `handle_start_game` SocketIO event).
    *   This handler needs to:
        *   Verify all players are ready.
        *   Fetch the `Template` associated with the `Game`.
        *   Fetch all `GamePlayer` records for the game to get `user_id` and `character_description`.
        *   Call a (potentially new or modified) function in `campaign_service.py` to orchestrate the AI generation, passing the template and player character data.
*   **Campaign Service (`campaign_service.py`):**
    *   Modify or create a function (e.g., `generate_campaign_structure`) that:
        *   Receives the `Template` object and a list/dict of player character descriptions.
        *   Calls `prompt_builder.build_campaign_prompt` (which needs revision - see Phase 3) with this data.
        *   Calls `ai_service.generate_campaign` with the generated prompt.
        *   Parses the AI response containing the generated campaign structure (objectives, locations, characters, plot points, initial state, etc.).
        *   Creates and saves the `Campaign` record, populating its fields with the AI-generated data.
        *   Creates and saves the initial `GameState` record based on the AI response.
        *   Handles potential errors during AI generation.
*   **Game Start Flow:**
    *   After successful campaign/state generation, the backend needs to notify players (e.g., via SocketIO emit or redirect) to load the main game interface (`/game/<id>/play`).

**Phase 3: AI Prompt Refinement**
*   **Prompt Builder (`utils/prompt_builder.py`):**
    *   Revise `build_campaign_prompt`:
        *   Remove reliance on removed template fields (`question_flow`, `default_rules`, `initial_state`).
        *   Incorporate the new high-level template fields (`genre`, `core_conflict`, `theme`, `desired_tone`, `world_description`, `scene_suggestions`, `player_character_guidance`, `difficulty`, `estimated_length`).
        *   Incorporate the list of player character descriptions.
        *   Update the "Your Task" section to explicitly request the AI to generate the full campaign structure (objective, locations, characters, plot points) in addition to the initial scene/state/goals.
        *   Define the expected JSON output structure from the AI clearly in the prompt.
    *   Review `build_response_prompt` to ensure it uses the AI-generated `Campaign` data effectively via the context provided by `context_manager.py`.
*   **Context Manager (`utils/context_manager.py`):**
    *   Review `build_context` to ensure it fetches and includes relevant parts of the *AI-generated* `Campaign` data (objectives, locations, characters, plot points) when building context for in-game actions.

**Phase 4: Testing & Deployment Prep (Medium Priority - Ongoing)**
*   **Testing:**
    *   Write unit tests for new/modified model methods and service functions.
    *   Write integration tests for the new template structure and creation/editing flow.
    *   Write integration tests for the character description saving mechanism.
    *   Write integration tests for the delayed campaign generation flow (mocking AI).
    *   Write tests for updated SocketIO event handlers.
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
*   Support for joining games already in progress.
*   Pre-made character selection system within templates.

## MySQL-specific Considerations

*   JSON field handling (Serialization/deserialization).
*   UTF-8 character set configuration.
