# Active Context - QuestForge - 2025-01-05

## Current Focus: Gameplay Enhancements & Bug Fixing

We are currently working on improving the core gameplay loop and addressing bugs identified during testing.

## Recent Changes (Summary)

*   **AI Model Display:** Added a section to the game play screen (`questforge/templates/game/play.html`) to display the AI model (`OPENAI_MODEL`) retrieved from the Flask app config via the `play` view (`questforge/views/game.py`). (Implemented 2025-01-05)
*   **Objective Display:** Added a section to the game play screen (`questforge/templates/game/play.html`) to display the campaign objective (`campaign.objectives`). Currently shows raw JSON; needs refinement based on actual data structure. (Implemented 2025-01-05)
*   **Game Conclusion Logic:** Attempted to fix game conclusion by modifying the AI prompt (`prompt_builder.py`) for structured `conclusion_conditions` and updating `check_conclusion` in `campaign_service.py`. This requires further debugging. (Attempted ~2025-01-04/05)
*   **UI Updates (`play.html`):** Implemented dynamic updates via JavaScript for Player Location, Visited Locations, and Inventory displays. (Fixed ~2025-01-04/05)
*   **Bug Fixes:** Resolved `ValueError` and `AttributeError` issues in `campaign_service.py` and `socket_service.py` related to AI response handling. Corrected a 404 error by replacing `game_create.html` content. (Fixed ~2025-01-04/05)

## Key Files Recently Modified/Reviewed

*   `questforge/templates/game/play.html`: Added AI model display card, added objective display card. Modified JS for dynamic UI updates.
*   `questforge/views/game.py`: Modified `play` function to pass `ai_model` to template. Reviewed `play` function to confirm campaign data is passed.
*   `questforge/models/campaign.py`: Reviewed `objectives` field.
*   `questforge/services/campaign_service.py`: Updated `check_conclusion`.
*   `questforge/utils/prompt_builder.py`: Modified prompt for `conclusion_conditions`.
*   `questforge/services/ai_service.py`: Modified return signatures.
*   `questforge/services/socket_service.py`: Reviewed `handle_player_action`.

## Next Steps & Pending Tasks

1.  **Refine Objective Display:**
    *   Observe the actual structure of `campaign.objectives` during gameplay.
    *   Update `questforge/templates/game/play.html` to parse and display the objective in a user-friendly format (e.g., extracting a specific text description).
2.  **Debug Game Conclusion:**
    *   Verify if the AI consistently returns structured `conclusion_conditions` and includes necessary state updates (e.g., `"escape_successful": true`).
    *   Add logging within `campaign_service.py:check_conclusion` to trace the evaluation logic.
    *   Test various game scenarios to ensure conclusion triggers correctly.
3.  **Update Memory Bank:** Ensure `progress.md` and potentially other relevant files reflect the latest status.

## Active Decisions & Considerations

*   Displaying raw objective JSON initially to understand its structure before formatting.
*   Prioritizing fixing core gameplay loop issues (like conclusion) alongside UI enhancements.
