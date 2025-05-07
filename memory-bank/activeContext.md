# Active Context - QuestForge - Narrative Guidance System

## Date: 2025-07-05

## 1. Current Work Focus:
Displaying NPC details on the game play screen.

## 2. Recent Changes (In Progress/Completed Task):
*   **NPC Details Display on Game Screen (Completed):**
    *   Modified `questforge/templates/game/play.html` to add a "Key Characters (NPCs)" section to the "Details" tab.
    *   This section iterates through `campaign.key_characters` (which can be a dictionary or a list of objects) and displays NPC names, descriptions, and attributes.
    *   The view function `questforge/views/game.py::play()` already passes the `campaign` object, so no changes were needed there.
*   **Completed Game Badge Styling (Completed):**
    *   Modified `questforge/templates/game/list.html` to display a green badge (`bg-success`) for games with status 'completed'. Other statuses retain the default gray badge (`bg-secondary`).
*   **Game Deletion Feature (Completed):**
    *   Added a new route `game/<int:game_id>/delete` (POST only) to `questforge/views/game.py`.
    *   The `delete_game` function in `questforge/views/game.py`:
        *   Verifies that the current user is the creator of the game (using `game.creator.id` for comparison).
        *   Deletes the `Game` record.
        *   Deletes associated `Campaign`, `GameState`, `GamePlayer`, and `ApiUsageLog` records.
        *   Redirects to the game list with a success/error flash message.
    *   Imported `GameState` into `questforge/views/game.py`.
    *   Updated `questforge/templates/game/list.html`:
        *   Added a "Delete" button within a form for each game, visible only if `current_user.is_authenticated and current_user.id == game.creator.id`.
        *   The form POSTs to the `game.delete_game` endpoint.
        *   Added a JavaScript `confirm()` dialog before form submission.
        *   Resolved `csrf_token` undefined error by passing a `FlaskForm` instance from the `list_games` view and using `{{ form.csrf_token }}` in the template.
*   **Re-enter Completed Games (Completed):**
    *   Modified `questforge/templates/game/list.html` to make games with status 'completed' link to the play view (`url_for('game.play', game_id=game.id)`), allowing users to review the game log and final state.

The following tasks related to the **ID-Based Plot Point System Upgrade** and its conclusion handling have been completed:

*   **ID-Based Plot Point System Implementation:**
    *   Modified AI prompts (`prompt_builder.py`) for campaign generation and action responses to use/expect plot point IDs.
    *   Enhanced AI response validation (`ai_service.py`) to check for plot point IDs and uniqueness.
    *   Updated campaign generation (`campaign_service.py`) to auto-complete the first required plot point by ID.
    *   Updated conclusion checking logic (`campaign_service.py`) to verify required plot points by ID and evaluate `conclusion_conditions`.
    *   Updated AI context generation (`context_manager.py`) to include plot point IDs and `conclusion_conditions`.
    *   Updated action handling (`socket_service.py`) to identify the next required plot point by ID, process AI-reported completions by ID, merge AI state changes correctly into `state_data`, track `visited_locations`, and call `check_conclusion` after state updates.
    *   Improved error handling in `campaign_service.py` for AI service errors during campaign generation.
    *   Refined AI prompts (`prompt_builder.py`) to explicitly guide the AI on setting critical event flags based on `conclusion_conditions`.

*   **Verification:**
    *   Thoroughly tested the implementation across different scenarios, confirming reliable game conclusion.
    *   Verified that the AI consistently sets necessary flags (e.g., `escape_successful`) when appropriate.

*   **UI Conclusion Handling:**
    *   Implemented client-side JavaScript logic in `questforge/static/js/socketClient.mjs` to:
        *   Listen for the `game_concluded` SocketIO event.
        *   Update the UI on `play.html` (element with ID `gameStatusDisplay`) to display "Status: Completed".
        *   Disable the action input field (`customActionInput`) and submit button (`submitCustomAction`).
        *   Display the conclusion message from the event payload.
    *   Added `id="gameStatusDisplay"` to the relevant `span` in `questforge/templates/game/play.html`.

*   **Final Turn Presentation:**
    *   Implemented logic in `questforge/services/socket_service.py`'s `handle_player_action` method.
    *   When `check_conclusion` returns `True`:
        *   Appended a system message (`{"type": "system", "content": "** CAMPAIGN COMPLETE! **"}`) to `broadcast_data['log']`.
        *   Set `broadcast_data['actions']` to `["Campaign Complete"]`.
        *   The modified `broadcast_data` is emitted via `game_state_update` for the final turn.
        *   The `game_concluded` event is emitted.
        *   The game's status in the database is updated to 'completed'.

*   **Memory Bank Cleanup:**
    *   The plan file `old-memory-bank-files-dont-use/id_based_plot_point_upgrade_plan.md` was handled (moved by user).

## 3. Next Steps:
*   Update `memory-bank/progress.md` to reflect the completion of the "Game Deletion Feature", "Re-enter Completed Games" enhancement, "Completed Game Badge Styling", and "NPC Details Display on Game Screen".
*   Await new tasks or further instructions.

## 4. Active Decisions & Considerations:
*   NPC details are displayed using data from `campaign.key_characters`. The template logic handles both dictionary and list-of-objects structures for this data, and also for NPC attributes.
*   Game deletion is a hard delete, removing the game and its associated records from the database. Creator comparison uses `game.creator.id`.
*   The "Join Game" screen (`game/list.html`) now displays all games and allows re-entry into 'completed' games by linking them to the play view.
*   Completed game status badges are now green (`bg-success`) on `game/list.html`.
*   The `STUCK_THRESHOLD` (related to the prior Narrative Guidance System) is set to 3 in `socket_service.py`. This was part of a previous feature but worth noting if further gameplay tuning is needed.
*   The ID-based plot point system stores full plot point objects in `GameState.state_data['completed_plot_points']`.
*   `campaign_service.check_conclusion` now robustly checks required plot points by ID and evaluates `conclusion_conditions` from the campaign against `state_data`.
