# ID-Based Plot Point System Upgrade Plan

## 1. Objective
Refactor the existing QuestForge narrative guidance and campaign conclusion systems to utilize a robust ID-based system for tracking Major Plot Point completion. This upgrade aims to improve reliability and simplify the logic for determining plot progression and campaign conclusion.

## 2. Current System Overview & Need for Upgrade
The QuestForge application currently features a Narrative Guidance System and campaign conclusion logic that tracks Major Plot Points by matching their `description` strings. While functional, this approach has proven brittle:
*   Minor variations in AI-generated descriptions for achieved plot points can lead to matching failures.
*   Reliance on string matching for a core progression mechanic is inherently less robust than using unique identifiers.

This plan details the upgrade to an ID-based system, where each Major Plot Point will be assigned a unique ID. This ID will become the primary means of tracking and verifying plot point completion.

**Assumption:** This plan will be executed on a codebase that has been reverted to its state *before* any recent attempts to fix campaign conclusion issues. It outlines all necessary changes to implement the ID-based plot point system as an upgrade to the existing functionalities.

## 3. Action Plan: Upgrading to ID-Based Plot Point Tracking

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
    *   Modify instructions for `generated_plot_points`. Each plot point object must now include:
        *   `id` (string): A unique, simple identifier (e.g., `pp_001`, `obj_reactor`). Instruct AI to ensure uniqueness within the campaign.
        *   `description` (string): Textual description.
        *   `required` (boolean): `true` if essential, `false` if optional.
    *   Update prompt examples (e.g., `[{"id": "pp_001", "description": "Players awaken...", "required": true}, ...]`).

*   **B. Validate AI-Generated Plot Points (`questforge/services/ai_service.py` -> `generate_campaign`):**
    *   Enhance validation for `generated_plot_points` to ensure each object has `id` (string), `description` (string), and `required` (boolean).
    *   Verify uniqueness of `id` values within the `generated_plot_points` list for the campaign. Fail generation or attempt correction if IDs are not unique.

*   **C. Store Plot Points with IDs (`questforge/services/campaign_service.py` -> `generate_campaign_structure`):**
    *   Ensure `new_campaign.major_plot_points` correctly stores the plot point objects, now including their IDs.

---
**Phase 2: Auto-Completing Initial Required Plot Point (ID-Based)**
---
*   **A. Modify `questforge/services/campaign_service.py` -> `generate_campaign_structure`:**
    *   After `new_campaign` and `initial_game_state` creation (before commit):
        *   If the first plot point in `new_campaign.major_plot_points` exists and is `required: True`.
        *   Initialize `initial_game_state.state_data['completed_plot_points']` as an empty list if needed.
        *   Append the full first plot point object (with its `id`) to `initial_game_state.state_data['completed_plot_points']`.
        *   Log this action (ID and description).

---
**Phase 3: Updating Action Handling and AI Interaction for ID-Based Plot Points**
---
*   **A. Update AI Context Building (`questforge/utils/context_manager.py` -> `build_context`):**
    *   When providing "Major Plot Points" in the AI context, include the `id` for each plot point (e.g., `Major Plot Points: [{"id": "pp_001", "description": "...", "required": true}, ...]`).
    *   "Current Objective/Focus" will still primarily use the `description` of the next required plot point, but the system will internally know its `id`.

*   **B. Update AI Prompt for Action Responses (`questforge/utils/prompt_builder.py` -> `build_response_prompt`):**
    *   Change "Plot Point Achievement" instruction:
        > "   - **Plot Point Achievement:** If the player's action *directly and successfully achieves* the 'Current Objective/Focus', YOU MUST include an `achieved_plot_point_id` key in your `state_changes` object. The value for this key MUST BE THE EXACT `id` (e.g., `\"pp_001\"`) of the 'Current Objective/Focus' that was completed, as provided in the 'Major Plot Points' list in the Game Context. Do NOT return the description here."
    *   Update `state_changes` example: `Example: {'location': '...', 'achieved_plot_point_id': 'pp_001', 'bomb_disabled': true}`.
    *   Retain instruction for "Critical Event Flags" (like `bomb_disabled: true`) as these are separate and vital for `conclusion_conditions`.

*   **C. Modify Plot Point Processing in Action Handler (`questforge/services/socket_service.py` -> `handle_player_action`):**
    *   **Next Required Plot Point Identification:**
        *   Extract `id`s from `state_data.get('completed_plot_points', [])` into `completed_ids`.
        *   Find the first plot point in `campaign.major_plot_points` that is `required: true` AND its `id` is NOT in `completed_ids`.
        *   Store its `id` as `next_required_plot_point_id` and `description` as `next_required_plot_point_desc` for AI context.
    *   **Processing AI's `achieved_plot_point_id`:**
        *   Look for `achieved_plot_point_id` from AI's `state_changes`.
        *   If found, retrieve the full plot point object from `campaign.major_plot_points` by matching this `id`.
        *   If valid object found and its `id` not already in `completed_ids` (derived from `state_data['completed_plot_points']`), add the full object to `state_data['completed_plot_points']`.
        *   Log ID and description of completed plot point.
        *   If ID not found in campaign plot points, log a warning.
        *   Reset `state_data['turns_since_plot_progress']` to `0` if AI reports an `achieved_plot_point_id`.
        *   Ensure modified `state_data` is saved.

---
**Phase 4: Updating Conclusion Logic for ID-Based Plot Points**
---
*   **A. Modify `questforge/services/campaign_service.py` -> `check_conclusion`:**
    *   **Required Plot Point Pre-Check:**
        *   Extract `id`s from `state_data.get('completed_plot_points', [])` into `completed_ids`.
        *   Iterate `campaign.major_plot_points`. For each `required: true` plot point, check if its `id` is in `completed_ids`.
        *   If any `required: true` plot point's `id` is missing, `all_required_completed` is `false`. Log missing ID/description and return `False`.
        *   If all `required: true` plot points are completed, `all_required_completed` is `true`.
    *   The rest of `check_conclusion` (evaluating `conclusion_conditions` like `bomb_disabled`) remains unchanged and critical.
    *   **Comprehensive Logging:** Ensure detailed debug logging within `check_conclusion` covers all aspects of this ID-based check and the subsequent `conclusion_conditions` evaluation.

---
**Phase 5: Verification Strategy**
---
*   **Campaign Generation & Initial State (Phases 1 & 2):**
    *   **Verify:** `Campaign.major_plot_points` stores objects with unique `id`, `description`, `required`.
    *   **Verify:** `GameState.state_data['completed_plot_points']` (initial) contains the first `required: true` plot point object. Logs confirm auto-completion.
*   **Action Handling & AI Interaction (Phase 3):**
    *   **Verify:** `socket_service.py` logs show correct `next_required_plot_point_id` and `desc` for AI.
    *   **Verify:** AI response includes `achieved_plot_point_id` with the correct ID.
    *   **Verify:** `socket_service.py` logs confirm plot point object (by ID) added to `completed_plot_points`.
*   **Conclusion Logic (Phase 4):**
    *   **Verify:** `check_conclusion` logs show `completed_ids` used for `all_required_completed` check.
    *   **Verify:** AI sets critical event flags (e.g., `bomb_disabled: true`) when appropriate, and `check_conclusion` evaluates these correctly.
*   **End-to-End Test:**
    *   Play a campaign where all `required: true` plot points (by ID) AND all `conclusion_conditions` are met.
    *   **Verify:** Campaign concludes; `game_concluded` event emitted. `check_conclusion` logs show all checks passing.

This ID-based upgrade should significantly enhance the reliability of plot progression and campaign conclusions.
