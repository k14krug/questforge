# QuestForge Socket.IO Real-Time Communication Events Specification

This document details the exact names and data structures for all Socket.IO real-time communication events within the QuestForge application. These events facilitate real-time updates and interactions between the server and connected clients within game rooms.

## Table of Contents
1.  [Client-to-Server Events](#client-to-server-events)
    1.1 [join_game](#11-join_game)
    1.2 [ready_up](#12-ready_up)
    1.3 [submit_action](#13-submit_action)
    1.4 [player_chat_message](#14-player_chat_message)
2.  [Server-to-Client Events](#server-to-client-events)
    2.1 [game_state_update](#21-game_state_update)
    2.2 [skill_check_initiated](#22-skill_check_initiated)
    2.3 [dice_roll_result](#23-dice_roll_result)
    2.4 [game_log_update](#24-game_log_update)
    2.5 [player_joined](#25-player_joined)
    2.6 [player_left](#26-player_left)
    2.7 [player_ready_status_update](#27-player_ready_status_update)
    2.8 [game_started](#28-game_started)
    2.9 [game_ended](#29-game_ended)
    2.10 [error_message](#210-error_message)

---

## 1. Client-to-Server Events

These events are emitted by the client (frontend) to the server (backend).

### 1.1 `join_game`
-   **Description:** A player requests to join a specific game room.
-   **Emitted by:** Client
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "user_id": "uuid",
      "character_name": "string"
    }
    ```
-   **Server Response:** Server will emit `player_joined` to all clients in the room (including the sender) upon successful join, or `error_message` if failed.

### 1.2 `ready_up`
-   **Description:** A player toggles their ready status in the game lobby.
-   **Emitted by:** Client
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "user_id": "uuid",
      "is_ready": "boolean"
    }
    ```
-   **Server Response:** Server will emit `player_ready_status_update` to all clients in the room upon successful update, or `error_message` if failed.

### 1.3 `submit_action`
-   **Description:** A player submits an action to the AI GM.
-   **Emitted by:** Client
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "game_player_id": "uuid",
      "action_text": "string"
    }
    ```
-   **Server Response:** Server will process the action, potentially emit `skill_check_initiated`, `dice_roll_result`, and `game_log_update`.

### 1.4 `player_chat_message`
-   **Description:** A player sends a chat message to other players in the game room.
-   **Emitted by:** Client
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "user_id": "uuid",
      "username": "string",
      "message": "string"
    }
    ```
-   **Server Response:** Server will broadcast `player_chat_message` to all clients in the room.

---

## 2. Server-to-Client Events

These events are emitted by the server (backend) to connected clients (frontend).

### 2.1 `game_state_update`
-   **Description:** Broadcasts a comprehensive update of the mutable game state. This can be used for initial state sync or major state changes.
-   **Emitted by:** Server
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "game_state": {
        "game_state_id": "uuid",
        "turn_number": "integer",
        "current_story_summary": "string (nullable)",
        "current_location": "string (nullable)",
        "active_npcs": "JSON (array/object)",
        "player_states": "JSON (object of player_id to state)",
        "game_log": "JSON (array of log entries)",
        "completed_objectives": "JSON (object)",
        "discovered_lore_items": "JSON (array/object)",
        "last_ai_exchange": "JSON (nullable)",
        "updated_at": "datetime (ISO 8601)"
      }
    }
    ```

### 2.2 `skill_check_initiated`
-   **Description:** Informs clients that the AI GM has determined a skill check is required for a player's action. This precedes the dice roll.
-   **Emitted by:** Server
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "game_player_id": "uuid",
      "skill": "string",
      "difficulty": "integer",
      "narration_prompt": "string (AI's prompt for outcome narration)",
      "message": "string (human-readable message for UI, e.g., 'A Persuasion check is required.')"
    }
    ```

### 2.3 `dice_roll_result`
-   **Description:** Broadcasts the result of a dice roll and skill check calculation. This event is crucial for the visual dice roller.
-   **Emitted by:** Server
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "game_player_id": "uuid",
      "skill": "string",
      "roll": "integer (e.g., 1-20 for 1d20)",
      "skill_bonus": "integer",
      "total_result": "integer (roll + skill_bonus)",
      "difficulty": "integer",
      "outcome": "string (e.g., 'Success', 'Failure', 'Critical Success', 'Critical Failure')",
      "message": "string (human-readable summary, e.g., 'Roll: 8 + Persuasion(2) = 10 (Difficulty: 15) -> Failure')"
    }
    ```

### 2.4 `game_log_update`
-   **Description:** Provides new entries to the game log. This is a more granular update than `game_state_update` for narrative flow.
-   **Emitted by:** Server
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "new_entry": {
        "timestamp": "datetime (ISO 8601)",
        "event_type": "string (e.g., 'GM_NARRATIVE', 'SYSTEM_MESSAGE', 'PLAYER_CHAT')",
        "actor": "string (e.g., 'player_name', 'AI', 'System')",
        "message": "string",
        "details": "object (optional, context-specific data, e.g., skill check results)"
      }
    }
    ```

### 2.5 `player_joined`
-   **Description:** Notifies all clients in a game room that a new player has joined.
-   **Emitted by:** Server
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "user_id": "uuid",
      "username": "string",
      "character_name": "string",
      "joined_at": "datetime (ISO 8601)"
    }
    ```

### 2.6 `player_left`
-   **Description:** Notifies all clients in a game room that a player has left.
-   **Emitted by:** Server
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "user_id": "uuid",
      "username": "string"
    }
    ```

### 2.7 `player_ready_status_update`
-   **Description:** Notifies all clients in a game room about a player's updated ready status.
-   **Emitted by:** Server
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "user_id": "uuid",
      "is_ready": "boolean"
    }
    ```

### 2.8 `game_started`
-   **Description:** Notifies all clients in a game room that the game has officially started.
-   **Emitted by:** Server
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "started_at": "datetime (ISO 8601)",
      "initial_game_state": {
        "game_state_id": "uuid",
        "turn_number": "integer",
        "current_location": "string",
        "game_log": "JSON (array of initial log entries)"
      }
    }
    ```

### 2.9 `game_ended`
-   **Description:** Notifies all clients in a game room that the game has ended.
-   **Emitted by:** Server
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "ended_at": "datetime (ISO 8601)",
      "final_game_state_summary": "string (e.g., AI-generated epilogue)"
    }
    ```

### 2.10 `error_message`
-   **Description:** Generic error message broadcast to a specific client or all clients in a room.
-   **Emitted by:** Server
-   **Data (JSON):**
    ```json
    {
      "game_id": "uuid (nullable)",
      "code": "integer (e.g., 400, 401, 500)",
      "message": "string (human-readable error description)",
      "details": "object (optional, additional error context)"
    }
