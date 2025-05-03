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
*   **Game Conclusion Logic Fix (Completed):**
    *   Modified `socket_service.py` to correctly merge the complete state from `game_state_service` into the DB `GameState` object, re-fetch the object after commit, and call `check_conclusion` with the refreshed state.
    *   Fixed issues with SQLAlchemy JSON field mutation tracking by explicitly assigning a copy of the updated state dictionary to force change detection.
    *   Fixed `campaign_service.py` to correctly access the campaign ID via `game_state.game.campaign.id`.
    *   Added missing `import json` in `campaign_service.py` to fix a `NameError` during logging.
    *   Enhanced logging in `campaign_service.py` (`check_conclusion`) for better debugging.
    *   Updated `prompt_builder.py` (`build_response_prompt`) to explicitly instruct the AI to include conclusion-related state keys in its `state_changes`.
    *   Fixed campaign generation JSON truncation by increasing `max_tokens` to 4000 in `ai_service.py`.

## Remaining Work (Phased Approach from Spec)

**Phase 1: Template Redesign & Character Definition (Completed)**
*   (Details omitted for brevity - see above)

**Phase 2: Delayed Campaign Generation (Completed)**

*   **Modify Game Creation API:** **(Completed)** Updated the `/api/games/create-game` endpoint (`questforge/views/game.py`) to only create the basic `Game` and `GamePlayer` records, removing premature `Campaign` creation.
*   **Implement Lobby Start Logic:** **(Verified)** Confirmed the `handle_start_game` SocketIO event (`questforge/services/socket_service.py`) correctly triggers the campaign generation process.
*   **Implement Campaign Generation Service:** **(Verified)** Confirmed the service logic (`campaign_service.generate_campaign_structure`) correctly orchestrates AI interaction and saves the `Campaign` and initial `GameState`. No code changes were needed.
*   **Implement Game Start Flow:** **(Verified)** Confirmed the `handle_start_game` function in `socket_service.py` correctly emits the `game_started` event only after successful campaign generation. No code changes were needed.

**Phase 3: AI Prompt Refinement (Completed)**

*   **Revise AI Campaign Prompt:** **(Completed)** Updated `build_campaign_prompt` in `questforge/utils/prompt_builder.py` to better utilize `Template` fields (including `default_rules`) and `player_descriptions`, providing clearer instructions to the AI for generating more tailored campaign structures.

**Phase 4: Gameplay Enhancements (Completed)** (See [./phase-4-gameplay-enhancements.md](./phase-4-gameplay-enhancements.md) for details)

*   Implement Inventory Display on `play.html`. **(Completed)**
*   Add AI Prompt Guardrails to `build_response_prompt`. **(Completed)**
*   Implement Location History tracking and display. **(Completed)**
*   Implement Multiplayer Location Display. **(Completed)**
*   Enable Single-Player Mode. **(Completed)**

**Phase 5: Narrative Guidance & Objective Enforcement (Implementation Complete, Testing Paused)** (See [./narrative_guidance_plan.md](./narrative_guidance_plan.md) for details)
*   Implemented required/optional plot points distinction. **(Completed)**
*   Added logic to track plot progression (`turns_since_plot_progress`). **(Completed)**
*   Enhanced AI prompts (`build_response_prompt`) to include objective focus, provide hints when stuck, and report plot achievement. **(Completed)**
*   Updated `socket_service` to handle plot tracking, stuck detection, and pass info to AI/conclusion check. **(Completed)**
*   Updated `check_conclusion` to verify required plot points are met. **(Completed)**
*   **Testing Pending:** Requires testing of objective enforcement, AI hints, and conclusion logic.
*   **Log Update Issue Pending:** Dynamic log update in `play.html` still needs diagnosis and fix.
*   **(Task Paused)** User requested pause to create game data generation tool first.

**Phase 6: Enhanced Game Creation (Next)** (Needs Planning - See [./phase-5-enhanced-game-creation.md](./phase-5-enhanced-game-creation.md) for initial thoughts - *Note: Renumbered from original Phase 5*)
*   Allow game creators to add customizations on top of templates before campaign generation.

**Phase 7: Testing & Deployment Prep** (Medium Priority - Ongoing - *Note: Renumbered from original Phase 6*)

*   Write unit & integration tests for new components (Phases 1-6).
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
