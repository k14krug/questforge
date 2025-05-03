# New Task: Enhance AI Logic for Contextual Awareness

## Objective
Improve the AI's ability to recognize and validate player actions based on the current game state and inventory. This will prevent illogical actions such as "find key" when the player already possesses keys.

## Proposed Enhancements
1. **Contextual Awareness:**
   - Implement checks to determine if a player already has an item before allowing actions that imply finding or acquiring it.
   - Provide appropriate responses for redundant actions (e.g., "You already have the key.").

2. **Action Validation:**
   - Create a validation mechanism that checks the player's current inventory before allowing actions that imply finding items.
   - Ensure the AI responds logically based on the player's inventory state.

3. **Refined Prompting:**
   - Update the AI's prompts to suggest actions relevant to the current context.
   - Avoid prompts that lead to confusion or redundancy.

## Relevant Files
- `questforge/services/socket_service.py`: Modify the action handling logic to include inventory checks.
- `questforge/utils/prompt_builder.py`: Refine AI prompts based on inventory state.
- `questforge/services/ai_service.py`: Update AI logic to incorporate contextual awareness.

## Next Steps
- Implement the proposed changes in the relevant files.
- Test the AI's responses to ensure logical consistency with the game state.
- Document any additional findings or adjustments needed during implementation.

## Notes
- This task is critical for improving player experience and ensuring the AI behaves logically within the game context.
