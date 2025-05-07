# Narrative Guidance Plan for QuestForge

## Objective
To implement strategies that enhance player engagement with the narrative through effective feedback, flexible plot points, and AI guidance.

## Proposed Strategies

1. **Narrative Feedback:**
   - Implement a system that provides players with feedback on their actions and choices. This could include:
     - In-game notifications that inform players of the consequences of their actions.
     - Visual or auditory cues that reinforce the importance of engaging with the plot.
     - Dynamic narrative responses that change based on player choices, enhancing immersion.

2. **Optional Plot Points:**
   - Structure plot points to allow for flexibility in player progression while still guiding them through the narrative. This will involve:
     - **Distinguishing Required vs. Optional:** Adding a `required: true/false` flag to each plot point object during campaign generation. Only `required: true` points must be completed for the campaign conclusion (in addition to any other `conclusion_conditions`).
     - Allowing players to complete optional points in any order, or skip them.
     - Providing alternative paths or outcomes based on the plot points players choose to engage with.
     - Ensuring that skipping optional plot points does not lead to a complete lack of context or understanding of the story, though it might make achieving required points or the final objective more challenging.

3. **AI Guidance:**
   - Leverage the AI to provide hints or nudges toward plot points without being overly prescriptive. This will involve:
     - **Automatic Trigger:** Implementing logic (likely within `socket_service.py` or `ai_service.py`) to detect if a player seems "stuck" (e.g., repeated failed actions, no progress towards next required plot point after several turns).
     - **Contextual Hints:** When triggered, the AI will be prompted (via `prompt_builder.py`) to subtly weave a hint or suggestion related to the next required plot point or a relevant optional one into its regular narrative response.
     - **Organic Integration:** Ensuring that AI guidance feels natural within the narrative flow and enhances the player's experience rather than feeling like an explicit, out-of-character hint system.

## Detailed Implementation Steps

1.  **Campaign Generation Modifications:**
    *   **`prompt_builder.py` (`build_campaign_prompt`):**
        *   Instruct AI to generate `generated_plot_points` as a list of JSON objects: `[{"description": "...", "required": true/false}, ...]`.
    *   **`campaign_service.py` (`generate_campaign_structure`):**
        *   Update parsing logic to handle the list of plot point objects.
        *   Save the list of objects correctly to `Campaign.major_plot_points`.

2.  **Game State Modifications:**
    *   **`GameState` Model (`models/game_state.py`):**
        *   Ensure `completed_plot_points` (list of strings - the descriptions) exists.
        *   Add `turns_since_plot_progress: 0` to the default `state_data` in `__init__`.
    *   **`game_state_service.py`:**
        *   Ensure the in-memory representation also includes `turns_since_plot_progress`.

3.  **Action Handling & Guidance Logic (`socket_service.py` - `handle_player_action`):**
    *   **Start of Handler:**
        *   Increment `state_data['turns_since_plot_progress']`.
        *   Identify the `next_required_plot_point` description (first required point not in `completed_plot_points`).
        *   Determine `is_stuck` boolean (`turns_since_plot_progress >= STUCK_THRESHOLD`, e.g., 3).
    *   **AI Call Preparation:**
        *   Build context string including `next_required_plot_point` (or fallback text).
        *   Pass `context`, `is_stuck`, and `next_required_plot_point` to `ai_service.get_response`.
    *   **AI Response Processing:**
        *   Check `ai_response_data['state_changes']` for `achieved_plot_point: "description"`.
        *   If found:
            *   Add the description to `GameState.completed_plot_points` (avoid duplicates).
            *   Reset `state_data['turns_since_plot_progress'] = 0`.
            *   Remove `achieved_plot_point` key from `state_changes` before updating state.
    *   **State Update:**
        *   Proceed with `game_state_service.update_state` and DB commit as usual, including the updated `turns_since_plot_progress`.
    *   **Conclusion Check:**
        *   (See step 5 below).

4.  **AI Prompt Modifications (`prompt_builder.py` - `build_response_prompt`):**
    *   **Context Injection:** Add `Current Objective/Focus: [Next Required Plot Point Description or 'Focus on final objective']` to the prompt context.
    *   **Guidance Instruction:** If `is_stuck` is true, add instruction: "The player might be stuck. Subtly weave a hint related to '[Next Required Plot Point Description]' into your narrative description or suggest a relevant action."
    *   **Achievement Instruction:** Add instruction: "If the player's action directly achieves the Current Objective/Focus, YOU MUST include `achieved_plot_point: \"Description of the achieved plot point\"` in your `state_changes`."
    *   **Objective Enforcement Instruction:** Add stronger instructions emphasizing that the AI must evaluate the player's action against the "Current Objective/Focus". If the action attempts to bypass the objective, the AI's narrative response should explain *why* it's difficult or impossible at this time (e.g., "The escape pod controls are unresponsive; perhaps the main power needs stabilizing first?"), unless the narrative context strongly justifies allowing the bypass.

5.  **Conclusion Logic Update (`campaign_service.py` - `check_conclusion`):**
    *   **New Pre-Check:** Before evaluating `conclusion_conditions`, iterate through `campaign.major_plot_points`. For each plot point where `required` is true, check if its `description` is present in `current_state_data.get('completed_plot_points', [])`.
    *   If any required plot point is missing, return `False` immediately.
    *   If all required plot points are present, proceed to evaluate the existing `conclusion_conditions`.

6.  **Testing and Iteration:**
    *   Thoroughly test scenarios involving completing required/optional points, getting stuck, receiving hints, and reaching the conclusion.
    *   Refine the `STUCK_THRESHOLD` and AI prompt instructions based on testing.

## Next Steps
Once this plan is approved, I will proceed to implement the changes in the codebase and update the memory bank accordingly.
