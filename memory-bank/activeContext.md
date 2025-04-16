# Active Context

## Current Focus: Implementing Delayed Campaign Generation (Phase 2)

*   **Modify Game Creation API:** Simplify the game creation endpoint to only create the basic `Game` record.
*   **Implement Lobby Start Logic:** Create the SocketIO handler (`handle_start_game`) to trigger campaign generation.
*   **Implement Campaign Generation Service:** Create/modify the service function to orchestrate the AI call using the template and character data, then save the `Campaign` and `GameState`.
*   **Implement Game Start Flow:** Ensure players are notified/redirected to the game interface after generation.

## Key References
*   **Application Specification:** [../questforge-spec.md](../questforge-spec.md) - The definitive specification detailing architecture, models, and remaining work phases.
*   **Progress Tracker:** [progress.md](./progress.md) - Detailed breakdown of remaining work phases.
*   **Project Brief:** [projectbrief.md](./projectbrief.md) - High-level overview and core concepts.
*   **Template Model:** [template_model.md](./template_model.md)
*   **Template Creation Process:** [template_creation_process.md](./template_creation_process.md)
*   **Game Creation Process:** [game_creation_process.md](./game_creation_process.md)
*   **Project Intelligence:** [.clinerules](./.clinerules)

## Recent Changes (Completed Task)
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
*   **Resolved Location Persistence Bug:** Modified `build_response_prompt` in `questforge/utils/prompt_builder.py` to require the AI to always include the current `location` in the `state_changes` JSON, ensuring the player's location is correctly maintained after AI responses.

## Next Steps (Phase 2)
*   **Modify Game Creation API:** Update `/api/games/create` (or equivalent) to only create `Game` and `GamePlayer` records.
*   **Implement Lobby Start Logic:** Update `handle_start_game` in `socket_service.py` to trigger campaign generation.
*   **Implement Campaign Generation Service:** Update `campaign_service.py` to handle generation using template + character data.
*   **Implement Game Start Flow:** Ensure `handle_start_game` notifies players to load the game interface.
*   **(Phase 3) Revise AI Prompt:** Update `build_campaign_prompt` in `prompt_builder.py`.

## Decisions & Considerations
*   Refine prompt structures in `prompt_builder.py` iteratively based on AI performance.
*   Determine specific strategy for context management (`context_manager.py`).
*   The `question_flow` field has been removed from the template.
*   The AI will generate the campaign structure based on high-level guidance and player character descriptions.
