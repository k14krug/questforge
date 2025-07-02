# Gemini Project Brief: QuestForge

This document provides instructions and context for the Gemini AI assistant to effectively contribute to the QuestForge project.

## 1. Project Overview

QuestForge is a web-based platform for creating and playing text-based role-playing games (RPGs). It features a dynamic story generation system that uses AI to create unique and engaging adventures for players. The platform allows users to create games, join existing games, and interact with the game world through a simple web interface.

## 2. Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Database:** Flask-SQLAlchemy (with SQLite)
- **Real-time Communication:** Flask-SocketIO
- **Authentication:** Flask-Login, Flask-Bcrypt
- **Key Libraries:**
    - `openai`: For AI-powered story generation.
    - `python-dotenv`: For managing environment variables.
    - `Flask-Migrate`: For database migrations.

## 3. Development Workflow

- **To run the application:** `python app.py`
- **To run tests:** `pytest`
- **To run linter:** `ruff check .`
- **To apply database migrations:** `flask db upgrade`

## 4. Key Files & Directories

- `app.py`: The main Flask application entry point.
- `config.py`: Contains application configuration settings.
- `database.py`: Sets up the database connection and SQLAlchemy instance.
- `models.py`: Defines the database schema and models (User, Game, etc.).
- `routes/`: Contains the Flask route definitions.
- `services/`: Houses business logic, such as `ai_service.py` and `game_state_service.py`.
- `static/`: Contains all static assets like CSS and JavaScript.
- `templates/`: Holds all Jinja2 HTML templates.

## 5. Coding Conventions & Style

- Follow PEP 8 for Python code.
- Use descriptive variable names.
- Keep functions small and focused on a single task.
- All new backend features should have corresponding tests.

## 6. Current Task: Display Active NPCs

**Objective:** Display the list of active NPCs from the `GameState` on the `play_page.html` for all players to see.

### Backend Plan:

1.  **Modify `games.py`:** The `/api/games/<int:game_id>/state` endpoint already retrieves the `GameState`. The `active_npcs` field is part of the `GameState.to_dict()` method, so no significant backend changes are needed here. The data is already available to the frontend.

### Frontend Plan:

1.  **Modify `play_page.html` & JavaScript:** The `play_page.html` already has a designated `<div id="npc-grid">`. The JavaScript on this page fetches the game state and calls a `updateCharacterGrids` function.

### Implementation Steps:

1.  **No changes needed in `routes/games.py`:** The `get_game_state` function already returns the full game state, including `active_npcs`.
2.  **Update JavaScript in `play_page.html`:**
    *   Locate the `updateCharacterGrids` function in the script block.
    *   This function already iterates through `npcs` and calls `createCharacterCard`.
    *   The `createCharacterCard` function needs to be adjusted to correctly access NPC attributes (e.g., `npc.name`, `npc.description`, `npc.portrait_url`).
    *   The `showCharacterDetails` function should be enhanced to display the full NPC details in a modal or a dedicated panel instead of a simple `alert()`.

This plan will guide the implementation of the NPC display feature. Let me know when you're ready to start making the changes.
