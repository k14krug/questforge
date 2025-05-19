# Plan: Historical Game Summary Feature

## 1. Problem Statement:
The AI's context for generating narrative responses during gameplay is limited to the current game state, campaign details, and only the last 5 entries of the game log. This can lead to the AI losing awareness of significant past events, revealed information, or long-term clues mentioned earlier in the game, potentially causing narrative inconsistencies and hindering effective guidance for the player towards objectives. Sending the full game log in every prompt is not feasible due to token limits and increased API costs.

## 2. Goal:
To provide the AI with a comprehensive, yet token-efficient, history of significant game events to maintain narrative coherence and improve gameplay guidance throughout the entire game duration.

## 3. Proposed Solution:
Implement a "Historical Game Summary" system by adding a dedicated field (`historical_summary`) to the `GameState.state_data`. This field will store concise summaries of key events from the game's history. A secondary AI model (`OPENAI_MODEL_MAIN`) will be used to generate these summaries after each turn. The main AI prompt for narrative generation will then include this historical summary instead of the recent game log.

## 4. Detailed Plan:

**Phase 1: Database Model Modification**

*   **Task 1.1:** Modify the `GameState` model in `questforge/models/game_state.py`.
    *   Update the default structure of the `state_data` JSON field to include a new key, e.g., `"historical_summary": []`. This will be an empty list initially.

**Phase 2: AI Summarization Service**

*   **Task 2.1:** Modify `questforge/services/ai_service.py`.
    *   Add a new method, e.g., `generate_historical_summary(player_action: str, stage_one_narrative: str, state_changes: Dict[str, Any]) -> Optional[str]`.
    *   This method will take the player's action, the Stage 1 AI narrative response, and the resulting state changes as input.
    *   It will construct a targeted prompt for the AI (`OPENAI_MODEL_MAIN`) asking it to generate a concise, single-sentence summary of the most significant event(s) that occurred in this turn, based on the provided inputs.
    *   The prompt should instruct the AI to output *only* the summary string.
    *   Implement the API call to `OPENAI_MODEL_MAIN` using this prompt.
    *   Include error handling and return `None` if summarization fails.
    *   Log API usage for this call.
*   **Task 2.2:** Modify `questforge/utils/prompt_builder.py`.
    *   Add a new function, e.g., `build_summary_prompt(player_action: str, stage_one_narrative: str, state_changes: Dict[str, Any]) -> str`.
    *   This function will construct the specific prompt string for the `generate_historical_summary` AI call, guiding the AI on what constitutes a "significant event" for summarization (e.g., plot point progress, major state changes, key information revealed).

**Phase 3: Integrate Summarization into Gameplay Loop**

*   **Task 3.1:** Modify `questforge/services/socket_service.py` in the `handle_player_action` event handler.
    *   After the Stage 1 AI response (`ai_service.get_response`) is successfully processed and its `state_changes` are merged into the `state_data`, call the new `ai_service.generate_historical_summary` method. Pass the player action, Stage 1 narrative, and the *merged* `state_changes`.
    *   If a summary is successfully returned, append it to the `historical_summary` list within the `state_data` dictionary of the `db_game_state` object.
    *   Ensure the `db_game_state.state_data` is flagged as modified for SQLAlchemy after appending the summary.

**Phase 4: Update AI Context Building**

*   **Task 4.1:** Modify `questforge/utils/context_manager.py` in the `build_context` function.
    *   Remove the section that includes the "--- Recent Events (Game Log) ---" and the last 5 log entries.
    *   Add a new section to include the "--- Game History Summary ---" based on the `historical_summary` list from `game_state.state_data`.
    *   Iterate through the `historical_summary` list and append each summary item to the context lines.

**Phase 5: Testing and Refinement**

*   **Task 5.1:** Manually test the feature by playing games.
    *   Verify that the `historical_summary` list in the database's `game_state.state_data` is being populated with concise summaries after each turn.
    *   Observe AI narrative responses in `play.html` to see if the AI demonstrates awareness of past events that occurred more than 5 turns ago, based on the historical summary.
    *   Monitor token usage and API costs to ensure the change is beneficial.
    *   Refine the `build_summary_prompt` and the criteria for summarization if the AI is not generating useful summaries.
*   **Task 5.2:** Update Memory Bank documentation (`activeContext.md`, `progress.md`) and `.clinerules/clinerules.md` to reflect the implemented feature and any lessons learned during testing.

## 5. Benefits:
*   **Improved AI Coherence:** AI will have better long-term memory of game events.
*   **Reduced Token Usage:** Replacing verbose log entries with concise summaries will decrease prompt size.
*   **Lower API Costs:** Reduced token usage directly translates to lower costs for AI calls.
*   **More Robust Gameplay:** AI can better handle scenarios requiring recall of earlier events.

## 6. Next Steps:
Toggle to ACT MODE to begin implementing Phase 1 of this plan.
