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

**Feature: Narrative Guidance System (Completed)**
    *   Updated `prompt_builder.py` (`build_campaign_prompt`) for plot points with `description` and `required` flag.
    *   Updated `ai_service.py` (`generate_campaign`) to validate new plot point structure.
    *   Updated `models/game_state.py` to include `turns_since_plot_progress` in default `state_data`.
    *   Updated `socket_service.py` (`handle_player_action`) to:
        *   Track `turns_since_plot_progress`.
        *   Identify `next_required_plot_point`.
        *   Determine `is_stuck` status.
        *   Pass guidance parameters to `ai_service.get_response`.
        *   Process `achieved_plot_point` from AI, update `completed_plot_points` (now stores full objects), and reset `turns_since_plot_progress`.
    *   Updated `ai_service.py` (`get_response`) signature and logic to handle `is_stuck` and `next_required_plot_point`.
    *   Updated `context_manager.py` (`build_context`) to include "Current Objective/Focus".
    *   Updated `prompt_builder.py` (`build_response_prompt`) with new instructions for objective adherence, hints, and reporting `achieved_plot_point`.
    *   Updated `campaign_service.py` (`check_conclusion`) to pre-check completion of all `required` plot points.
    *   Created `memory-bank/narrative_guidance_implementation.md` and `memory-bank/narrative_guidance_plan.md`.

**Feature: Join Game Screen Shows All Games (Completed)**
    *   Modified `questforge/views/game.py` in `list_games` function to query all games instead of just 'active' ones.
    *   Updated `questforge/templates/game/list.html` to adjust the "no games available" message.

**Feature: Game Deletion from Join Game Screen (Completed)**
    *   Added `delete_game` route and function to `questforge/views/game.py` to handle game deletion (POST request).
        *   Ensures only the game creator can delete the game.
        *   Deletes the `Game` record and associated `Campaign`, `GameState`, `GamePlayer`, and `ApiUsageLog` records.
    *   Imported `GameState` model into `questforge/views/game.py`.
    *   Updated `questforge/templates/game/list.html` to include a "Delete" button for game creators.
        *   Button is part of a form that POSTs to the delete route.
        *   Includes a JavaScript confirmation dialog.
        *   Includes `csrf_token()` (resolved `UndefinedError` by passing `FlaskForm` instance from view).
        *   Creator comparison uses `game.creator.id`.

**Feature: Re-enter Completed Games from Join Game Screen (Completed)**
    *   Modified `questforge/templates/game/list.html` to change the linking logic for game names.
    *   Games with status 'completed' now link to the play view (`url_for('game.play', game_id=game.id)`), allowing users to review the game log and final state.
    *   This also applies to 'in_progress' games, while 'active' games link to the lobby. Other statuses remain non-clickable.

**Feature: Completed Game Badge Styling (Completed)**
    *   Modified `questforge/templates/game/list.html` to display a green badge (`bg-success`) for games with status 'completed'. Other statuses retain the default gray badge (`bg-secondary`).

## Remaining Work (Phased Approach from Spec)

**Phase 1: Template Redesign & Character Definition (Completed)**
*   (Details omitted for brevity - see above)

**Phase 2: Delayed Campaign Generation (Completed)**

*   **Modify Game Creation API:** **(Completed)** Updated the `/api/games/create-game` endpoint (`questforge/views/game.py`) to only create the basic `Game` and `GamePlayer` records, removing premature `Campaign` creation.
*   **Implement Lobby Start Logic:** **(Verified)** Confirmed the `handle_start_game` SocketIO event (`questforge/services/socket_service.py`) correctly triggers the campaign generation process.
*   **Implement Campaign Generation Service:** **(Verified)** Confirmed the service logic (`campaign_service.generate_campaign_structure`) correctly orchestrates AI interaction and saves the `Campaign` and initial `GameState`. No code changes were needed.
*   **Implement Game Start Flow:** **(Verified)** Confirmed the `handle_start_game` function in `socket_service.py` correctly emits the `game_started` event only after successful campaign generation. No code changes were needed.

**Phase 3: AI Prompt Refinement (Completed)**

*   **Revise AI Campaign Prompt:** **(Completed)** Updated `build_campaign_prompt` in `questforge/utils/prompt_builder.py` to better utilize `Template` fields (including `default_rules`), providing clearer instructions to the AI for generating more tailored campaign structures.
*   **Integrate Player Character Descriptions:** **(Completed)** Ensured `character_description` from `GamePlayer` is passed through the service layer (`socket_service` -> `campaign_service` -> `ai_service`) and incorporated into the `build_campaign_prompt` to influence AI generation (especially initial scene and plot points).

**Phase 4: Gameplay Enhancements (Completed)** (See [./phase-4-gameplay-enhancements.md](./phase-4-gameplay-enhancements.md) for details)

*   Implement Inventory Display on `play.html`. **(Completed)**
*   Add AI Prompt Guardrails to `build_response_prompt`. **(Completed)**
*   Implement Location History tracking and display. **(Completed)**
*   Implement Multiplayer Location Display. **(Completed)**
*   Enable Single-Player Mode. **(Completed)**

**Phase 5: Enhanced Game Creation (Completed)** (See [./phase-5-enhanced-game-creation.md](./phase-5-enhanced-game-creation.md) for details)

*   Allow game creators to add customizations (NPCs, locations, plot hooks, rules, exclusions) via UI (`game/create.html`). **(Completed)**
*   Allow game creators to override template details (genre, conflict, world, etc.) via UI (`game/create.html`). **(Completed)**
*   Store creator customizations in `Game.creator_customizations` (JSON field). **(Completed)**
*   Pass customizations and overrides through services (`socket_service`, `campaign_service`, `ai_service`) to prompt builder. **(Completed)**
*   Integrate customizations and overrides into `build_campaign_prompt` (`utils/prompt_builder.py`). **(Completed)**

**Feature: Character Naming System (Completed)**

*   Added `character_name` field to `GamePlayer` model and migrated DB.
*   Updated `lobby.html` UI and JS to handle name input.
*   Updated `socket_service.py` (`handle_update_character_details`) to save name and description.
*   Added `build_character_name_prompt` to `prompt_builder.py`.
*   Added `generate_character_name` method to `ai_service.py`.
*   Integrated AI name generation into `campaign_service.generate_campaign_structure`.
*   Updated `build_campaign_prompt` and `build_response_prompt` to use character names.
*   Updated `context_manager.build_context` to include player names/descriptions.
*   Updated `game.py` view (`play`) to fetch full player details.
*   Updated `play.html` JS to display character name (fallback to username).
*   Created `memory-bank/character_naming_system.md`.

**Feature: Narrative Guidance System (Completed)**
    *   (Details listed under "Completed Features & Documentation" above)

**Feature: ID-Based Plot Point System & Conclusion Handling (Completed)**
    *   **Core Logic:**
        *   Modified AI prompts (`prompt_builder.py`) for campaign generation and action responses to use/expect plot point IDs.
        *   Enhanced AI response validation (`ai_service.py`) to check for plot point IDs and uniqueness.
        *   Updated campaign generation (`campaign_service.py`) to auto-complete the first required plot point by ID.
        *   Updated conclusion checking logic (`campaign_service.py`) to verify required plot points by ID and evaluate `conclusion_conditions`.
        *   Updated AI context generation (`context_manager.py`) to include plot point IDs and `conclusion_conditions`.
        *   Updated action handling (`socket_service.py`) to identify the next required plot point by ID, process AI-reported completions by ID, merge AI state changes correctly into `state_data`, track `visited_locations`, and call `check_conclusion` after state updates.
        *   Improved error handling in `campaign_service.py` for AI service errors during campaign generation.
        *   Refined AI prompts (`prompt_builder.py`) to explicitly guide the AI on setting critical event flags based on `conclusion_conditions`.
    *   **Verification:**
        *   Thoroughly tested the implementation, confirming reliable game conclusion and AI flag setting.
    *   **UI Conclusion Handling (`questforge/static/js/socketClient.mjs`, `questforge/templates/game/play.html`):**
        *   Client-side JS listens for `game_concluded` event.
        *   Updates UI to "Status: Completed" (using `gameStatusDisplay` ID).
        *   Disables action input and button.
        *   Displays conclusion message.
    *   **Final Turn Presentation (`questforge/services/socket_service.py`):**
        *   On game conclusion, appends "** CAMPAIGN COMPLETE! **" to log.
        *   Sets available actions to `["Campaign Complete"]`.
        *   Emits modified `game_state_update` and `game_concluded` event.
        *   Updates game status in DB to 'completed'.
    *   **Memory Bank:** Plan file cleanup handled.

**Current Task: Game Screen Redesign (`play.html`)** (Low Priority - In Progress)

*   Consolidate Game Log & Narrative display.
*   Restructure right column with always-visible actions and tabs for secondary info (Status, Details).
    *   **NPC Details Display (Completed):** Added display of `campaign.key_characters` (NPCs and their attributes) to the "Details" tab in `questforge/templates/game/play.html`.
*   Display player names instead of IDs.
*   Relocate API cost display.
*   Apply subtle thematic styling.

**Phase 6: Testing & Deployment Prep** (Medium Priority - Next)

*   Write unit & integration tests for new components (Phases 1-5).
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
