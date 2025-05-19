# Plot Point Completion Strategy v2

## 1. The Problem (The "Why")

The previous system for determining plot point completion in QuestForge faced several challenges:

*   **Reliance on AI for Complex Lookup:** The AI was tasked with identifying the "Current Objective/Focus" (a description) and then finding its corresponding `id` from a list of all plot points provided in the context. This "description-to-ID lookup" was prone to errors if descriptions didn't match exactly or if the AI misinterpreted the instruction.
*   **Difficulty with Non-Sequential Completion:** The system was primarily oriented towards players completing a system-identified "next required plot point." It didn't robustly handle scenarios where players might complete optional plot points or required plot points out of the expected sequence.
*   **Challenges with Multi-Faceted Plot Points:** Evaluating whether a complex plot point with multiple conditions (e.g., "Reach location X, obtain item Y, and speak to character Z") was completed by a single player action and its immediate narrative was difficult and unreliable.
*   **Single-Turn Expectation:** The previous framing implied that a plot point's completion was judged solely on the immediate outcome of the current turn, which is often unrealistic for objectives requiring multiple steps or specific evolving game states.

**Goal of this Revision:** To implement a more reliable, flexible, and robust system that:
*   Accurately tracks the completion of any defined plot point.
*   Supports non-sequential player progression.
*   Handles plot points that require multiple turns or specific game state conditions to be met.
*   Reduces the cognitive load on any single AI call to improve accuracy.

## 2. The Solution (The "How"): Multi-Stage AI Processing with Atomic Plot Points

This strategy revises how plot point completion is determined by decomposing complex objectives and using a series of more focused AI interactions and system logic.

### Core Principle 1: Decomposition of Plot Points
Complex objectives that have multiple distinct conditions for success should be broken down into smaller, **atomic plot points** during campaign design or AI-driven campaign generation. Each atomic plot point should represent a single, clear condition.

*   **Example:**
    *   **Original Complex Plot Point:** `ID: escape_sequence`, `Description: "Players reach the Escape Pod Bay, choose the correct pod, and avoid Security Officer Jax."`
    *   **Decomposed Atomic Plot Points:**
        1.  `ID: pp_reach_bay`, `Description: "Player is in the Escape Pod Bay."`
        2.  `ID: pp_choose_pod`, `Description: "Player has chosen/identified the correct escape pod."`
        3.  `ID: pp_handle_jax`, `Description: "Player has successfully avoided or dealt with Security Officer Jax in the Escape Pod Bay."`
*   An "umbrella" or parent plot point (e.g., `pp_escape_sequence_complete`) can then be systemically marked as complete when all its constituent atomic plot points are achieved.

### Core Principle 2: State-Aware Evaluation
The completion of an atomic plot point is not judged solely on the immediate narrative of the last player action. Instead, it's evaluated against the **accumulated and current `GameState.state_data`**, which reflects the history of player actions and AI responses.

### The Multi-Stage Process per Turn:

**Stage 1: Narrative Generation & General State Update (Main AI Call)**
*   **Player Action:** The player submits their action.
*   **AI's Role (Prompt 1):**
    *   Generate a compelling narrative response to the player's action.
    *   Update the *general game state*. This includes:
        *   Player's new location.
        *   Changes to inventory.
        *   Status of NPCs (e.g., `NPCs_present_in_location: ["Officer Jax"]`, `jax_status: "alerted"`).
        *   Status of key world objects or environmental conditions.
    *   **Crucially, this AI call is NOT asked to identify or return completed plot point IDs.** Its focus is on narrative and world simulation.
*   **Output:** Narrative text, a dictionary of general state changes, and suggested available actions for the player.
*   **System Action:** The system updates `GameState.state_data` with these general changes from the AI.

**Stage 2: System-Side "Plausibility Check"**
*   **System's Role:** After Stage 1 updates the general game state:
    *   The system iterates through *all atomic plot points* defined in the campaign that are still *pending* (not yet in `GameState.state_data['completed_plot_points']`).
    *   For each pending atomic plot point, the system performs a quick heuristic check: "Is it *plausible* that the player's last action and the resulting narrative/state changes from Stage 1 *could have* completed *this specific* atomic plot point?"
    *   This check aims to narrow down the list of plot points that require a more detailed AI evaluation, optimizing performance and cost. Heuristics might include:
        *   Keyword matching between the plot point description and the Stage 1 narrative.
        *   Checking if the current location in `GameState.state_data` is relevant to the plot point.
        *   Checking if NPCs or items mentioned in the plot point description are currently active or present in the state.

**Stage 3: Focused AI Completion Analysis (Conditional Second AI Call(s))**
*   **Trigger:** For each atomic plot point deemed "plausible" by the Stage 2 system check.
*   **AI's Role (Prompt 2 - one call per plausible plot point):**
    *   **Input to this AI call:**
        1.  The specific atomic plot point's `id` and `description` (e.g., `ID: pp_handle_jax`, `Description: "Player has successfully avoided or dealt with Security Officer Jax in the Escape Pod Bay."`).
        2.  The *full current `GameState.state_data`* (as updated by Stage 1). This provides the AI with the complete context of the world.
        3.  The player's original action from the current turn.
        4.  The narrative generated by the Stage 1 AI in the current turn.
    *   **AI Instruction:** "Considering the objective for plot point `[ID]` is `'[description]'`, and given the current game state `[state_data]`, the player's action `'[action]'`, and the immediate narrative result `'[narrative from Stage 1]'`, was this specific atomic plot point `[ID]` directly and successfully completed? Respond ONLY with JSON: `{\"plot_point_id\": \"[ID]\", \"completed\": true/false, \"confidence_score\": <a number between 0.0 and 1.0>}`."
*   **Output (for each call):** A JSON object indicating if *that specific atomic plot point* was completed, along with a confidence score.

**Stage 4: System Aggregation & Final State Update**
*   **System's Role:**
    *   Collect all responses from the Stage 3 AI calls.
    *   For each plot point where the AI responded `completed: true` (and optionally, the `confidence_score` is above a defined threshold, e.g., 0.75), the system adds the full plot point object to `GameState.state_data['completed_plot_points']`.
    *   If any *required* atomic plot point was newly completed, `GameState.state_data['turns_since_plot_progress']` is reset.
    *   All changes to `GameState.state_data` are committed to the database.
*   **Output to Client:** The narrative from Stage 1 is sent to the player, along with the fully updated game state (which now reflects any newly completed plot points). The `check_conclusion` function will then operate on this updated state.

## 3. Benefits of this Strategy

*   **Robust Non-Sequential Completion:** Players can complete any available atomic plot point if their actions and the resulting game state satisfy its conditions.
*   **Increased Accuracy:** Breaking the AI's task into a narrative generation step and separate, focused completion-check steps for atomic objectives should improve the reliability of detecting completed plot points.
*   **Handles Multi-Turn Objectives:** Atomic plot points are evaluated against the accumulated game state, allowing their conditions to be met over several turns.
*   **Clearer Game Design:** Encourages the design of campaigns with well-defined, atomic objectives.
*   **Manageable AI Complexity:** Each AI call has a more constrained and specific task.
*   **Tunable Performance/Cost:** The "plausibility check" can be tuned to balance the number of Stage 3 AI calls (affecting cost and latency) against the thoroughness of checking every pending plot point.

## 4. Key Implementation Areas

*   **Campaign Design/Generation:** Prompts for AI campaign generation (or manual template design guidelines) must emphasize the creation of atomic plot points. Consider how to represent dependencies between atomic plot points if needed (e.g., `pp_choose_pod` can only be completed if `pp_reach_bay` is complete).
*   **`GameState.state_data` Richness:** The Stage 1 AI must be prompted to update `state_data` with sufficient detail (e.g., precise location, list of NPCs present and their general status, status of key items/world elements) so that Stage 3 AI calls have enough context.
*   **`socket_service.py`:** Major refactoring of `handle_player_action` to implement the multi-stage flow, including the system-side plausibility check logic.
*   **`ai_service.py`:**
    *   The existing `get_response` method will be adapted for Stage 1 (narrative & general state, no plot completion IDs).
    *   A new method (e.g., `check_atomic_plot_completion`) will be created for Stage 3 AI calls.
*   **`prompt_builder.py`:**
    *   The existing `build_response_prompt` will be modified for Stage 1.
    *   A new prompt function (e.g., `build_plot_completion_check_prompt`) will be created for Stage 3.
*   **Parallelism (Optional Optimization):** Investigate if multiple Stage 3 AI calls can be made in parallel to reduce overall turn latency.
