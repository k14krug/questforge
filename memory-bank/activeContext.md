# Active Context - QuestForge - Narrative Guidance System

## Date: 2025-05-06

## 1. Current Work Focus:
Implementation of the **Narrative Guidance System**. This system aims to enhance player engagement by:
    - Distinguishing between required and optional plot points.
    - Tracking player progress towards required plot points.
    - Detecting if a player is "stuck" (multiple turns without progressing towards a required plot point).
    - Providing AI-driven hints when a player is stuck.
    - Ensuring all required plot points are completed before a campaign can be concluded.
    - Modifying AI prompts to enforce objective adherence and report plot point achievements.

## 2. Recent Changes (Current Task):
The following changes were made to implement the Narrative Guidance System:

*   **`questforge/utils/prompt_builder.py`:**
    *   `build_campaign_prompt`: Updated to instruct AI to generate `generated_plot_points` as a list of objects, each with `description` (string) and `required` (boolean).
    *   `build_response_prompt`:
        *   Signature updated to accept `is_stuck` and `next_required_plot_point`.
        *   Added instructions for AI to:
            *   Adhere to the "Current Objective/Focus".
            *   Provide hints if `is_stuck` is true.
            *   Include `achieved_plot_point: "description"` in `state_changes` upon objective completion.

*   **`questforge/services/ai_service.py`:**
    *   `generate_campaign`: Added validation for the new `generated_plot_points` structure.
    *   `get_response`:
        *   Signature updated to accept `is_stuck` and `next_required_plot_point`.
        *   Passes these new parameters to `build_context` and `build_response_prompt`.

*   **`questforge/models/game_state.py`:**
    *   `GameState.__init__`: Added `'turns_since_plot_progress': 0` to the default `state_data`. `completed_plot_points` will now store full plot point objects.

*   **`questforge/services/socket_service.py` (`handle_player_action`):**
    *   Implemented logic to:
        *   Increment `turns_since_plot_progress` in `state_data`.
        *   Identify the `next_required_plot_point_desc` by comparing campaign plot points with completed ones in `state_data`.
        *   Determine `is_stuck` based on `turns_since_plot_progress` and `STUCK_THRESHOLD`.
        *   Pass `is_stuck` and `next_required_plot_point_desc` to `ai_service.get_response`.
        *   Process `achieved_plot_point` from AI response:
            *   Add the full achieved plot point object to `state_data['completed_plot_points']`.
            *   Reset `state_data['turns_since_plot_progress']` to 0.
            *   Remove `achieved_plot_point` from `state_changes` before further processing.
        *   Persist updated `state_data` (including `turns_since_plot_progress` and `completed_plot_points`) to `db_game_state.state_data`.

*   **`questforge/utils/context_manager.py` (`build_context`):**
    *   Signature updated to accept `next_required_plot_point`.
    *   Added a "--- Current Objective/Focus ---" section to the generated context string, using `next_required_plot_point` or falling back to general campaign objectives.

*   **`questforge/services/campaign_service.py` (`check_conclusion`):**
    *   Added a pre-check to ensure all plot points in `campaign.major_plot_points` marked as `required: true` have their descriptions present in the `state_data.get('completed_plot_points', [])` (which stores objects) before evaluating other `conclusion_conditions`.
    *   If all required plot points are done and no other conclusion conditions exist, the game is considered concluded.

*   **`memory-bank/narrative_guidance_implementation.md`:** Created to document these specific implementation details.

## 3. Next Steps:
*   Update `memory-bank/progress.md` to reflect the completion of the Narrative Guidance System implementation.
*   Thoroughly test the new system:
    *   Campaign generation with required/optional plot points.
    *   Player getting stuck and receiving hints.
    *   Achieving plot points (required and optional).
    *   Conclusion logic with required plot points.
    *   AI behavior regarding objective adherence and plot achievement reporting.
*   Refine `STUCK_THRESHOLD` and AI prompt instructions based on testing if necessary.
*   Address any bugs or issues identified during testing.

## 4. Active Decisions & Considerations:
*   The `STUCK_THRESHOLD` is currently set to 3 within `socket_service.py`. This might need adjustment after testing.
*   The system now stores full plot point objects (dictionaries with `description` and `required` keys) in `GameState.state_data['completed_plot_points']` instead of just descriptions. This was necessary to accurately track completion and differentiate between plot points if multiple had the same description (though unlikely, it's more robust).
*   The `campaign_service.check_conclusion` logic now considers a game concluded if all required plot points are met and no other specific `conclusion_conditions` are defined. This seems like a reasonable default.
