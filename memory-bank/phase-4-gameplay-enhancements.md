# Phase 4: Gameplay Enhancements

This phase focuses on improving the turn-by-turn gameplay experience by providing more context to the player and refining AI interactions.

## Goals & Tasks

1.  **Inventory Display:**
    *   **Goal:** Show the player their current inventory items on the main game screen (`play.html`).
    *   **Data Source:** `GameState.state_data['current_inventory']` (list of strings).
    *   **Backend Tasks:**
        *   Verify `GameStateService` (`get_state`, `update_state`) and the `game_state_update` SocketIO event consistently include the `current_inventory` list from `state_data`.
    *   **Frontend Tasks:**
        *   Modify `questforge/templates/game/play.html` to add a dedicated section (e.g., sidebar panel, collapsible div) to display the items in the `current_inventory` list received via the `game_state_update` event.
        *   Update `questforge/static/js/socketClient.mjs` to handle rendering the inventory list when the state updates.

2.  **AI Prompt Guardrails:**
    *   **Goal:** Make the AI less likely to fulfill player requests that bypass intended challenges or narrative logic.
    *   **Tasks:**
        *   Modify `build_response_prompt` function in `questforge/utils/prompt_builder.py`.
        *   Add explicit instructions to the AI's system message or prompt structure, guiding it to:
            *   Evaluate player actions against the current game state and narrative consistency.
            *   Provide narrative consequences or deny actions that are illogical (e.g., using an item not possessed, finding something not present).
            *   Prioritize narrative progression and realistic outcomes over simply executing commands.

3.  **Location History:**
    *   **Goal:** Allow players to see a list of locations they have visited.
    *   **Tasks:**
        *   **Schema:** Add `visited_locations` (JSON list of strings) to `questforge/models/game_state.py::GameState`. Generate and apply DB migration.
        *   **Backend:** Modify `questforge/services/game_state_service.py::update_state` to check the `location` in `state_changes`. If it's new and not in `visited_locations`, append it. Ensure `visited_locations` is saved and included in the `game_state_update` event payload.
        *   **Frontend:** Modify `questforge/templates/game/play.html` and `questforge/static/js/socketClient.mjs` to display the `visited_locations` list (e.g., in a separate panel or modal).

4.  **Multiplayer Location Display:**
    *   **Goal:** Show the current location of all players in the game on `play.html`.
    *   **Approach (Option B - Service Tracking):** Track player locations separately in `GameStateService` to avoid major `state_data` refactoring initially.
    *   **Tasks:**
        *   **Backend:**
            *   Modify `questforge/services/game_state_service.py`:
                *   Add structure to `active_games` dictionary (e.g., `active_games[game_id]['player_locations'] = {'user_id_1': 'Location A', ...}`).
                *   Update `join_game` and `leave_game` to manage this structure.
                *   Modify `update_state` to update the acting player's location based on `state_changes['location']`. (Assumption: AI response implies the acting player moved).
                *   Include `player_locations` in the data returned by `get_state` and emitted via `game_state_update`.
        *   **Frontend:** Modify `questforge/templates/game/play.html` and `questforge/static/js/socketClient.mjs` to display the `player_locations` dictionary, likely near the existing player list.

5.  **Single-Player Mode:**
    *   **Goal:** Allow games to be started and played by a single user.
    *   **Tasks:**
        *   Modify `handle_start_game` in `questforge/services/socket_service.py`.
        *   Change the player count check from `if player_count < 2:` (or similar) to `if player_count < 1:`.
        *   Verify no other logic breaks when iterating over a single player.
