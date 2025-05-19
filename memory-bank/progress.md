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

**Feature: Login with Username (Completed)**
    *   Modified `questforge/views/forms.py`: Changed `LoginForm` to use `username` field instead of `email`, updated validators.
    *   Modified `questforge/views/auth.py`: Updated `login` function to query `User` by `username` and adjusted flash message.
    *   Modified `questforge/templates/auth/login.html`: Updated login form to use `form.username`.

**Feature: UI Display Fixes for `play.html` (Completed)**
    *   **Objective:** Ensure correct and complete display of game log, player location, inventory, and visited locations.
    *   **`socketClient.mjs` Changes:**
        *   Centralized all UI update logic (game log, player/visited locations, inventory, actions, cost).
        *   Revised `updateGameLog` to target `gameStateVisualization`, render full history with styling, and show current location.
        *   Revised `updateGameState` to call all necessary helper functions for UI updates.
        *   Ensured helper functions (`updatePlayerLocationsDisplay`, `updateInventoryDisplay`, `updateVisitedLocationsDisplay`) correctly access data and update their respective elements.
    *   **`play.html` Changes:**
        *   Removed redundant UI update JavaScript functions from the inline script.
        *   Simplified inline script to primarily handle initialization and global variable setup (`window.currentUserId`, `window.playerDetails`).
    *   **Outcome:** Resolved issues of blank UI sections and incomplete game log.

**Feature: Plot Point Completion System Enhancement (v3 Strategy - Phases 1-3 Completed)**
*   **Objective:** Improve the plot point completion system to address issues identified during testing, evolving from v2.
*   **Documentation:** New strategy detailed in `memory-bank/plot_point_completion_strategy_v3.md`. (Supersedes v2 documentation).
*   **Phase 1: AI Service Enhancements (Completed)**
    *   Updated `build_plot_completion_check_prompt` (`prompt_builder.py`) with clearer criteria, examples, and emphasis on full game state for Stage 3 AI calls.
    *   Updated `build_response_prompt` (`prompt_builder.py`) for Stage 1 AI calls to encourage detailed state updates (NPCs, world objects, etc.) and ensure AI focuses on narrative and general state, not plot completion.
    *   Enhanced `ai_service.py`:
        *   `get_response` (Stage 1): Improved validation and augmentation of AI-provided `state_changes` (location, inventory, NPC status, world objects), ensuring robustness and fallback to previous state if AI output is invalid or missing critical fields. Explicitly removed `achieved_plot_point_id` if AI tried to include it.
        *   `check_atomic_plot_completion` (Stage 3): Implemented for focused AI analysis of individual plot points, using the new prompt. Includes validation of AI response structure.
    *   Confidence threshold adjustment deferred to testing if still needed after other improvements.
*   **Phase 2: Plausibility Check & State Management Enhancements (Completed)**
    *   Enhanced the plausibility check (Stage 2) in `socket_service.py` (`handle_player_action`):
        *   Improved word matching (TF-IDF inspired approach).
        *   Added location-based relevance checks.
        *   Added NPC-based relevance checks (considering NPCs present in the current location).
        *   Added special handling for critical/required plot points and for situations where players might be stuck.
    *   Ensured `socket_service.py` correctly merges validated `state_changes` from `ai_service.get_response` (Stage 1) into its working `state_data` before Stage 2 and 3 processing.
*   **Phase 3: Campaign Generation & Advanced Semantic Matching (Completed)**
    *   Updated `build_campaign_prompt` (`prompt_builder.py`) with more explicit examples of good atomic plot points and emphasized their importance.
    *   Enhanced `generate_campaign` (`ai_service.py`) to add validation ensuring plot points are atomic and clearly defined using a new `_check_plot_point_atomicity` helper function (checks for conjunctions, multiple verbs, etc.), logging warnings for non-atomic points.
    *   Advanced semantic matching for Stage 2 (Task 3.3 of v3 plan) deferred, to be revisited if testing shows current methods are insufficient.

## Remaining Work (Phased Approach from Spec)

**Feature: Plot Point Completion System Enhancement (v3 Strategy - Phase 4 Pending)**
*   **Phase 4: Debugging & Monitoring Enhancements**
    *   Add detailed logging of plot point evaluation decisions, "near-miss" completions, and frequently checked but never completed plot points.
    *   Implement developer tools for debugging plot point completion and manually marking plot points as completed for testing.

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

*   Implement Inventory Display on `play.html`. **(Verified & Centralized)** - Display logic now correctly implemented in `socketClient.mjs`.
*   Add AI Prompt Guardrails to `build_response_prompt`. **(Completed)**
*   Implement Location History tracking and display. **(Verified & Centralized)** - Display logic now correctly implemented in `socketClient.mjs`.
*   Implement Multiplayer Location Display. **(Verified & Centralized)** - Display logic now correctly implemented in `socketClient.mjs`.
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

**Feature: Game Details Page (Completed)**
    *   **Objective:** Allow users to view comprehensive details of a game, including template data, campaign specifics, player information, and customizations.
    *   **Plan:** `memory-bank/game_details_page_plan.md`
    *   **Backend (`questforge/views/game.py`):**
        *   Added new route `/game/<int:game_id>/details`.
        *   Implemented `game_details(game_id)` view function to fetch `Game`, `Template`, `Campaign`, `GamePlayer` data.
    *   **Frontend (`questforge/templates/game/details.html`):**
        *   Created new Jinja2 template to display all fetched information.
        *   Handles display of basic game info, player details, template data, campaign specifics (if available), and creator customizations/overrides.
        *   Includes formatting for JSON data and a link back to the game list.
    *   **Linking (`questforge/templates/game/list.html`):**
        *   Added a "View Details" link on the "Join a Game" screen for each game.

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

**Feature: Conclusion Check Logic Refinement (Completed)**
*   **Objective:** Refine the game's conclusion check logic in `questforge/services/campaign_service.py` to be less restrictive, particularly for string and list comparisons.
*   **Implementation:**
    *   Modified `check_conclusion` in `questforge/services/campaign_service.py`:
        *   For `state_key_contains` conditions:
            *   If `actual_value` (from `state_data`) is a list, the check now passes if any item in `actual_value` (converted to string) contains the `value_to_contain` (converted to string) as a case-insensitive substring.
            *   If `actual_value` is a string, the check now passes if `actual_value` contains `value_to_contain` as a case-insensitive substring.
        *   For `location_visited` conditions:
            *   The check now passes if the `location_name_condition` (from the conclusion condition) is found as a case-insensitive substring within any of the location strings in `state_data['visited_locations']`.
    *   This addresses issues where slight variations in strings (e.g., "Escape Pod Bay" vs. "Escape Pod Bay (outside blast doors)") would cause a valid conclusion to fail.

**Feature: Dynamic Gameplay Difficulty (Completed)**
*   **Objective:** Allow game creators to change game difficulty ('Easy', 'Normal', 'Hard') during active gameplay, influencing AI narrative responses.
*   **Plan:** `memory-bank/dynamic_gameplay_difficulty_plan.md`
*   **Database:**
    *   Added `current_difficulty` to `Game` model (`questforge/models/game.py`).
    *   Generated and applied DB migration.
*   **Game Creation:**
    *   Updated `Game.__init__` and `questforge/views/campaign_api.py` to set initial `current_difficulty`.
*   **AI Integration:**
    *   `ai_service.get_response` now accepts `current_difficulty`.
    *   `prompt_builder.build_response_prompt` now incorporates `current_difficulty` to add specific instructions for AI behavior regarding unreasonable player actions.
*   **SocketIO:**
    *   `handle_player_action` in `socket_service.py` passes `game.current_difficulty` to `ai_service.get_response`.
    *   Added new `change_difficulty` event handler in `socket_service.py` to update `game.current_difficulty` in DB.
*   **UI:**
    *   Added difficulty selector dropdown to `play.html` (visible to game creator).
    *   `socketClient.mjs` emits `change_difficulty` event when dropdown value changes.

**Feature: Historical Game Summary (Completed)**
*   **Objective:** Provide the AI with a token-efficient, persistent memory of significant game events to improve narrative coherence.
*   **Plan:** `memory-bank/historical_game_summary_plan.md`
*   **Database (`GameState`):** Added `historical_summary: []` to `state_data` in `questforge/models/game_state.py`.
*   **AI Service (`ai_service.py`):**
    *   Added `generate_historical_summary` method using `OPENAI_MODEL_MAIN`.
    *   Calls `prompt_builder.build_summary_prompt`.
*   **Prompt Builder (`prompt_builder.py`):** Added `build_summary_prompt` function.
*   **Socket Service (`socket_service.py`):**
    *   `handle_player_action` calls `generate_historical_summary` after Stage 1 AI response.
    *   Appends summary to `state_data['historical_summary']`, capped by `MAX_HISTORICAL_SUMMARIES`.
*   **Context Manager (`context_manager.py`):**
    *   `build_context` prepends `historical_summary` to AI context.
*   **Configuration (`config.py`):** Added `MAX_HISTORICAL_SUMMARIES` variable.

**Feature: Slash Command System (Completed)**
*   **Objective:** Allowed players to use slash commands (`/help`, `/remaining_plot_points`, `/game_help`) for in-game information and actions.
*   **Phase 1: Frontend Detection & Backend Stub (Completed)**
    *   Modified `questforge/static/js/socketClient.mjs`: Centralized action processing in `socketClient.performAction`, which now differentiates slash commands (emitting `slash_command` event) from regular actions (emitting `player_action` event).
    *   Modified `questforge/templates/game/play.html`: Event handlers for custom input now call `socketClient.performAction()` and clear the input field afterwards.
*   **Phase 2: Backend Logic for `/help`, `/remaining_plot_points`, and `/show_plot_points` (Completed)**
    *   Modified `questforge/services/socket_service.py`:
        *   Implemented logic in `handle_slash_command` for `/help` (returns command list) and `/remaining_plot_points` (calculates remaining required plot points).
        *   Updated `/show_plot_points` to list all plot points, their required/optional status, and their completion status (Completed/Pending), formatted as a list of strings.
        *   Updated `/help` command to include `/show_plot_points`.
*   **Phase 3: Backend AI Interaction for `/game_help` (Completed)**
    *   Modified `questforge/utils/prompt_builder.py`: Added `build_hint_prompt`.
    *   Modified `questforge/services/ai_service.py`: Added `get_ai_hint` method to `AIService`; corrected `log_api_usage` to align with `ApiUsageLog` model (removed `player_id`, `endpoint`).
    *   Modified `questforge/services/socket_service.py`: `handle_slash_command` now calls `ai_service.get_ai_hint()` for `/game_help`.
*   **Phase 4: Frontend Display of Slash Command Responses (Completed)**
    *   Modified `questforge/templates/game/play.html`: Added SocketIO listener for `slash_command_response` to display responses in `gameStateVisualization`.
*   **Debugging & Refinements (Completed):**
    *   Resolved various client-side JavaScript and backend Python issues.
    *   Removed diagnostic `console.log` statements from JavaScript files.

**Feature: Difficulty Setting Enhancement (Implementation Completed, Awaiting Testing)**
*   **Objective:** Make the "difficulty" setting chosen during game creation more impactful on the generated campaign.
*   **Investigation (Completed):**
    *   Traced data flow of "difficulty" from `create.html` UI -> `Game.template_overrides` -> `campaign_service` -> `ai_service` -> `prompt_builder`.
    *   Confirmed "difficulty" was included in the AI prompt but likely lacked specific instructions for impact.
*   **Implementation (Completed):**
    *   Modified `questforge/utils/prompt_builder.py` (`build_campaign_prompt` function):
        *   Added logic to retrieve the `difficulty_value` (defaulting to 'medium').
        *   Appended more explicit instructions to the AI prompt based on the `difficulty_value` ('easy', 'medium', 'hard', 'very hard'). These instructions guide the AI on aspects like resource availability, challenge complexity, NPC behavior, and plot point clarity.
*   **Next Steps:** User to test by creating games with various difficulty settings. Document effective AI patterns in `.clinerules/clinerules.md` if discovered.

**Ongoing Task: AI Response Granularity Tuning** (Medium Priority - In Progress)

*   **Objective:** Refine AI prompts to prevent overly verbose responses or the AI performing multiple actions from a single player input.
*   **Actions Taken:**
    *   Modified `questforge/utils/prompt_builder.py` (`build_response_prompt`):
        *   Added explicit instructions for the AI to focus on the immediate outcome of the player's current action.
        *   Emphasized a single-turn mentality.
        *   Reinforced that plot point achievements and conclusion condition flags should only be triggered by the single, current player action.
*   **Next Steps:** Test changes, iterate on prompts if needed, document successful strategies.

**Previous Task: Game Screen Redesign (`play.html`)** (Progress Update)

*   Consolidate Game Log & Narrative display. **(Completed)** - `gameStateVisualization` now handles full log and current location.
*   Restructure right column with always-visible actions and tabs for secondary info (Status, Details). (Partially Completed - Tabs exist)
    *   **NPC Details Display (Completed):** Added display of `campaign.key_characters` (NPCs and their attributes) to the "Details" tab in `questforge/templates/game/play.html`.
*   **Sticky Navbar (Completed):** Modified `questforge/static/css/styles.css` to make the navbar sticky.
*   Display player names instead of IDs. **(Completed)** - Implemented in `updatePlayerLocationsDisplay` within `socketClient.mjs`.
*   Relocate API cost display. **(Completed)** - Moved to "Details" tab.
*   Apply subtle thematic styling. (Ongoing/Low Priority)

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
