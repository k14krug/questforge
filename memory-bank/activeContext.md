# Active Context - QuestForge - 2025-05-05 (Updated after Character Naming)

## Completed Task: Character Naming System

Implemented a system allowing players to optionally provide a character name in the lobby. If left blank, the AI generates one based on the description. This definitive name is now stored, used in AI prompts, and displayed on the game screen.

*   Added `character_name` field to `GamePlayer` model and migrated DB.
*   Updated `lobby.html` UI and JS to handle name input.
*   Updated `socket_service.py` (`handle_update_character_details`) to save name and description.
*   Added `build_character_name_prompt` to `prompt_builder.py`.
*   Added `generate_character_name` method to `ai_service.py`.
*   Integrated AI name generation into `campaign_service.generate_campaign_structure`.
*   Updated `build_campaign_prompt` and `build_response_prompt` to use character names.
*   Updated `context_manager.build_context` to include player names/descriptions.
*   Updated `game.py` view (`play`) to fetch full player details.
*   Updated `play.html` JS to display character name (fallback to username).
*   Created `memory-bank/character_naming_system.md`.

## Current Focus: Game Screen Redesign (`play.html`)

Resuming the task to redesign the main game play screen (`questforge/templates/game/play.html`) based on user feedback to improve layout and user experience.

## Planned Changes (Game Screen Redesign)

*   **Consolidate Game Log & Narrative:** Remove the separate "Game Log" box and integrate historical log entries into the main `#gameStateVisualization` area, making it scrollable.
*   **Restructure Right Column:**
    *   Keep "Available Actions" and "Custom Action" input always visible at the top.
    *   Implement a tabbed interface below the action inputs.
    *   **Tab 1 ("Status"):** Player Locations, Inventory.
    *   **Tab 2 ("Details"):** Objective, Visited Locations, AI Model, API Cost.
*   **Display Player Names:** Modify the backend view (`game.py`) to fetch player usernames and update the frontend JavaScript (`play.html`) to display names instead of user IDs in "Player Locations".
*   **Relocate API Cost:** Move the API cost display from the header into the "Details" tab.
*   **Styling:** Apply subtle thematic styling (e.g., background colors, borders) for a more adventurous feel, prioritizing readability.

## Key Files for Current Task

*   `questforge/templates/game/play.html`: Primary file for HTML structure and JavaScript logic.
*   `questforge/views/game.py`: Backend view function (`play`) to be modified for player name fetching.
*   `questforge/static/css/styles.css`: Potential minor style adjustments.
*   `questforge/static/css/theme.css`: Potential minor style adjustments.
*   `questforge/models/user.py`: User model for fetching usernames.
*   `questforge/models/game.py`: Game and GamePlayer models for fetching player associations.

## Next Steps & Pending Tasks

1.  **Update `progress.md`:** Mark previous tasks as complete and add the "Game Screen Redesign" task.
2.  **Modify Backend View:** Update `questforge/views/game.py` to fetch and pass player names to the template.
3.  **Modify Template HTML:** Restructure `questforge/templates/game/play.html` according to the plan (log consolidation, right column restructure, tabs).
4.  **Modify Template JavaScript:** Update the JS in `play.html` to handle the new structure, display player names, and manage log/narrative display.
5.  **Apply Styling:** Add subtle thematic CSS changes.
6.  **Testing:** Manually test the redesigned game screen.

## Active Decisions & Considerations

*   Keeping primary action controls always visible for better usability.
*   Organizing secondary information into tabs to reduce clutter.
*   Applying minimal styling changes to suggest theme without significant effort.
