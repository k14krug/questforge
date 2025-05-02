# Active Context

## Current Focus: Enhanced Game Creation (Phase 5)

*   **Initiate Phase 5:** Begin work on the tasks outlined in [./phase-5-enhanced-game-creation.md](./phase-5-enhanced-game-creation.md).

## Key References
*   **Application Specification:** [../questforge-spec.md](../questforge-spec.md) - The definitive specification detailing architecture, models, and remaining work phases.
*   **Progress Tracker:** [progress.md](./progress.md) - Detailed breakdown of remaining work phases.
*   **Project Brief:** [projectbrief.md](./projectbrief.md) - High-level overview and core concepts.
*   **Template Model:** [template_model.md](./template_model.md)
*   **Template Creation Process:** [template_creation_process.md](./template_creation_process.md)
*   **Game Creation Process:** [game_creation_process.md](./game_creation_process.md)
*   **Project Intelligence:** [.clinerules](./.clinerules)
*   **Phase 4 Details:** [./phase-4-gameplay-enhancements.md](./phase-4-gameplay-enhancements.md)
*   **Phase 5 Details:** [./phase-5-enhanced-game-creation.md](./phase-5-enhanced-game-creation.md)

## Recent Changes (Completed Task)
*   **Completed Phase 4: Gameplay Enhancements:** Successfully implemented Inventory Display, AI Prompt Guardrails, Location History, and Multiplayer Location Display.
*   **Completed Phase 2 Verification:** Verified `campaign_service.generate_campaign_structure` and `socket_service.handle_start_game` function correctly for delayed campaign generation. No code changes needed.
*   **Restructured Project Phases:** Introduced Phase 4 (Gameplay Enhancements) and Phase 5 (Enhanced Game Creation), shifting Testing & Deployment to Phase 6. Created corresponding detail files in the Memory Bank (`phase-4-gameplay-enhancements.md`, `phase-5-enhanced-game-creation.md`). Updated `progress.md` to reflect the new structure.
*   **Completed Phase 3: AI Prompt Refinement:** Successfully updated `build_campaign_prompt` in `questforge/utils/prompt_builder.py` to better utilize `Template` fields (including `default_rules`) and `player_descriptions`, providing clearer instructions to the AI for generating more tailored campaign structures.
*   **Implemented Inventory Display (Phase 4):** Added an inventory display section to `questforge/templates/game/play.html` to render items from `game_state.state_data.inventory`.
*   **Implemented AI Prompt Guardrails (Phase 4):** Modified `build_response_prompt` in `questforge/utils/prompt_builder.py` to include instructions for the AI to evaluate player actions against game state and narrative consistency.
*   **Implemented Location History (Phase 4):** Added `visited_locations` to `GameState` model, updated `game_state_service.py` to track visited locations, and modified frontend (`play.html`, `socketClient.mjs`) to display the history.
*   **Implemented Multiplayer Location Display (Phase 4):** Modified `game_state_service.py` to track player locations in memory and updated frontend (`play.html`, `socketClient.mjs`) to display this information.
*   **Implemented Single-Player Mode (Phase 4):** Modified `handle_start_game` in `questforge/services/socket_service.py` to allow games to be started with a single player.
*   Created `questforge-spec.md` reflecting current codebase and defining remaining work phases.
*   Updated `projectbrief.md`, `progress.md`, and this file (`activeContext.md`) to align with the new spec.
*   Created `template_creation_process.md`.
*   Reviewed and updated `.clinerules`.
*   Resolved route conflict for `/api/games/create`:
    * Renamed conflicting route in `game_bp` to `/api/games/create-game`.
    * Fixed double-prefix issue in `campaign_api_bp` by removing `url_prefix='/api'` during blueprint registration.
*   Cleaned up excessive debug logging (`print` statements, verbose `logger.debug`) in `questforge/services/campaign_service.py`.
*   Removed unnecessary debug logging related to blueprint registration and route listing during application startup in `questforge/__init__.py`.
*   Corrected game creation issues identified from database analysis:
    *   Fixed `GameState.current_location` population by setting the attribute *after* object creation in `campaign_service.py`.
    *   Correctly associated the game creator using the `GamePlayer` association object in `campaign_api.py`. Verified that the `game_players` table is now being updated correctly.
*   Implemented LLM API connection logic in `ai_service.py`.
*   Enhanced `Template.validate_ai_response`.
*   Implemented error handling and logging in `ai_service.py`.
*   Implemented `campaign_service.update_campaign_state` and `check_conclusion`.
*   Refined join/leave handling in `socket_service.py`.
*   Implemented validation of state changes in `game_state_service.py`.
*   Ensured `get_state` provides necessary data in `game_state_service.py`.
*   **Resolved Game Start & Initial State Issues:**
    *   Fixed various `NameError` and `AttributeError` exceptions related to imports (`request`, `ai_service`), model relationships (`GameState` to `Campaign`), and attribute access (`Campaign.description`, `Campaign.initial_state`) during game start and state requests.
    *   Refactored `GameState` model to remove redundant `campaign_id`.
    *   Added `game_log` and `available_actions` fields to `GameState` model and database schema.
    *   Implemented `AIService.generate_initial_scene` to handle initial narrative/action generation.
    *   Updated `GameStateService` (`get_state`, `update_state`) and `SocketService` (`handle_start_game`, `handle_player_action`, `handle_state_request`) to correctly handle new fields, relationships, and initial scene generation flow.
    *   Corrected database migration script errors.
    *   Result: Game now starts successfully, displaying the initial AI-generated narrative and actions.
*   **Fixed Template Creation:** Resolved a series of errors related to template creation and editing, including `TypeError` and `ValidationErrors` related to the `question_flow` field. The template creation and editing process should now function correctly.
*   **Addressed Prompt Building Error:** Fixed a `TypeError` in `build_campaign_prompt` by ensuring the `default_rules` field is converted to a string before being added to the prompt.
*   **Completed Phase 1: Template Redesign & Character Definition:**
    *   Modified `Template` model (`questforge/models/template.py`) with new guidance fields, removed old fields.
    *   Modified `TemplateForm` (`questforge/views/forms.py`) to match the new model.
    *   Modified Template Views (`questforge/views/template.py`) to handle the new form/model.
    *   Added `character_description` column to `GamePlayer` model (`questforge/models/game.py`).
    *   Generated and applied database migration (`migrations/versions/06ff0646a8b4_...`).
    *   Updated Lobby UI (`questforge/templates/game/lobby.html`) with character description textareas and save buttons.
    *   Implemented character save logic via `handle_update_character_description` in `questforge/services/socket_service.py`.
*   **Implemented API Cost Tracking:**
    *   Created `ApiUsageLog` model (`questforge/models/api_usage_log.py`) to store details of each AI API call (model, tokens, calculated cost).
    *   Added `OPENAI_PRICING` dictionary to `config.py` for cost calculation (requires user updates for actual prices).
    *   Modified `AIService` (`questforge/services/ai_service.py`) to return model name and token usage data from API responses.
    *   Updated `campaign_service.py` and `socket_service.py` to:
        *   Log `ApiUsageLog` entries after successful AI calls.
        *   Implement robust model name matching (exact then iterative suffix removal) for pricing lookup.
        *   Handle database transactions correctly for logging.
    *   Updated `game.py` views (`list_games`, `play`) to calculate and pass total cost to templates.
    *   Updated `list.html` and `play.html` templates to display the calculated cost (dynamically on `play.html`).
    *   Updated `main.py` and `home.html` to display the configured `OPENAI_MODEL`.
*   **Resolved Location Persistence Bug:** Modified `build_response_prompt` in `questforge/utils/prompt_builder.py` to require the AI to always include the current `location` in the `state_changes` JSON.
*   **Added AI Context Logging:** Added debug logging in `questforge/services/ai_service.py` (`get_response` method) to print the exact context string being sent to the AI.
*   **Resolved Stale Context/Location Issue:**
    *   Identified and removed the redundant `current_location` column from the `GameState` model and database.
    *   Modified `game_state_service.update_state` to assign *new* dict/list objects to `state_data`, `game_log`, and `available_actions` instead of updating in place, ensuring SQLAlchemy detects changes to these TEXT-based JSON fields.
    *   Removed associated update/flagging logic for the deleted `current_location` column.
*   **Fixed Campaign Data Type Handling:** Modified `build_context` in `questforge/utils/context_manager.py` to handle cases where `campaign.campaign_data` might be stored as a JSON string instead of a dictionary, preventing an `AttributeError`.
*   **Implemented Log Rotation:** Replaced `FileHandler` with `RotatingFileHandler` in `questforge/__init__.py` to limit log file size (5MB) and keep backups (3).

## Next Steps (Phase 5)
*   **Initiate Phase 5: Enhanced Game Creation:** Begin work on the tasks outlined in [./phase-5-enhanced-game-creation.md](./phase-5-enhanced-game-creation.md).
