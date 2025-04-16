# Project Progress

## Reference Specification
*   **Main Spec:** [../questforge-spec.md](../questforge-spec.md) - Details the current architecture, models, and remaining work phases.

## Completed Features & Documentation

*   **Core Framework:** Flask app factory, DB models (User, Template, Game, Campaign, GameState), Migrations, Auth basics, Blueprints, Config.
*   **Template System:** Template model, CRUD UI & backend logic.
*   **Game Creation Foundation:** Game/Campaign/GameState models, creation wizard UI, backend logic for template selection/initial record creation, basic AI interaction points in Template model.
*   **Real-time Foundation:** SocketIO initialized, basic service structure.
*   **Memory Bank & Spec:** All core Memory Bank docs updated, new `template_creation_process.md` added, `questforge-spec.md` created/updated.
*   **Phase 1: Template Redesign & Character Definition (Completed):**
    *   Modified `Template` model (`questforge/models/template.py`) with new guidance fields, removed old fields.
    *   Modified `TemplateForm` (`questforge/views/forms.py`) to match the new model.
    *   Modified Template Views (`questforge/views/template.py`) to handle the new form/model.
    *   Added `character_description` column to `GamePlayer` model (`questforge/models/game.py`).
    *   Generated and applied database migration (`migrations/versions/06ff0646a8b4_...`).
    *   Updated Lobby UI (`questforge/templates/game/lobby.html`) with character description textareas and save buttons.
    *   Implemented character save logic via `handle_update_character_description` in `questforge/services/socket_service.py`.
*   **API Cost Tracking:**
    *   Created `ApiUsageLog` model and database table.
    *   Implemented logic in services (`ai_service`, `campaign_service`, `socket_service`) to record API call details (model, tokens) and calculate cost based on `config.py` pricing.
    *   Updated UI (`list.html`, `play.html`, `home.html`) to display cost information and configured model.

## Remaining Work (Phased Approach from Spec)

**Phase 2: Delayed Campaign Generation**

*   Modify the `/api/games/create` endpoint to only create the basic `Game` record.
*   Implement the delayed campaign generation logic, triggered by a SocketIO event (e.g., `start_game`) from the lobby.
*   This logic will fetch the template, gather all player character descriptions from `game_players`, call `build_campaign_prompt` and `ai_service.generate_campaign`, and save the returned campaign structure and initial state.

**Phase 3: AI Prompt Refinement**

*   Revise `build_campaign_prompt` to use the new template fields and player character descriptions to request a comprehensive campaign structure from the AI.

**Phase 4: Testing & Deployment Prep (Medium Priority - Ongoing)**

*   Write unit & integration tests for new components (character definition, delayed generation).
*   Write tests for SocketIO handlers & gameplay.
*   Increase overall test coverage.
*   Verify/test production configuration (Gunicorn, Systemd, Nginx).

## Known Issues & Potential Enhancements (Post-MVP)

*   AI response validation needs further enhancement (content quality).
*   General UI/UX improvements.
*   See `questforge-spec.md` for more potential enhancements.

## Documentation Status
*   `questforge-spec.md` is the primary specification.
*   Memory Bank documents (`projectbrief.md`, `activeContext.md`, `progress.md`, process docs, `.clinerules`) are aligned with the spec.
