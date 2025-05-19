# QuestForge: Slash Command System Implementation Plan

## Date: 2025-08-05

## 1. Overview

**Objective:** Implement a system allowing players to type slash commands (e.g., `/help`, `/remaining_plot_points`, `/game_help`) into the game's input field to get specific information or trigger actions.

**Key Commands to Implement:**
*   `/help`: Displays available slash commands.
*   `/remaining_plot_points`: Shows the number of plot points left to complete.
*   `/game_help`: Provides a clue from the AI game master.

## 2. Implementation Phases

### Phase 1: Frontend - Command Detection and Emission

*   **File:** `questforge/templates/game/play.html` (within the `<script type="module">` block)
*   **Changes:**
    1.  Modify the event listeners for `customActionInput` (specifically the `'keypress'` event for 'Enter') and `submitCustomActionButton` (the `'click'` event).
    2.  Inside these listeners, *before* the existing `performAction(actionText)` call:
        *   Check if `actionText.startsWith('/')`.
        *   If true:
            *   Prevent the default game action (i.e., don't call `performAction(actionText)` for the original `'player_action'` event).
            *   Parse the command:
                *   `const parts = actionText.substring(1).split(' ');`
                *   `const command = parts[0].toLowerCase();`
                *   `const args = parts.slice(1);`
            *   Emit a new SocketIO event: `socketClient.socket.emit('slash_command', { game_id: gameId, user_id: window.currentUserId, command: command, args: args });`
            *   Add `console.log("Slash command detected:", actionText);` and `console.log("Emitted slash_command:", { command, args });` for debugging.
            *   Clear `customActionInput.value = '';`.
        *   If false (not a slash command):
            *   Proceed with the existing `performAction(actionText)` call.
            *   Clear `customActionInput.value = '';` (as it currently does).
*   **Verification:**
    1.  Run the application and navigate to a game's `play.html` page.
    2.  Open the browser's developer console.
    3.  Type a command like `/testcmd arg1 arg2` and press Enter/Submit.
    4.  **Expected Frontend:** `console.log` messages showing the detected command and the emitted event data. The command should NOT appear in the game log as a regular player action.
    5.  **Expected Backend (Initial Stub):** Add a temporary handler in `socket_service.py` for `'slash_command'` that prints "Received slash_command:" and the received data to the Flask server console. This confirms frontend-to-backend communication for the new event type.

### Phase 2: Backend - Basic Command Handling (`/help`, `/remaining_plot_points`)

*   **File:** `questforge/services/socket_service.py`
*   **Changes:**
    1.  Within `SocketService.register_handlers()`, add a new event handler: `@socketio.on('slash_command') def handle_slash_command(data):`
    2.  Inside `handle_slash_command(data)`:
        *   Extract `game_id`, `user_id`, `command`, `args` from `data`.
        *   Perform basic validation (fields present).
        *   Wrap database/logic in `with current_app.app_context():`.
        *   Log the received command: `current_app.logger.info(f"Received slash_command: /{command} {args} from user {user_id} in game {game_id}")`
        *   Fetch `Game` object.
        *   **For `command == 'help'`:**
            *   Define `available_commands = ["/help - Shows this help message.", "/remaining_plot_points - Shows how many plot points are left.", "/game_help - Asks the AI for a hint."]`
            *   `emit('slash_command_response', {'command': command, 'type': 'info', 'lines': available_commands}, room=request.sid)`
        *   **For `command == 'remaining_plot_points'`:**
            *   Fetch `Campaign` and `GameState` for `game_id`.
            *   If not found, emit an error response.
            *   Access `campaign.major_plot_points` (list of plot point dicts).
            *   Access `game_state_obj.state_data.get('completed_plot_points', [])` (list of completed plot point dicts). Ensure these are lists of dicts with an `id` key.
            *   Filter `major_plot_points` to find those where `pp.get('required') == True`.
            *   Filter again to find those whose `id` is NOT in the `id`s of `completed_plot_points`.
            *   `count = len(remaining_required_plot_points)`
            *   `emit('slash_command_response', {'command': command, 'type': 'info', 'message': f"There are {count} required plot points remaining."}, room=request.sid)`
        *   **Else (unknown command):**
            *   `emit('slash_command_response', {'command': command, 'type': 'error', 'message': f"Unknown command: /{command}"}, room=request.sid)`
*   **Verification:**
    1.  After backend changes, restart the Flask app.
    2.  In the game, type `/help`. Expected: Help messages appear in the UI.
    3.  In the game, type `/remaining_plot_points`. Expected: Message about remaining plot points appears.
    4.  Type an unknown command like `/foo`. Expected: "Unknown command: /foo" message appears.

### Phase 3: Backend - AI Interaction for `/game_help`

*   **File:** `questforge/utils/prompt_builder.py`
    *   **Changes:** Add `def build_hint_prompt(game_state_obj, campaign_obj):`
        *   Constructs a prompt including current game context (location, recent log, objective, remaining plot points).
        *   Instructs AI to provide a subtle, non-spoilery hint.
*   **File:** `questforge/services/ai_service.py` (class `AIService`)
    *   **Changes:** Add `def get_ai_hint(self, game_state_obj, campaign_obj):`
        *   Calls `prompt_builder.build_hint_prompt`.
        *   Calls LLM API.
        *   Returns AI's textual hint.
        *   Handles API errors and logs API usage (similar to existing `get_response`).
*   **File:** `questforge/services/socket_service.py`
    *   **Changes:** In `handle_slash_command(data)`:
        *   Add `elif command == 'game_help':` block.
        *   Fetch `GameState` and `Campaign` objects.
        *   Call `ai_service.get_ai_hint(game_state_obj, campaign_obj)`.
        *   `emit('slash_command_response', {'command': command, 'type': 'hint', 'message': ai_hint_text}, room=request.sid)`
*   **Verification:**
    1.  Restart Flask app.
    2.  In the game, type `/game_help`.
    3.  Expected: An AI-generated hint appears in the UI. Check server logs for AI API call.

### Phase 4: Frontend - Displaying Command Responses

*   **File:** `questforge/templates/game/play.html` (within the `<script type="module">` block)
*   **Changes:**
    1.  Add a new SocketIO listener: `socketClient.socket.on('slash_command_response', (data) => { ... });`
    2.  Inside this listener:
        *   `console.log("Received slash_command_response:", data);`
        *   Get the `gameStateVisualization` div.
        *   Create a new `div` for the response message. Add classes like `log-entry log-entry-system` (or a new specific class like `log-entry-slash-command`).
        *   If `data.type == 'info'` or `data.type == 'hint'`:
            *   If `data.lines` (for `/help`): Iterate `data.lines`, create a `p` or `div` for each, and append to the new response div.
            *   If `data.message`: Set the new response div's `textContent` to `data.message`.
        *   If `data.type == 'error'`:
            *   Set `textContent` to `data.message`. Style as an error.
        *   Append the new response div to `gameStateVisualization`.
        *   Scroll `gameStateVisualization` to the bottom.
*   **Verification:**
    1.  Verified by successful display of outputs from Phases 2 and 3. Ensure messages are clear and appear in the game log area.

### Phase 5: Documentation and Refinement

*   **Update `memory-bank/activeContext.md`:** Set "Slash Command System Implementation" as current work focus.
*   **Update `memory-bank/progress.md`:** Add "Slash Command System" under "Current Task" or "In Progress Features."
*   **Update `.clinerules/clinerules.md`:** Document any new generalizable patterns.
*   **Refine `/help` (Optional):** If time permits, make the `/help` command dynamically list commands based on backend definitions rather than a hardcoded list in `socket_service.py`.

## 3. Key Files Involved

*   `questforge/templates/game/play.html`
*   `questforge/services/socket_service.py`
*   `questforge/utils/prompt_builder.py`
*   `questforge/services/ai_service.py`
*   `questforge/models/campaign.py` (for reading plot point structure)
*   `questforge/models/game_state.py` (for reading completed plot points)

## 4. Notes on Plot Point Logic for `/remaining_plot_points`

*   `Campaign.major_plot_points` is expected to be a list of dictionaries.
*   Each plot point dictionary should have an `id` (string or int) and a `required` (boolean) key.
*   `GameState.state_data['completed_plot_points']` is expected to be a list of dictionaries, where each dictionary represents a completed plot point and contains at least an `id` key.
