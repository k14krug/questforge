# QuestForge Database Schema Plan

This document outlines the detailed database schemas for the core models of the QuestForge application, based on the `questforge_spec.md`. These schemas define the fields, data types, relationships, and constraints for each table.

## 1. User Model (Table: `users`)

Represents a user account in the system.

| Field Name          | Data Type | Constraints                                   | Description                                     |
| :------------------ | :-------- | :-------------------------------------------- | :---------------------------------------------- |
| `id`                | INTEGER   | PRIMARY KEY, AUTOINCREMENT                    | Unique identifier for the user.                 |
| `username`          | TEXT      | UNIQUE, NOT NULL                              | User's chosen username.                         |
| `email`             | TEXT      | UNIQUE, NOT NULL                              | User's email address.                           |
| `password_hash`     | TEXT      | NOT NULL                                      | Hashed password using bcrypt.                   |
| `created_at`        | DATETIME  | NOT NULL, DEFAULT CURRENT_TIMESTAMP           | Timestamp when the user account was created.    |
| `last_login`        | DATETIME  | NULLABLE                                      | Timestamp of the user's last login.             |

**Note on Character Backstories:** Individual character backstories are stored with the `GamePlayer` model. If a historical collection of all backstories generated for a user across different games is required for the `User` profile, this would necessitate further design (e.g., an additional JSON field or a new linking table).

## 2. Template Model (Table: `templates`)

Defines the foundational guidance for AI campaign generation.

| Field Name          | Data Type | Constraints                                   | Description                                     |
| :------------------ | :-------- | :-------------------------------------------- | :---------------------------------------------- |
| `id`                | INTEGER   | PRIMARY KEY, AUTOINCREMENT                    | Unique identifier for the template.             |
| `name`              | TEXT      | UNIQUE, NOT NULL                              | Name of the campaign template.                  |
| `genre`             | TEXT      | NOT NULL                                      | Genre of the campaign (e.g., Fantasy, Sci-Fi).  |
| `core_conflict`     | TEXT      | NOT NULL                                      | The central problem or conflict of the campaign.|
| `world_description` | TEXT      | NOT NULL                                      | Detailed description of the campaign world.     |
| `ai_gm_persona`     | TEXT      | NOT NULL                                      | Default AI Game Master persona for this template.|
| `core_skills`       | JSON      | NOT NULL                                      | JSON array of core skills for the campaign.     |
| `created_by_user_id`| INTEGER   | NOT NULL, FOREIGN KEY (`users.id`)            | User who created this template.                 |
| `created_at`        | DATETIME  | NOT NULL, DEFAULT CURRENT_TIMESTAMP           | Timestamp when the template was created.        |

## 3. Game Model (Table: `games`)

Represents an active or completed game instance.

| Field Name          | Data Type | Constraints                                   | Description                                     |
| :------------------ | :-------- | :-------------------------------------------- | :---------------------------------------------- |
| `id`                | INTEGER   | PRIMARY KEY, AUTOINCREMENT                    | Unique identifier for the game.                 |
| `template_id`       | INTEGER   | NOT NULL, FOREIGN KEY (`templates.id`)        | The template this game was created from.        |
| `creator_user_id`   | INTEGER   | NOT NULL, FOREIGN KEY (`users.id`)            | The user who created this game.                 |
| `current_game_state_id`| INTEGER | NULLABLE, FOREIGN KEY (`game_states.id`)      | Points to the latest `GameState` for this game. |
| `settings`          | JSON      | NOT NULL                                      | Game-specific settings (e.g., `enable_visual_dice_roller`, `expected_session_length_minutes`). |
| `campaign_charter`  | JSON      | NOT NULL                                      | Immutable JSON object defining campaign structure.|
| `cumulative_cost`   | REAL      | NOT NULL, DEFAULT 0.0                         | Total cumulative cost of AI calls for this game.|
| `created_at`        | DATETIME  | NOT NULL, DEFAULT CURRENT_TIMESTAMP           | Timestamp when the game was created.            |
| `started_at`        | DATETIME  | NULLABLE                                      | Timestamp when the game officially started.     |
| `completed_at`      | DATETIME  | NULLABLE                                      | Timestamp when the game was completed.          |

**Note on Campaign Charter Components:** The `campaign_charter` field is an immutable JSON object that contains all the specified Charter Components, including "Core Conflict & Ultimate Goal," "Critical Path Objectives," "Key World Elements," "Immutable Rules," "Interactive Map Layout," and "NPC Generation."

## 4. GamePlayer Model (Table: `game_players`)

Represents a player's participation in a specific game.

| Field Name          | Data Type | Constraints                                   | Description                                     |
| :------------------ | :-------- | :-------------------------------------------- | :---------------------------------------------- |
| `id`                | INTEGER   | PRIMARY KEY, AUTOINCREMENT                    | Unique identifier for the game player entry.    |
| `game_id`           | INTEGER   | NOT NULL, FOREIGN KEY (`games.id`)            | The game this player is part of.                |
| `user_id`           | INTEGER   | NOT NULL, FOREIGN KEY (`users.id`)            | The user associated with this game player.      |
| `character_name`    | TEXT      | NOT NULL                                      | The player's character name in the game.        |
| `character_description`| TEXT   | NULLABLE                                      | Description of the player's character.          |
| `ai_generated_backstory`| TEXT | NULLABLE                                      | AI-generated backstory for the character.       |
| `character_portrait_url`| TEXT | NULLABLE                                      | URL to the character's portrait image.          |
| `ready_status`      | BOOLEAN   | NOT NULL, DEFAULT FALSE                       | Indicates if the player is ready to start/continue the game. |
| `character_sheet`   | JSON      | NOT NULL                                      | JSON object holding character stats and skills. |
| `joined_at`         | DATETIME  | NOT NULL, DEFAULT CURRENT_TIMESTAMP           | Timestamp when the player joined the game.      |

## 5. GameState Model (Table: `game_states`)

Represents the mutable, live state of a game at a given point in time.

| Field Name          | Data Type | Constraints                                   | Description                                     |
| :------------------ | :-------- | :-------------------------------------------- | :---------------------------------------------- |
| `id`                | INTEGER   | PRIMARY KEY, AUTOINCREMENT                    | Unique identifier for this game state snapshot. |
| `game_id`           | INTEGER   | NOT NULL, FOREIGN KEY (`games.id`)            | The game this state belongs to.                 |
| `current_player_id` | INTEGER   | NOT NULL, FOREIGN KEY (`users.id`)            | The user whose turn it is.                      |
| `turn_number`       | INTEGER   | NOT NULL, DEFAULT 1                           | Current turn number of the game.                |
| `current_story_summary`| TEXT   | NULLABLE                                      | AI-generated summary of the story so far.       |
| `current_location`  | TEXT      | NULLABLE                                      | Current location of the party (from interactive map). |
| `active_npcs`       | JSON      | NULLABLE                                      | JSON array/object of active NPCs and their states.|
| `player_states`     | JSON      | NULLABLE                                      | JSON object of player-specific mutable states (e.g., health, inventory). |
| `game_log`          | JSON      | NOT NULL                                      | JSON array of game log entries (narrative, system messages). |
| `completed_objectives`| JSON    | NULLABLE                                      | JSON object tracking the completion status of "Critical Path Objectives" and the "Core Conflict & Ultimate Goal." |
| `discovered_lore_items`| JSON   | NULLABLE                                      | JSON array/object tracking discovered lore items and documents. |
| `last_ai_exchange`  | JSON      | NULLABLE                                      | Last 1-2 raw AI exchanges for context management.|
| `updated_at`        | DATETIME  | NOT NULL, DEFAULT CURRENT_TIMESTAMP           | Timestamp when this game state was last updated.|

**Note on `active_npcs`:** This JSON field should include mutable NPC states such as their `condensed_memory`, current health, location, disposition, and any other dynamic attributes.

**Note on `game_log` Structure:** The `game_log` is a JSON array where each entry should follow a structured format. For example:
- GM Narrative: `{"type": "GM_NARRATIVE", "timestamp": "ISO_DATETIME", "content": "..."}`
- System Message: `{"type": "SYSTEM_MESSAGE", "timestamp": "ISO_DATETIME", "event": "SKILL_CHECK_RESULT", "details": {"roll": 8, "skill_bonus": 2, "total": 10, "difficulty": 15, "outcome": "Failure"}}`
