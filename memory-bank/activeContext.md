# Active Context - QuestForge - Narrative Guidance System

## Date: 2025-10-05

## 1. Current Work Focus:
**Revising Plot Point Completion Strategy.**
The primary focus is to design and document a new strategy for more robust and flexible plot point completion, addressing issues with non-sequential progression and evaluation of complex objectives.

## 2. Recent Changes (In Progress/Completed Task):
*   **Plot Point Completion Strategy Revision (Planning & Documentation Phase):**
    *   **Problem Analysis (Completed):** Identified weaknesses in the current AI-driven plot point completion mechanism, including reliance on AI for complex lookups, difficulty with non-sequential completion, and challenges with multi-faceted plot points.
    *   **Solution Design (Completed):** Designed a new "Multi-Stage AI Processing with Atomic Plot Points" strategy. This involves:
        *   Decomposing complex plot points into smaller, atomic units during campaign design.
        *   A Stage 1 AI call for narrative generation and general game state updates (without direct plot completion ID requests).
        *   A system-side "plausibility check" to identify potentially completed atomic plot points.
        *   Conditional Stage 2 focused AI calls for each plausible atomic plot point, using richer game state context, to get a `completed: true/false` status and a confidence score.
        *   System aggregation of Stage 2 results to update `GameState.state_data['completed_plot_points']`.
    *   **Documentation (Completed):** Created `memory-bank/plot_point_completion_strategy_v2.md` detailing the problem, the new multi-stage solution, its benefits, and key implementation areas.
*   **Difficulty Setting Enhancement (Completed & Awaiting User Testing):**
    *   (Details omitted for brevity - this task was completed prior to the current focus on plot point strategy)
*   **Slash Command System (Completed):**
    *   (Details omitted for brevity)
*   (Other previously completed items like Sticky Navbar, Login with Username, etc., are omitted for brevity as they are not part of the current active work.)

## 3. Next Steps:
*   **Plot Point Completion Strategy Implementation:**
    *   Discuss and finalize the details of the "Multi-Stage AI Processing with Atomic Plot Points" strategy with the user.
    *   Proceed with implementing the changes outlined in `memory-bank/plot_point_completion_strategy_v2.md`, including modifications to:
        *   Campaign design principles (favoring atomic plot points).
        *   `socket_service.py` (multi-stage flow, plausibility check).
        *   `ai_service.py` (new method for Stage 2 calls, adapt existing for Stage 1).
        *   `prompt_builder.py` (new prompt for Stage 2, adapt existing for Stage 1).
        *   Ensuring `GameState.state_data` is sufficiently detailed by Stage 1 AI.
    *   Update `memory-bank/progress.md` to reflect the commencement and progress of this implementation.
    *   Once implemented, thorough testing will be required.
*   **Difficulty Setting Enhancement (User Testing Pending):** Awaiting user feedback on the effectiveness of the previously implemented difficulty prompt changes.

## 4. Active Decisions & Considerations:
*   The new plot point completion strategy aims to significantly improve reliability and flexibility by using decomposed atomic plot points and multi-stage, state-aware AI evaluations.
*   The Stage 1 AI call will focus on narrative and general state, while Stage 2 calls will handle specific plot point completion checks.
*   The richness of `GameState.state_data` updated by Stage 1 AI is critical for the success of Stage 2 evaluations.
*   The system-side "plausibility check" is important for managing the number of Stage 2 AI calls, balancing accuracy with performance and cost.
*   Slash command processing is centralized in `socketClient.performAction` on the client-side, emitting distinct events (`slash_command` or `player_action`) to the backend.
*   The `ApiUsageLog` model in `questforge/models/api_usage_log.py` does *not* include `player_id` or `endpoint` fields. Logging calls have been updated accordingly.
*   The primary strategy for constraining AI responses is through detailed prompt engineering in `build_response_prompt`.
*   Secondary consideration: adjusting `max_tokens` in `ai_service.py` if prompt changes alone are insufficient.
*   NPC details are displayed using data from `campaign.key_characters`. The template logic handles both dictionary and list-of-objects structures for this data, and also for NPC attributes.
*   Game deletion is a hard delete, removing the game and its associated records from the database. Creator comparison uses `game.creator.id`.
*   The "Join Game" screen (`game/list.html`) now displays all games and allows re-entry into 'completed' games by linking them to the play view.
*   Completed game status badges are now green (`bg-success`) on `game/list.html`.
*   The `STUCK_THRESHOLD` (related to the prior Narrative Guidance System) is set to 3 in `socket_service.py`. This was part of a previous feature but worth noting if further gameplay tuning is needed.
*   The ID-based plot point system stores full plot point objects in `GameState.state_data['completed_plot_points']`.
*   `campaign_service.check_conclusion` now robustly checks required plot points by ID and evaluates `conclusion_conditions` from the campaign against `state_data`.
