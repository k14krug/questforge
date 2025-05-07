# Narrative Guidance System Implementation

This document details the implementation of the Narrative Guidance System as outlined in `narrative_guidance_plan.md`.

## 1. Campaign Generation Modifications

*   **`questforge/utils/prompt_builder.py` (`build_campaign_prompt`):**
    *   Modified the prompt instructions for `generated_plot_points`. The AI is now instructed to generate plot points as a list of JSON objects, each containing:
        *   `description` (string): The textual description of the plot point.
        *   `required` (boolean): `true` if the plot point is essential for campaign completion, `false` if it's optional.
    *   The prompt now emphasizes that at least one plot point should be `required: true`.
    *   Example in prompt updated to: `[{"description": "Players investigate the initial theft.", "required": true}, {"description": "Players find optional clues about the thief's accomplice.", "required": false}, ...]`

*   **`questforge/services/ai_service.py` (`generate_campaign`):**
    *   Added validation logic to ensure `generated_plot_points` from the AI response is a list of dictionaries, and each dictionary contains a string `description` and a boolean `required` key.

*   **`questforge/services/campaign_service.py` (`generate_campaign_structure`):**
    *   No direct change was needed for parsing, as `major_plot_points=ai_response_data.get('generated_plot_points', [])` correctly assigns the list of new plot point objects to the `Campaign.major_plot_points` (JSON) field.

## 2. Game State Modifications

*   **`questforge/models/game_state.py` (`GameState` model):**
    *   Added `'turns_since_plot_progress': 0` to the default `state_data` dictionary in the `__init__` method. This field will track how many player turns have passed since the last plot point was achieved.
    *   The `completed_plot_points` field already existed as `db.Column(sa.JSON, default=list)` and is initialized in `state_data`. It will now store the full plot point objects (including `description` and `required` status) when they are completed.

*   **`questforge/services/game_state_service.py`:**
    *   No direct changes were needed. The service loads `state_data` from the `GameState` model, so `turns_since_plot_progress` and the new structure for `completed_plot_points` will be handled as part of the `state_data` dictionary it manages.

## 3. Action Handling & Guidance Logic

*   **`questforge/services/socket_service.py` (`handle_player_action`):**
    *   **Initialization:**
        *   A `STUCK_THRESHOLD` constant (e.g., 3) is defined.
        *   `state_data['turns_since_plot_progress']` is fetched and incremented at the start of each action.
    *   **Next Required Plot Point Identification:**
        *   Logic was added to iterate through the `campaign.major_plot_points` (which are now objects).
        *   It compares these against the `description` of plot points in `state_data.get('completed_plot_points', [])` (which now stores full plot point objects).
        *   The `description` of the first `required: true` plot point not found among the completed descriptions is identified as `next_required_plot_point_desc`.
    *   **Stuck Detection:**
        *   `is_stuck` boolean is determined: `True` if `turns_since_plot_progress >= STUCK_THRESHOLD` AND a `next_required_plot_point_desc` exists.
    *   **AI Call Modification:**
        *   The call to `ai_service.get_response` was updated to pass `is_stuck` and `next_required_plot_point_desc`.
    *   **Plot Point Achievement Processing:**
        *   After receiving the AI response, the code checks if `ai_response_data.get('state_changes', {}).pop('achieved_plot_point', None)` returns a description.
        *   If an `achieved_plot_point_desc` is found:
            *   The full plot point object (matching the description) is retrieved from `campaign.major_plot_points`.
            *   This full object is added to `state_data['completed_plot_points']` if its description is not already present (to avoid duplicates).
            *   `state_data['turns_since_plot_progress']` is reset to `0`.
            *   The `achieved_plot_point` key is removed from `state_changes` before passing to `game_state_service.update_state`.
        *   The modified `state_data` (with updated `turns_since_plot_progress` and `completed_plot_points`) is assigned back to `db_game_state.state_data` before the `game_state_service.update_state` call and subsequent commit.

## 4. AI Service & Prompt Modifications

*   **`questforge/services/ai_service.py` (`get_response`):**
    *   Method signature updated to `get_response(self, game_state: GameState, player_action: str, is_stuck: bool = False, next_required_plot_point: Optional[str] = None)`.
    *   The call to `build_context` now passes `next_required_plot_point`.
    *   The call to `build_response_prompt` now passes `is_stuck` and `next_required_plot_point`.

*   **`questforge/utils/context_manager.py` (`build_context`):**
    *   Method signature updated to `build_context(game_state: GameState, next_required_plot_point: Optional[str] = None)`.
    *   A new section "--- Current Objective/Focus ---" is added to the context string.
        *   If `next_required_plot_point` is provided, it's displayed as "Next Objective: ...".
        *   Otherwise, it falls back to the first overall campaign objective or a generic "Focus on exploring..." message.

*   **`questforge/utils/prompt_builder.py` (`build_response_prompt`):**
    *   Method signature updated to `build_response_prompt(context: str, player_action: str, is_stuck: bool = False, next_required_plot_point: Optional[str] = None)`.
    *   **Objective Adherence:** Added stronger instructions for the AI to evaluate player actions against the "Current Objective/Focus" from the context and to explain narratively if an action attempts to bypass it.
    *   **Player Guidance:** If `is_stuck` is true and `next_required_plot_point` is available, an instruction is added for the AI to subtly weave a hint related to this objective into its narrative.
    *   **Plot Point Achievement:** An instruction was added for the AI: "If the player's action *directly and successfully achieves* the 'Current Objective/Focus', YOU MUST include `\"achieved_plot_point\": \"Description of the achieved plot point (matching the Current Objective/Focus)\"` in your `state_changes` object."
    *   The example for `state_changes` in the prompt now includes `achieved_plot_point`.

## 5. Conclusion Logic Update

*   **`questforge/services/campaign_service.py` (`check_conclusion`):**
    *   **Required Plot Point Pre-Check:**
        *   Before evaluating `conclusion_conditions`, the function now iterates through `campaign.major_plot_points`.
        *   For each plot point object where `required` is true, it checks if its `description` is present among the descriptions of the plot point objects stored in `state_data.get('completed_plot_points', [])`.
        *   If any required plot point is found to be not completed, `check_conclusion` returns `False` immediately.
        *   If all required plot points are completed and there are no other `conclusion_conditions`, the function now returns `True` (considering the game concluded).

This implementation aims to create a more guided and engaging narrative experience by ensuring players address key story elements while still allowing flexibility with optional content.
