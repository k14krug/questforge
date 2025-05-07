# Campaign Conclusion Remediation Plan (ID-Based Plot Points)

## 1. Core Objective
Implement an ID-based system for Major Plot Points to ensure robust tracking of their completion, and verify that the campaign conclusion logic correctly uses this system alongside existing `conclusion_conditions`.

## 2. Background & Problem Statement
Previous attempts to fix campaign conclusion issues revealed that relying on matching plot point `description` strings was brittle. Even with normalization and stricter AI prompting, mismatches could occur. The most reliable way to track plot point completion is by assigning unique IDs to each plot point and using these IDs for all tracking and completion logic. This plan outlines the steps to refactor the system to use ID-based plot points.

This plan assumes the codebase will be reverted to its state *before* the previous multi-step debugging task for campaign conclusion began. It outlines all necessary changes to implement ID-based plot points from that baseline.

## 3. Action Plan: Implementing ID-Based Plot Point Tracking

**Target Files for Modifications:**
*   `questforge/utils/prompt_builder.py` (AI prompts for campaign generation and action responses)
*   `questforge/services/ai_service.py` (Validation of AI-generated campaign data)
*   `questforge/services/campaign_service.py` (Campaign generation, initial state, and conclusion logic)
*   `questforge/services/socket_service.py` (Action handling, plot point completion)
*   `questforge/utils/context_manager.py` (Context building for AI)

---
**Phase 1: Modifying Campaign Generation to Include Plot Point IDs**
---
*   **A. Update AI Prompt for Campaign Generation (`questforge/utils/prompt_builder.py` -> `build_campaign_prompt`):**
    *   Modify the instructions for `generated_plot_points`. The AI must now generate each plot point object with three keys:
        *   `id` (string): A unique, simple, and consistent identifier for the plot point (e.g., `pp_001`, `pp_intro`, `obj_reactor_stabilized`). The AI should be instructed to ensure these IDs are unique within the list of plot points for a single campaign.
        *   `description` (string): The textual description of the plot point.
        *   `required` (boolean): `true` if the plot point is essential for campaign completion, `false` if optional.
    *   Update the example for `generated_plot_points` in the prompt to reflect this new structure (e.g., `[{"id": "pp_001", "description": "Players awaken...", "required": true}, ...]`).

*   **B. Validate AI-Generated Plot Points (`questforge/services/ai_service.py` -> `generate_campaign` method, within its validation logic for AI response):**
    *   After receiving the campaign structure from the AI, enhance the validation for `generated_plot_points`.
    *   Ensure each object in the `generated_plot_points` list contains the string `id`, string `description`, and boolean `required` keys.
    *   Add a check to ensure that all `id` values within the `generated_plot_points` list are unique for that campaign. If not, the generation should be considered failed or an attempt should be made to regenerate/fix IDs. (For simplicity in the first pass, failing on non-unique IDs is acceptable).

*   **C. Store Plot Points with IDs (`questforge/services/campaign_service.py` -> `generate_campaign_structure`):**
    *   The existing logic that assigns `ai_response_data.get('generated_plot_points', [])` to `new_campaign.major_plot_points` will now store plot point objects that include these IDs. No change is needed here other than ensuring the AI provides them.

---
**Phase 2: Auto-Completing Initial Required Plot Point (ID-Based)**
---
*   **A. Modify `questforge/services/campaign_service.py` -> `generate_campaign_structure`:**
    *   After `new_campaign` and `initial_game_state` are created (but before commit).
    *   Check if `new_campaign.major_plot_points` is a non-empty list.
    *   If the first plot point object (`new_campaign.major_plot_points[0]`) exists and its `required` field is `True`.
    *   Initialize `initial_game_state.state_data['completed_plot_points']` as an empty list if it doesn't exist.
    *   Append the *full first plot point object* (which now includes its `id`) to `initial_game_state.state_data['completed_plot_points']`.
    *   Log this action, including the ID and description of the auto-completed plot point.

---
**Phase 3: Updating Action Handling and AI Interaction for ID-Based Plot Points**
---
*   **A. Update AI Context Building (`questforge/utils/context_manager.py` -> `build_context`):**
    *   When constructing the "Major Plot Points" section of the context string provided to the AI for action responses, each plot point listed **MUST** now include its `id`.
    *   Example format for AI context: `Major Plot Points: [{"id": "pp_001", "description": "Players awaken...", "required": true}, {"id": "pp_002", ...}]`.
    *   The "Current Objective/Focus" will still be primarily the `description` of the next required plot point, but the system will know its `id`.

*   **B. Update AI Prompt for Action Responses (`questforge/utils/prompt_builder.py` -> `build_response_prompt`):**
    *   Change the instruction for "Plot Point Achievement":
        > "   - **Plot Point Achievement:** If the player's action *directly and successfully achieves* the 'Current Objective/Focus', YOU MUST include an `achieved_plot_point_id` key in your `state_changes` object. The value for this key MUST BE THE EXACT `id` (e.g., `\"pp_001\"`) of the 'Current Objective/Focus' that was completed, as provided in the 'Major Plot Points' list in the Game Context. Do NOT return the description here."
    *   Update the example for `state_changes` in the prompt: `Example: {'location': 'Cave Entrance', 'items_added': ['torch'], 'achieved_plot_point_id': 'pp_001', 'bomb_disabled': true}`.
    *   The instruction for "Critical Event Flags" (like `bomb_disabled: true`) should remain, as these are separate from plot point ID achievement and are used for `conclusion_conditions`.

*   **C. Modify Plot Point Processing in Action Handler (`questforge/services/socket_service.py` -> `handle_player_action`):**
    *   **Next Required Plot Point Identification:**
        *   Fetch the list of completed plot point objects from `state_data.get('completed_plot_points', [])`. Extract their `id`s into a list/set: `completed_ids`.
        *   Iterate through `campaign.major_plot_points`. The first plot point object that has `required: true` AND whose `id` is *not* in `completed_ids` is the next required one.
        *   Store its `id` as `next_required_plot_point_id` and its `description` as `next_required_plot_point_desc`. These are passed to the AI.
    *   **Processing AI's `achieved_plot_point_id`:**
        *   After getting the AI response, look for `achieved_plot_point_id = current_state_changes.pop('achieved_plot_point_id', None)`.
        *   If an `achieved_plot_point_id` is provided by the AI:
            *   Find the corresponding full plot point object from `campaign.major_plot_points` by matching this `id`.
            *   If a valid object is found:
                *   Ensure `state_data['completed_plot_points']` is a list.
                *   Check if a plot point with this `id` is already in `state_data['completed_plot_points']`.
                *   If not already completed, add the full plot point object (retrieved from the campaign definition by ID) to `state_data['completed_plot_points']`.
                *   Log the ID and description of the completed plot point.
            *   Else (if ID doesn't match any campaign plot point), log a warning.
            *   Reset `state_data['turns_since_plot_progress']` to `0` (as the AI believed a plot point was achieved).
        *   Ensure the modified `state_data` (with updated `completed_plot_points` and `turns_since_plot_progress`) is saved.

---
**Phase 4: Updating Conclusion Logic for ID-Based Plot Points**
---
*   **A. Modify `questforge/services/campaign_service.py` -> `check_conclusion`:**
    *   **Required Plot Point Pre-Check:**
        *   Fetch the list of completed plot point objects from `state_data.get('completed_plot_points', [])`. Extract their `id`s into a list/set: `completed_ids`.
        *   Iterate through `campaign.major_plot_points`. For each plot point object where `required` is `true`:
            *   Check if its `id` is present in `completed_ids`.
            *   If any `required: true` plot point's `id` is *not* found in `completed_ids`, then `all_required_completed` is `false`. Log the missing plot point's ID and description. Break and return `False` from `check_conclusion`.
        *   If the loop completes and all `required: true` plot points are found in `completed_ids`, then `all_required_completed` is `true`.
    *   The rest of the `check_conclusion` logic (evaluating `conclusion_conditions` like `bomb_disabled`) remains the same.

---
**Phase 5: Verification Strategy**
---
*   **After Phase 1 & 2 (Campaign Generation & Initial Plot Point):**
    *   Start a new game.
    *   **Verify:** `Campaign.major_plot_points` in the database contains plot point objects, each with a unique `id`, `description`, and `required` status.
    *   **Verify:** `GameState.state_data['completed_plot_points']` for the initial state contains the full object of the first `required: true` plot point.
    *   **Verify:** Logs confirm the auto-completion, showing the ID and description.
*   **After Phase 3 (Action Handling & AI Interaction):**
    *   Play through a scenario where a `required: true` plot point (other than the first) should be completed.
    *   **Verify:** `socket_service.py` logs show the correct `next_required_plot_point_id` and `next_required_plot_point_desc` being sent to the AI.
    *   **Verify:** The AI's response in the logs includes `achieved_plot_point_id` with the correct ID.
    *   **Verify:** `socket_service.py` logs confirm it found the plot point object by ID from the campaign definition and added it to `completed_plot_points`.
    *   **Verify:** `turns_since_plot_progress` is reset.
*   **After Phase 4 (Conclusion Logic):**
    *   In `check_conclusion` debug logs:
        *   **Verify:** `completed_ids` are correctly extracted.
        *   **Verify:** The check for `all_required_completed` correctly uses these IDs.
    *   Play through a scenario where a `conclusion_condition` (e.g., `bomb_disabled: true`) should be met.
    *   **Verify:** `socket_service.py` logs show the AI's `state_changes` includes the relevant flag (e.g., `bomb_disabled: true`).
    *   **Verify:** `check_conclusion` logs show this flag present in `state_data` and the corresponding `conclusion_condition` evaluates to `true`.
*   **Final Test:**
    *   Play a campaign through to a point where all `required: true` plot points (verified by ID) AND all `conclusion_conditions` are met.
    *   **Verify:** The campaign concludes, and a `game_concluded` event is emitted. Logs from `check_conclusion` should show all checks passing.

This ID-based approach is more complex to implement initially but will provide a much more reliable foundation for plot progression and campaign conclusion.
