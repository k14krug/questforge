# QuestForge API Endpoints Specification

This document details the precise API endpoints, HTTP methods, and JSON request/response structures for all backend interactions within the QuestForge application.

## Table of Contents
1.  [Authentication Endpoints](#authentication-endpoints)
2.  [User Management Endpoints](#user-management-endpoints)
3.  [Template Management Endpoints](#template-management-endpoints)
4.  [Game Management Endpoints](#game-management-endpoints)
5.  [Game State Interaction Endpoints](#game-state-interaction-endpoints)
6.  [AI Service Interaction Endpoints](#ai-service-interaction-endpoints)

---

## 1. Authentication Endpoints

### 1.1 User Registration
-   **Endpoint:** `/api/auth/register`
-   **Method:** `POST`
-   **Description:** Registers a new user account.
-   **Request Body (JSON):**
    ```json
    {
      "username": "string",
      "email": "string (email format)",
      "password": "string (min 8 chars, strong)"
    }
    ```
-   **Response (JSON):**
    -   **Success (201 Created):**
        ```json
        {
          "message": "User registered successfully",
          "user_id": "uuid"
        }
        ```
    -   **Error (400 Bad Request):**
        ```json
        {
          "error": "Invalid input data",
          "details": {
            "username": "Username already taken",
            "email": "Invalid email format"
          }
        }
        ```
    -   **Error (409 Conflict):**
        ```json
        {
          "error": "User with this email or username already exists"
        }
        ```

### 1.2 User Login
-   **Endpoint:** `/api/auth/login`
-   **Method:** `POST`
-   **Description:** Authenticates a user and returns an access token.
-   **Request Body (JSON):**
    ```json
    {
      "username_or_email": "string",
      "password": "string"
    }
    ```
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "message": "Login successful",
          "access_token": "string (JWT)",
          "token_type": "bearer"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Invalid credentials"
        }
        ```

### 1.3 User Logout
-   **Endpoint:** `/api/auth/logout`
-   **Method:** `POST`
-   **Description:** Invalidates the current user's session/token. (Requires authentication)
-   **Request Body:** None
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "message": "Logged out successfully"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```

---

## 2. User Management Endpoints

### 2.1 Get User Profile
-   **Endpoint:** `/api/users/{user_id}`
-   **Method:** `GET`
-   **Description:** Retrieves a user's profile information. (Requires authentication, user can only view their own or admin can view others)
-   **Path Parameters:**
    -   `user_id`: `uuid` (ID of the user)
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "user_id": "uuid",
          "username": "string",
          "email": "string",
          "created_at": "datetime (ISO 8601)",
          "last_login": "datetime (ISO 8601, nullable)"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```
    -   **Error (403 Forbidden):**
        ```json
        {
          "error": "Access denied"
        }
        ```
    -   **Error (404 Not Found):**
        ```json
        {
          "error": "User not found"
        }
        ```

### 2.2 Update User Profile
-   **Endpoint:** `/api/users/{user_id}`
-   **Method:** `PUT`
-   **Description:** Updates a user's profile information. (Requires authentication, user can only update their own)
-   **Path Parameters:**
    -   `user_id`: `uuid` (ID of the user)
-   **Request Body (JSON):**
    ```json
    {
      "username": "string (optional)",
      "email": "string (email format, optional)",
      "password": "string (min 8 chars, strong, optional)"
    }
    ```
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "message": "User profile updated successfully",
          "user_id": "uuid"
        }
        ```
    -   **Error (400 Bad Request):**
        ```json
        {
          "error": "Invalid input data"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```
    -   **Error (403 Forbidden):**
        ```json
        {
          "error": "Access denied"
        }
        ```
    -   **Error (404 Not Found):**
        ```json
        {
          "error": "User not found"
        }
        ```
    -   **Error (409 Conflict):**
        ```json
        {
          "error": "Username or email already taken"
        }
        ```

---

## 3. Template Management Endpoints

### 3.1 Create Template
-   **Endpoint:** `/api/templates`
-   **Method:** `POST`
-   **Description:** Creates a new campaign template. (Requires authentication)
-   **Request Body (JSON):**
    ```json
    {
      "user_id": "uuid",
      "name": "string",
      "description": "string",
      "charter": {
        "campaign_name": "string",
        "setting_description": "string",
        "core_conflict": "string",
        "initial_player_context": "string",
        "ai_directives": {
          "adherence": "string",
          "narrative_redirection": "string",
          "deviation_budget": "string",
          "post_campaign_epilogue": "string"
        },
        "game_rules": {
          "combat_system": "string",
          "magic_system": "string",
          "skill_checks": "string",
          "inventory_management": "string"
        },
        "initial_state_elements": {
          "starting_location": "string",
          "key_npcs": "array of strings",
          "initial_quests": "array of strings"
        }
      },
      "settings": {
        "difficulty": "string (e.g., 'easy', 'medium', 'hard')",
        "player_limit": "integer",
        "genre": "string (e.g., 'fantasy', 'sci-fi', 'horror')"
      }
    }
    ```
-   **Response (JSON):**
    -   **Success (201 Created):**
        ```json
        {
          "message": "Template created successfully",
          "template_id": "uuid"
        }
        ```
    -   **Error (400 Bad Request):**
        ```json
        {
          "error": "Invalid input data"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```

### 3.2 Get All Templates (Public/User-Owned)
-   **Endpoint:** `/api/templates`
-   **Method:** `GET`
-   **Description:** Retrieves a list of all public templates or templates owned by the authenticated user.
-   **Query Parameters:**
    -   `user_id`: `uuid` (optional, filter by user-owned templates)
    -   `public`: `boolean` (optional, filter by public templates, default true if user_id not provided)
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        [
          {
            "template_id": "uuid",
            "user_id": "uuid",
            "name": "string",
            "description": "string",
            "created_at": "datetime (ISO 8601)",
            "updated_at": "datetime (ISO 8601)",
            "settings": {
              "difficulty": "string",
              "player_limit": "integer",
              "genre": "string"
            }
          }
        ]
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```

### 3.3 Get Template by ID
-   **Endpoint:** `/api/templates/{template_id}`
-   **Method:** `GET`
-   **Description:** Retrieves a specific campaign template by its ID.
-   **Path Parameters:**
    -   `template_id`: `uuid` (ID of the template)
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "template_id": "uuid",
          "user_id": "uuid",
          "name": "string",
          "description": "string",
          "charter": {
            "campaign_name": "string",
            "setting_description": "string",
            "core_conflict": "string",
            "initial_player_context": "string",
            "ai_directives": {
              "adherence": "string",
              "narrative_redirection": "string",
              "deviation_budget": "string",
              "post_campaign_epilogue": "string"
            },
            "game_rules": {
              "combat_system": "string",
              "magic_system": "string",
              "skill_checks": "string",
              "inventory_management": "string"
            },
            "initial_state_elements": {
              "starting_location": "string",
              "key_npcs": "array of strings",
              "initial_quests": "array of strings"
            }
          },
          "settings": {
            "difficulty": "string",
            "player_limit": "integer",
            "genre": "string"
          },
          "created_at": "datetime (ISO 8601)",
          "updated_at": "datetime (ISO 8601)"
        }
        ```
    -   **Error (404 Not Found):**
        ```json
        {
          "error": "Template not found"
        }
        ```

### 3.4 Update Template
-   **Endpoint:** `/api/templates/{template_id}`
-   **Method:** `PUT`
-   **Description:** Updates an existing campaign template. (Requires authentication, user must own the template)
-   **Path Parameters:**
    -   `template_id`: `uuid` (ID of the template to update)
-   **Request Body (JSON):**
    ```json
    {
      "name": "string (optional)",
      "description": "string (optional)",
      "charter": {
        "campaign_name": "string (optional)",
        "setting_description": "string (optional)",
        "core_conflict": "string (optional)",
        "initial_player_context": "string (optional)",
        "ai_directives": {
          "adherence": "string (optional)",
          "narrative_redirection": "string (optional)",
          "deviation_budget": "string (optional)",
          "post_campaign_epilogue": "string (optional)"
        },
        "game_rules": {
          "combat_system": "string (optional)",
          "magic_system": "string (optional)",
          "skill_checks": "string (optional)",
          "inventory_management": "string (optional)"
        },
        "initial_state_elements": {
          "starting_location": "string (optional)",
          "key_npcs": "array of strings (optional)",
          "initial_quests": "array of strings (optional)"
        }
      },
      "settings": {
        "difficulty": "string (e.g., 'easy', 'medium', 'hard', optional)",
        "player_limit": "integer (optional)",
        "genre": "string (e.g., 'fantasy', 'sci-fi', 'horror', optional)"
      }
    }
    ```
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "message": "Template updated successfully",
          "template_id": "uuid"
        }
        ```
    -   **Error (400 Bad Request):**
        ```json
        {
          "error": "Invalid input data"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```
    -   **Error (403 Forbidden):**
        ```json
        {
          "error": "Access denied (user does not own template)"
        }
        ```
    -   **Error (404 Not Found):**
        ```json
        {
          "error": "Template not found"
        }
        ```

### 3.5 Delete Template
-   **Endpoint:** `/api/templates/{template_id}`
-   **Method:** `DELETE`
-   **Description:** Deletes a campaign template. (Requires authentication, user must own the template)
-   **Path Parameters:**
    -   `template_id`: `uuid` (ID of the template to delete)
-   **Response (JSON):**
    -   **Success (204 No Content):** (No response body)
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```
    -   **Error (403 Forbidden):**
        ```json
        {
          "error": "Access denied (user does not own template)"
        }
        ```
    -   **Error (404 Not Found):**
        ```json
        {
          "error": "Template not found"
        }
        ```

---

## 4. Game Management Endpoints

### 4.1 Create Game from Template
-   **Endpoint:** `/api/games`
-   **Method:** `POST`
-   **Description:** Creates a new game instance from a specified template. (Requires authentication)
-   **Request Body (JSON):**
    ```json
    {
      "template_id": "uuid",
      "host_user_id": "uuid",
      "game_name": "string",
      "player_limit": "integer (optional, overrides template if provided)",
      "initial_player_ids": ["uuid"] (optional, initial players)
    }
    ```
-   **Response (JSON):**
    -   **Success (201 Created):**
        ```json
        {
          "message": "Game created successfully",
          "game_id": "uuid",
          "initial_game_state": {
            "game_state_id": "uuid",
            "current_location": "string",
            "active_quests": "array of strings",
            "completed_objectives": "array of strings",
            "discovered_lore_items": "array of strings",
            "game_log": "array of objects",
            "player_states": "array of objects",
            "npc_states": "array of objects",
            "inventory": "array of objects",
            "world_events": "array of objects",
            "current_turn": "integer",
            "last_updated": "datetime (ISO 8601)"
          }
        }
        ```
    -   **Error (400 Bad Request):**
        ```json
        {
          "error": "Invalid input data",
          "details": "Template not found or player limit exceeded"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```

### 4.2 Get All Games (User-Specific)
-   **Endpoint:** `/api/games`
-   **Method:** `GET`
-   **Description:** Retrieves a list of games associated with the authenticated user (either as host or player).
-   **Query Parameters:**
    -   `user_id`: `uuid` (optional, filter by games where this user is host or player)
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        [
          {
            "game_id": "uuid",
            "template_id": "uuid",
            "host_user_id": "uuid",
            "game_name": "string",
            "status": "string (e.g., 'active', 'completed', 'paused')",
            "current_players": ["uuid"],
            "created_at": "datetime (ISO 8601)",
            "last_played": "datetime (ISO 8601)"
          }
        ]
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```

### 4.3 Get Game Details by ID
-   **Endpoint:** `/api/games/{game_id}`
-   **Method:** `GET`
-   **Description:** Retrieves detailed information about a specific game instance. (Requires authentication, user must be a participant)
-   **Path Parameters:**
    -   `game_id`: `uuid` (ID of the game)
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "game_id": "uuid",
          "template_id": "uuid",
          "host_user_id": "uuid",
          "game_name": "string",
          "status": "string",
          "player_limit": "integer",
          "current_players": [
            {
              "game_player_id": "uuid",
              "user_id": "uuid",
              "character_name": "string",
              "joined_at": "datetime (ISO 8601)"
            }
          ],
          "created_at": "datetime (ISO 8601)",
          "last_played": "datetime (ISO 8601)",
          "charter": {
            "campaign_name": "string",
            "setting_description": "string",
            "core_conflict": "string",
            "initial_player_context": "string",
            "ai_directives": {
              "adherence": "string",
              "narrative_redirection": "string",
              "deviation_budget": "string",
              "post_campaign_epilogue": "string"
            },
            "game_rules": {
              "combat_system": "string",
              "magic_system": "string",
              "skill_checks": "string",
              "inventory_management": "string"
            },
            "initial_state_elements": {
              "starting_location": "string",
              "key_npcs": "array of strings",
              "initial_quests": "array of strings"
            }
          }
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```
    -   **Error (403 Forbidden):**
        ```json
        {
          "error": "Access denied (user not a participant)"
        }
        ```
    -   **Error (404 Not Found):**
        ```json
        {
          "error": "Game not found"
        }
        ```

### 4.4 Join Game
-   **Endpoint:** `/api/games/{game_id}/join`
-   **Method:** `POST`
-   **Description:** Allows a user to join an existing game. (Requires authentication)
-   **Path Parameters:**
    -   `game_id`: `uuid` (ID of the game to join)
-   **Request Body (JSON):**
    ```json
    {
      "user_id": "uuid",
      "character_name": "string"
    }
    ```
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "message": "Successfully joined game",
          "game_player_id": "uuid"
        }
        ```
    -   **Error (400 Bad Request):**
        ```json
        {
          "error": "Game is full or user already joined"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```
    -   **Error (404 Not Found):**
        ```json
        {
          "error": "Game not found"
        }
        ```

### 4.5 Leave Game
-   **Endpoint:** `/api/games/{game_id}/leave`
-   **Method:** `POST`
-   **Description:** Allows a user to leave an existing game. (Requires authentication)
-   **Path Parameters:**
    -   `game_id`: `uuid` (ID of the game to leave)
-   **Request Body (JSON):**
    ```json
    {
      "user_id": "uuid"
    }
    ```
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "message": "Successfully left game"
        }
        ```
    -   **Error (400 Bad Request):**
        ```json
        {
          "error": "User not in this game"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```
    -   **Error (404 Not Found):**
        ```json
        {
          "error": "Game not found"
        }
        ```

### 4.6 End Game
-   **Endpoint:** `/api/games/{game_id}/end`
-   **Method:** `POST`
-   **Description:** Ends an active game. (Requires authentication, only host can end)
-   **Path Parameters:**
    -   `game_id`: `uuid` (ID of the game to end)
-   **Request Body:** None
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "message": "Game ended successfully",
          "game_id": "uuid"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```
    -   **Error (403 Forbidden):**
        ```json
        {
          "error": "Access denied (user is not the host)"
        }
        ```
    -   **Error (404 Not Found):**
        ```json
        {
          "error": "Game not found"
        }
        ```

---

## 5. Game State Interaction Endpoints

### 5.1 Get Current Game State
-   **Endpoint:** `/api/games/{game_id}/state`
-   **Method:** `GET`
-   **Description:** Retrieves the current mutable game state. (Requires authentication, user must be a participant)
-   **Path Parameters:**
    -   `game_id`: `uuid` (ID of the game)
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "game_state_id": "uuid",
          "game_id": "uuid",
          "current_location": "string",
          "active_quests": "array of strings",
          "completed_objectives": "array of strings",
          "discovered_lore_items": "array of strings",
          "game_log": [
            {
              "timestamp": "datetime (ISO 8601)",
              "event_type": "string (e.g., 'player_action', 'ai_response', 'system_event')",
              "actor": "string (e.g., 'player_name', 'AI', 'System')",
              "message": "string",
              "details": "object (optional, context-specific data)"
            }
          ],
          "player_states": [
            {
              "player_id": "uuid",
              "health": "integer",
              "mana": "integer",
              "inventory": "array of objects",
              "status_effects": "array of strings",
              "location": "string"
            }
          ],
          "npc_states": [
            {
              "npc_id": "uuid",
              "name": "string",
              "health": "integer",
              "location": "string",
              "status": "string"
            }
          ],
          "inventory": [
            {
              "item_id": "uuid",
              "name": "string",
              "description": "string",
              "quantity": "integer"
            }
          ],
          "world_events": [
            {
              "event_id": "uuid",
              "name": "string",
              "description": "string",
              "status": "string"
            }
          ],
          "current_turn": "integer",
          "last_updated": "datetime (ISO 8601)"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```
    -   **Error (403 Forbidden):**
        ```json
        {
          "error": "Access denied (user not a participant)"
        }
        ```
    -   **Error (404 Not Found):**
        ```json
        {
          "error": "Game or GameState not found"
        }
        ```

### 5.2 Submit Player Action
-   **Endpoint:** `/api/games/{game_id}/action`
-   **Method:** `POST`
-   **Description:** Submits a player's action to the game. This triggers the AI processing. (Requires authentication, user must be a participant)
-   **Path Parameters:**
    -   `game_id`: `uuid` (ID of the game)
-   **Request Body (JSON):**
    ```json
    {
      "game_player_id": "uuid",
      "action_type": "string (e.g., 'move', 'interact', 'attack', 'speak')",
      "action_details": "object (context-specific data for the action, e.g., {'target': 'NPC Name', 'dialogue': 'Hello'})"
    }
    ```
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "message": "Action submitted, awaiting AI response",
          "game_state_id": "uuid",
          "new_game_log_entry": {
            "timestamp": "datetime (ISO 8601)",
            "event_type": "player_action",
            "actor": "player_name",
            "message": "string (summary of action)",
            "details": "object (original action_details)"
          }
        }
        ```
    -   **Error (400 Bad Request):**
        ```json
        {
          "error": "Invalid action or not player's turn"
        }
        ```
    -   **Error (401 Unauthorized):**
        ```json
        {
          "error": "Authentication required"
        }
        ```
    -   **Error (403 Forbidden):**
        ```json
        {
          "error": "Access denied (user not a participant)"
        }
        ```
    -   **Error (404 Not Found):**
        ```json
        {
          "error": "Game or GamePlayer not found"
        }
        ```

### 5.3 Get Game Log Updates (Real-time via Socket.IO)
-   **Endpoint:** (Socket.IO event) `game_log_update`
-   **Method:** `N/A` (WebSocket)
-   **Description:** Real-time updates to the game log and potentially other game state elements.
-   **Event Data (JSON):**
    ```json
    {
      "game_id": "uuid",
      "updates": [
        {
          "timestamp": "datetime (ISO 8601)",
          "event_type": "string (e.g., 'player_action', 'ai_response', 'system_event')",
          "actor": "string (e.g., 'player_name', 'AI', 'System')",
          "message": "string",
          "details": "object (optional, context-specific data)"
        }
      ],
      "current_turn": "integer",
      "game_state_snapshot": {
        "completed_objectives": "array of strings",
        "discovered_lore_items": "array of strings",
        "player_states": "array of objects",
        "npc_states": "array of objects",
        "inventory": "array of objects",
        "world_events": "array of objects"
      }
    }
    ```
-   **Note:** This is a Socket.IO event, not a REST endpoint. The client will subscribe to this event after joining a game.

---

## 6. AI Service Interaction Endpoints (Internal Backend Only)

These endpoints are for internal backend use only and are not exposed directly to the frontend.

### 6.1 Generate Initial Game State
-   **Endpoint:** `/api/internal/ai/generate_initial_state`
-   **Method:** `POST`
-   **Description:** Generates the initial game state based on a campaign charter.
-   **Request Body (JSON):**
    ```json
    {
      "charter": {
        "campaign_name": "string",
        "setting_description": "string",
        "core_conflict": "string",
        "initial_player_context": "string",
        "ai_directives": {
          "adherence": "string",
          "narrative_redirection": "string",
          "deviation_budget": "string",
          "post_campaign_epilogue": "string"
        },
        "game_rules": {
          "combat_system": "string",
          "magic_system": "string",
          "skill_checks": "string",
          "inventory_management": "string"
        },
        "initial_state_elements": {
          "starting_location": "string",
          "key_npcs": "array of strings",
          "initial_quests": "array of strings"
        }
      },
      "player_count": "integer"
    }
    ```
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "current_location": "string",
          "active_quests": "array of strings",
          "completed_objectives": "array of strings",
          "discovered_lore_items": "array of strings",
          "game_log": [
            {
              "timestamp": "datetime (ISO 8601)",
              "event_type": "system_event",
              "actor": "System",
              "message": "Game initialized.",
              "details": {}
            }
          ],
          "player_states": [
            {
              "player_id": "uuid",
              "health": "integer",
              "mana": "integer",
              "inventory": "array of objects",
              "status_effects": "array of strings",
              "location": "string"
            }
          ],
          "npc_states": [
            {
              "npc_id": "uuid",
              "name": "string",
              "health": "integer",
              "location": "string",
              "status": "string"
            }
          ],
          "inventory": [
            {
              "item_id": "uuid",
              "name": "string",
              "description": "string",
              "quantity": "integer"
            }
          ],
          "world_events": [
            {
              "event_id": "uuid",
              "name": "string",
              "description": "string",
              "status": "string"
            }
          ],
          "current_turn": "integer"
        }
        ```
    -   **Error (500 Internal Server Error):**
        ```json
        {
          "error": "Failed to generate initial state"
        }
        ```

### 6.2 Process Player Action (AI)
-   **Endpoint:** `/api/internal/ai/process_action`
-   **Method:** `POST`
-   **Description:** Processes a player's action and generates AI responses and game state updates.
-   **Request Body (JSON):**
    ```json
    {
      "game_id": "uuid",
      "current_game_state": {
        "game_state_id": "uuid",
        "current_location": "string",
        "active_quests": "array of strings",
        "completed_objectives": "array of strings",
        "discovered_lore_items": "array of strings",
        "game_log": "array of objects",
        "player_states": "array of objects",
        "npc_states": "array of objects",
        "inventory": "array of objects",
        "world_events": "array of objects",
        "current_turn": "integer",
        "last_updated": "datetime (ISO 8601)"
      },
      "player_action": {
        "game_player_id": "uuid",
        "action_type": "string",
        "action_details": "object"
      },
      "charter": {
        "campaign_name": "string",
        "setting_description": "string",
        "core_conflict": "string",
        "initial_player_context": "string",
        "ai_directives": {
          "adherence": "string",
          "narrative_redirection": "string",
          "deviation_budget": "string",
          "post_campaign_epilogue": "string"
        },
        "game_rules": {
          "combat_system": "string",
          "magic_system": "string",
          "skill_checks": "string",
          "inventory_management": "string"
        },
        "initial_state_elements": {
          "starting_location": "string",
          "key_npcs": "array of strings",
          "initial_quests": "array of strings"
        }
      }
    }
    ```
-   **Response (JSON):**
    -   **Success (200 OK):**
        ```json
        {
          "new_game_state": {
            "current_location": "string",
            "active_quests": "array of strings",
            "completed_objectives": "array of strings",
            "discovered_lore_items": "array of strings",
            "game_log": "array of objects",
            "player_states": "array of objects",
            "npc_states": "array of objects",
            "inventory": "array of objects",
            "world_events": "array of objects",
            "current_turn": "integer",
            "last_updated": "datetime (ISO 8601)"
          },
          "ai_response_log_entry": {
            "timestamp": "datetime (ISO 8601)",
            "event_type": "ai_response",
            "actor": "AI",
            "message": "string (AI's narrative response)",
            "details": "object (optional, AI-specific data)"
          }
        }
        ```
    -   **Error (500 Internal Server Error):**
        ```json
        {
          "error": "Failed to process player action"
        }
