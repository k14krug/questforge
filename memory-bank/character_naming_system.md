# Character Naming System Implementation

## Goal

Implement a system where players can optionally provide a character name in the lobby. If left blank, the AI generates a name based on the player's character description. This definitive name (player-provided or AI-generated) will be stored, used consistently by the AI in prompts and responses, and displayed on the main game screen.

## Implementation Plan

1.  **Database Schema Update:**
    *   **Action:** Add a new nullable string field `character_name` to the `GamePlayer` model in `questforge/models/game.py`.
    *   **Details:** `character_name = db.Column(db.String(100), nullable=True)`
    *   **Migration:** Generate and apply a database migration using Flask-Migrate (`flask db migrate`, `flask db upgrade`).

2.  **Lobby User Interface & Logic:**
    *   **Action:** Modify the game lobby (`questforge/templates/game/lobby.html`) and the corresponding SocketIO handler.
    *   **UI:** Add a new text input field labeled "Character Name (Optional)" next to the existing "Character Description" textarea.
    *   **JavaScript:** Update the JavaScript in `lobby.html` associated with saving character details. When the save button is clicked, it should send both the `character_description` and the (potentially empty) `character_name` to the backend.
    *   **Backend (SocketIO):** Modify the existing `handle_update_character_description` event handler in `questforge/services/socket_service.py`. It should now accept both `description` and `name` in its payload and update both `character_description` and `character_name` fields on the relevant `GamePlayer` database record.

3.  **AI Name Generation Service:**
    *   **Action:** Create dedicated functions for generating character names via AI.
    *   **Prompt Builder (`questforge/utils/prompt_builder.py`):** Create a new function `build_character_name_prompt(description)`. This function will construct a concise prompt asking the AI to generate a single, suitable fantasy character name based *only* on the provided character description (e.g., "Generate a fantasy character name for: Tiny Elf with green skin").
    *   **AI Service (`questforge/services/ai_service.py`):** Create a new function `generate_character_name(description)`. This function will:
        *   Call `build_character_name_prompt`.
        *   Make a call to the AI service.
        *   Parse the AI response to extract only the generated name.
        *   Log the API usage/cost via `ApiUsageLog`.
        *   Return the generated name string.

4.  **Integrate Name Generation into Game Start:**
    *   **Action:** Modify the campaign generation process to include AI name generation if needed.
    *   **Location:** Update the `generate_campaign_structure` function within `questforge/services/campaign_service.py`.
    *   **Logic:** *Before* the main campaign generation prompt is built and sent to the AI:
        1.  Fetch all `GamePlayer` records associated with the current game.
        2.  Iterate through each `player`.
        3.  Check if `player.character_name` is empty or `None` AND `player.character_description` is not empty.
        4.  If both conditions are true, call the new `ai_service.generate_character_name(player.character_description)` function.
        5.  Save the returned name to `player.character_name`.
        6.  Commit these potential updates to the database (`db.session.commit()`) so the definitive names are available for the next step.

5.  **Ensure Consistent AI Name Usage:**
    *   **Action:** Update prompt builders to use the definitive `character_name`.
    *   **Prompt Builder (`questforge/utils/prompt_builder.py`):**
        *   Modify `build_campaign_prompt`: Ensure it fetches and includes the definitive `character_name` for *all* players involved in the game setup. Instruct the AI explicitly to refer to players by these names.
        *   Modify `build_response_prompt`: Ensure it fetches and includes the definitive `character_name` for the player taking the action, and potentially other players present in the current game state context. Instruct the AI explicitly to use these names in its narrative response.
    *   **Services (`campaign_service.py`, `socket_service.py`, `ai_service.py`):** Ensure the necessary player data (including the definitive `character_name`) is passed through the service layers to the prompt builders correctly.

6.  **Update Game Display:**
    *   **Action:** Modify the main game screen (`play.html`) and its backend view to display the character name.
    *   **Backend View (`questforge/views/game.py`):** Update the `play` view function. When fetching player data for the template context, ensure it retrieves the `GamePlayer` object (with `character_name`) and the associated `User` object (for `username` as a fallback).
    *   **Frontend Template (`questforge/templates/game/play.html`):** Update the JavaScript logic that renders the "Player Locations" list (or wherever player identities are displayed). For each player, display `player.character_name` if it has a value. If `player.character_name` is empty or null, display `player.user.username` as a fallback.

7.  **Documentation:**
    *   **Action:** Update Memory Bank files.
    *   **Files:**
        *   `memory-bank/activeContext.md`: Set this character naming task as the current focus.
        *   `memory-bank/progress.md`: Add this task under a new phase or as a distinct feature enhancement.
        *   `questforge-spec.md`: Update relevant sections describing `GamePlayer` and the game joining/start process.
        *   `.clinerules/clinerules.md`: Add notes about the new AI name generation pattern if applicable.
        *   `memory-bank/character_naming_system.md`: This file.
