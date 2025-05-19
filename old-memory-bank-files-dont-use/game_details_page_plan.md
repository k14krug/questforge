# Implementation Plan: Game Details Page

This document outlines the steps to implement a new "Game Details" page for QuestForge. This page will display comprehensive information about a game's original plan, including template details, AI-generated campaign specifics, player information, and creator customizations.

## Feature Request Summary

Users should be able to click a link on the "Join a Game" screen (`questforge/templates/game/list.html`) for each game, leading to a dedicated page showing:
*   Basic game information (name, status, creator, creation date).
*   Associated template name.
*   List of players with their character names and descriptions.
*   All details from the original `Template` (description, genre, conflict, theme, world, scenes, player guidance, difficulty, length, rules).
*   AI-generated `Campaign` specifics (key characters/NPCs, key locations, objectives, major plot points, conclusion conditions).
*   Any `Game.template_overrides` and `Game.creator_customizations`.

## Implementation Phases

### Phase 1: Backend Implementation (Flask)

1.  **Define New Route and View Function:**
    *   **File:** `questforge/views/game.py`
    *   **Route:** `@game_bp.route('/game/<int:game_id>/details', methods=['GET'])`
    *   **View Function:** `game_details(game_id)`
    *   **Imports:** Ensure `Game`, `Template`, `Campaign`, `User`, `GamePlayer` are imported.

2.  **Implement View Function Logic (`game_details`):**
    *   Fetch the `Game` object: `game = Game.query.get_or_404(game_id)`
    *   Access associated `Template`: `template = game.template`
    *   Access associated `Campaign`: `campaign = game.campaign` (handle if `None`)
    *   Fetch player details:
        ```python
        players_details = []
        for assoc in game.player_associations:
            players_details.append({
                'username': assoc.user.username,
                'character_name': assoc.character_name,
                'character_description': assoc.character_description
            })
        ```
    *   Render template:
        ```python
        return render_template('game/details.html', 
                               game=game, 
                               template_data=template,
                               campaign_data=campaign,
                               players_details=players_details)
        ```

### Phase 2: Frontend Implementation (Jinja2 HTML Template)

1.  **Create New HTML Template File:**
    *   **File:** `questforge/templates/game/details.html`
    *   Extend `base.html`.

2.  **Implement Template Structure and Display Logic:**
    *   **Basic Game Info:** Display `game.name`, `game.status`, `game.creator.username`, `game.created_at`, `template_data.name`.
    *   **Players Section:** Loop through `players_details` and display each player's info.
    *   **Original Game Blueprint (from Template):**
        *   Display all relevant fields from `template_data` (e.g., `description`, `genre`, `core_conflict`, `theme`, `world_description`, `scene_suggestions`, `player_character_guidance`, `difficulty`, `estimated_length`).
        *   Format and display `template_data.default_rules` (JSON).
    *   **Generated Campaign Specifics:**
        *   Conditionally display if `campaign_data` exists.
        *   Format and display `campaign_data.key_characters`, `key_locations`, `objectives`, `major_plot_points`, `conclusion_conditions` (all JSON).
        *   Show a message if `campaign_data` is `None`.
    *   **Creator Customizations & Overrides:**
        *   Format and display `game.template_overrides` (JSON).
        *   Format and display `game.creator_customizations` (JSON).
        *   Handle `None` or empty cases.
    *   **JSON Display:** Use loops and conditional logic for readable presentation of JSON data. Consider Jinja2 macros for complex structures if needed.
    *   **Navigation:** Add a "Back to Join Game List" link: `{{ url_for('game.list_games') }}`.

### Phase 3: Linking from "Join a Game" Screen

1.  **Update "Join a Game" List Template:**
    *   **File:** `questforge/templates/game/list.html`
    *   In the game listing loop (`{% for game in games %}`), add a "View Details" link/button for each game.
    *   Link URL: `{{ url_for('game.game_details', game_id=game.id) }}`.
    *   Example:
        ```html
        <td>
            <a href="{{ url_for('game.game_details', game_id=game.id) }}" class="btn btn-sm btn-info">View Details</a>
            <!-- Existing buttons -->
        </td>
        ```

### Phase 4: Testing and Refinement

1.  **Testing Scenarios:**
    *   Game with all data present (template, campaign, players, customizations).
    *   Game where campaign is not yet generated.
    *   Game with no players.
    *   Game with/without template overrides and creator customizations.
    *   Games with empty or `None` JSON fields.
    *   Verify all links and data display.
2.  **Refinement:**
    *   Adjust CSS styling for readability and consistent look and feel.
    *   Ensure clear presentation of all information sections.

## Mock-up Reference

(The textual mock-up previously discussed would be included here for reference during implementation.)

```
--------------------------------------------------------------------------------
Game Details: [Game Name]
--------------------------------------------------------------------------------

Based on Template: [Template Name]
Status: [Game.status]
Created By: [Game.creator.username]
Created At: [Game.created_at]

Players
--------------------------------------------------
*   Player: [User.username]
    Character Name: [GamePlayer.character_name]
    Character Description: [GamePlayer.character_description]
... (repeat for each player)

Original Game Blueprint (from Template)
--------------------------------------------------
Description:
[Template.description]

Genre: [Template.genre]
Core Conflict:
[Template.core_conflict]

Theme: [Template.theme]
Desired Tone: [Template.desired_tone]

World Description:
[Template.world_description]

Scene Suggestions:
[Template.scene_suggestions]

Player Character Guidance (Template):
[Template.player_character_guidance]

Difficulty: [Template.difficulty]
Estimated Length: [Template.estimated_length]

Default Rules (Template):
[Formatted display of Template.default_rules JSON]

Generated Campaign Specifics
--------------------------------------------------
Key Characters (NPCs):
[Formatted display of Campaign.key_characters JSON]

Key Locations:
[Formatted display of Campaign.key_locations JSON]

Objectives:
[Formatted display of Campaign.objectives JSON]

Major Plot Points:
[Formatted display of Campaign.major_plot_points JSON]

Conclusion Conditions:
[Formatted display of Campaign.conclusion_conditions JSON]

Creator Customizations & Overrides (If any)
--------------------------------------------------
Template Overrides:
[Formatted display of Game.template_overrides JSON]

Creator Customizations:
[Formatted display of Game.creator_customizations JSON]

--------------------------------------------------------------------------------
[ Back to Join Game List ]
--------------------------------------------------------------------------------
