# Phase 5: Enhanced Game Creation

This phase focuses on giving the game creator more control over the campaign generation process by allowing them to add specific customizations on top of the selected template.

**Note:** This phase requires more detailed planning before implementation begins.

## Goals & Initial Thoughts

1.  **Creator Customizations:**
    *   **Goal:** Allow the game creator to input additional details, instructions, or overrides *after* selecting a template but *before* campaign generation. This aims to further tailor the AI's output beyond the template's general guidance.
    *   **Potential Customization Areas (Needs Refinement):**
        *   Specific NPCs to include (name, role, basic description).
        *   Key locations to feature.
        *   Specific plot hooks or starting situations.
        *   Minor rule modifications or emphasis points.
        *   Exclusions (e.g., "avoid themes of X").
    *   **Tasks (High-Level):**
        *   **UI Design:** Design and implement a new step or form in the game creation flow (likely after template selection in `questforge/templates/game/create.html` or a subsequent step).
        *   **Data Storage:** Determine the best way to store these customizations. Options:
            *   Add a new JSON field (e.g., `creator_customizations`) to the `Game` model (`questforge/models/game.py`). Requires DB migration.
            *   Store temporarily and pass directly to the generation service (less persistent). (Model field seems better).
        *   **Backend Logic:**
            *   Create a new view function/API endpoint (e.g., in `questforge/views/game.py`) to handle saving the customization form data to the chosen storage location.
            *   Modify the game creation/lobby logic to ensure these customizations are loaded when `handle_start_game` is triggered.
        *   **Prompt Integration:** Modify `build_campaign_prompt` in `questforge/utils/prompt_builder.py` to incorporate these `creator_customizations` into the prompt sent to the AI, instructing it to prioritize or integrate them alongside the template and player data.

## Planning Considerations

*   How structured should the customization input be? Free text vs. specific fields?
*   How should conflicts between template guidance and creator customizations be handled in the prompt?
*   What is the impact on the complexity of `build_campaign_prompt`?
*   How much detail can realistically be passed to the AI within token limits?
