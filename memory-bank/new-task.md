# New Task Plan: Enforcing Plot Points and Preventing Premature Actions

## Objective
Implement logic to prevent players from performing actions that bypass necessary conclusion conditions or major plot points in the QuestForge application. Integrate `Campaign.major_plot_points` into the game flow to guide the narrative.

## Key Areas to Address

1. **Plot Point Tracking:**
   - Utilize the `completed_plot_points` attribute in the `GameState` model to track which plot points have been achieved.
   - Update the game state whenever a plot point is completed.

2. **Identifying the Next Plot Point:**
   - Create a function to determine the next relevant plot point based on the `major_plot_points` list and the `completed_plot_points` in the game state.
   - This function will be called before processing player actions to ensure that players are aware of the current narrative requirements.

3. **AI Prompt Integration:**
   - Modify the `build_player_action_prompt` function in `questforge/utils/prompt_builder.py` to include the current/next plot point as context for the AI.
   - Ensure that the AI generates responses that align with the current plot point.

4. **Action Prevention/Guidance:**
   - In `questforge/services/socket_service.py`, modify the `handle_player_action` function to include checks against the current plot point before allowing actions to proceed.
   - If a player attempts an action that bypasses a plot point, emit an error message and prevent the action from being executed.

5. **Addressing the Log Update Issue:**
   - Investigate the existing issue with the dynamic log updates in `play.html` to ensure that the game log reflects the current state and player actions in real-time.

## Implementation Steps

1. **Modify `questforge/services/socket_service.py`:**
   - Add logic to check the current plot point before processing player actions.
   - Emit error messages if players attempt to perform actions that are not allowed based on the current plot point.

2. **Update `questforge/utils/prompt_builder.py`:**
   - Modify the AI prompt to include the current plot point, ensuring that the AI's responses are contextually relevant.

3. **Create a function to track plot points:**
   - Implement a function that updates the `completed_plot_points` in the `GameState` whenever a plot point is achieved.

4. **Implement Narrative Guidance Strategies:**
   - Implement strategies for narrative feedback, optional plot points, and AI guidance.
   - (See `narrative_guidance_plan.md` for detailed implementation steps).

5. **Test the implementation:**
   - Ensure that the new logic works as intended and that players are appropriately guided through the narrative.
   - Verify that the game log updates dynamically and accurately reflects the game state.
   - Address the pending log update issue (`play.html`).

## Next Steps
Once this plan is approved, I will proceed to implement the changes in the codebase and update the memory bank accordingly.
