# Game Creation Process (Revised 2025-04-05)

This document outlines the step-by-step process for creating a new game instance in QuestForge, incorporating template selection, creator customizations/overrides, and delayed campaign generation.

## Process Flow

```mermaid
graph TD
    A[User navigates to /game/create] --> B{Selects Template};
    B --> C{Fills Game Name, Overrides (Optional), Customizations (Optional)};
    C --> D[Submits Form to /api/games/create];

    subgraph Frontend (game/create.html)
        A
        B
        C
        D
    end

    E[API /api/games/create receives data] --> F{Validates Template ID};
    F --> G[Creates Game record w/ Overrides & Customizations];
    G --> H[Creates GamePlayer record for Creator];
    H --> I[Commits Game & GamePlayer];
    I --> J[Returns Redirect URL to /game/{id}/lobby];

    subgraph Backend API (campaign_api.py)
        E
        F
        G
        H
        I
        J
    end

    K[User lands in Lobby /game/{id}/lobby] --> L{Players Join & Ready Up};
    L --> M[Creator clicks Start Game];
    M --> N[SocketIO 'start_game' event received];

    subgraph Frontend (game/lobby.html)
        K
        L
        M
    end

    O[Server retrieves Game w/ Overrides & Customizations] --> P{Gathers Player Descriptions};
    P --> Q[Calls Campaign Generation Service];
    Q --> R[AI Service builds prompt w/ Template, Overrides, Customizations];
    R --> S{AI Generates Campaign Data};
    S --> T[Service validates AI response];
    T --> U[Creates Campaign & initial GameState records];
    U --> V[Commits Campaign & GameState];
    V --> W[Updates Game status to 'in_progress'];
    W --> X[Emits 'game_started' event];

    subgraph Backend SocketIO (socket_service.py & campaign_service.py)
        N
        O
        P
        Q
        T
        U
        V
        W
        X
    end

    subgraph AI Service (ai_service.py & prompt_builder.py)
        R
        S
    end

    Y[Client receives 'game_started'] --> Z[Redirects to /game/{id}/play];

    subgraph Frontend (game/lobby.html)
        Y
        Z
    end

    D --> J;
    J --> K;
    N --> O;
    X --> Y;

```

## Detailed Steps

1.  **Navigate to Create View (User Action):**
    *   User accesses the game creation page (`/game/create`).
    *   View function: `questforge/views/game.py::create_game_view`.

2.  **Select Template & Provide Details (User Action):**
    *   User selects a template from the dropdown.
    *   JavaScript fetches template details (`/api/templates/<id>/details`) and populates override fields.
    *   User enters a Game Name.
    *   User *optionally* modifies template details in the "Customize Template Details" section (template overrides).
    *   User *optionally* adds details in the "Add Customizations" section (creator customizations).

3.  **Submit Creation Form (User Action):**
    *   User clicks "Create Game".
    *   Frontend JavaScript gathers the game name, template ID, non-empty `template_overrides`, and non-empty `creator_customizations`.
    *   Data is POSTed as JSON to `/api/games/create`.

4.  **Handle API Request (Backend - `campaign_api.py::create_game_api`):**
    *   Receives the JSON payload.
    *   Validates the `template_id`.
    *   Creates a new `Game` object instance, initializing it with name, template ID, and creator ID.
    *   Sets the `template_overrides` and `creator_customizations` attributes on the `Game` object instance from the received payload.
    *   Adds the `Game` object to the database session.
    *   Flushes the session to assign an ID to the `Game` object.
    *   Creates a `GamePlayer` association record linking the creator (current user) to the new game ID.
    *   Adds the `GamePlayer` object to the database session.
    *   Commits the transaction, saving the `Game` (with overrides/customizations) and `GamePlayer` records.
    *   Returns a JSON response containing the URL for the game lobby (e.g., `/game/123/lobby`).

5.  **Redirect to Lobby (Frontend):**
    *   Frontend JavaScript receives the success response and redirects the user to the game lobby URL.

6.  **Lobby Phase (User Interaction & SocketIO):**
    *   Creator (and potentially other players) join the lobby (`/game/<id>/lobby`).
    *   Players connect via SocketIO (`socket_service.py::handle_join_game`).
    *   Players optionally provide character descriptions (`socket_service.py::handle_update_character_description`).
    *   Players mark themselves as ready (`socket_service.py::handle_player_ready`).

7.  **Start Game Trigger (User Action):**
    *   Once all players are ready (or just the creator in single-player), the creator clicks "Start Game".
    *   Frontend emits the `start_game` SocketIO event with the `game_id`.

8.  **Handle Start Game Event (Backend - `socket_service.py::handle_start_game`):**
    *   Receives the `start_game` event.
    *   Validates that the user is the creator and all players are ready.
    *   Retrieves the `Game` object from the database, ensuring `template`, `template_overrides`, and `creator_customizations` are loaded/available.
    *   Retrieves player character descriptions from `GamePlayer` records.
    *   Calls `campaign_service.generate_campaign_structure`, passing the `game`, `template`, `player_descriptions`, `creator_customizations`, and `template_overrides`.

9.  **Generate Campaign Structure (Backend - `campaign_service.py::generate_campaign_structure`):**
    *   Calls `ai_service.generate_campaign`, passing the `template`, `template_overrides`, and `creator_customizations`.

10. **Generate AI Content (Backend - `ai_service.py::generate_campaign`):**
    *   Calls `prompt_builder.build_campaign_prompt` to construct the prompt using the template, overrides, and customizations.
    *   Sends the prompt to the OpenAI API.
    *   Receives the JSON response containing the generated campaign structure.
    *   Returns the parsed data, model used, and usage info to the campaign service.

11. **Process AI Response (Backend - `campaign_service.py::generate_campaign_structure`):**
    *   Receives the AI response data.
    *   Logs API usage.
    *   Validates the basic structure of the AI response (placeholder validation currently).
    *   Creates a new `Campaign` record, populating its fields (objectives, locations, characters, etc.) from the AI response.
    *   Creates the initial `GameState` record, populating its `state_data`, `game_log`, and `available_actions` from the AI response's `initial_scene`.
    *   Commits the `Campaign` and `GameState` records.
    *   Initializes the in-memory state in `GameStateService`.
    *   Returns `True` to the socket service upon success.

12. **Finalize Game Start (Backend - `socket_service.py::handle_start_game`):**
    *   Receives confirmation of successful campaign generation.
    *   Updates the `Game` status to `in_progress` and commits the change.
    *   Emits the `game_started` event to all clients in the game room.

13. **Redirect to Play (Frontend):**
    *   Clients in the lobby listening for the `game_started` event redirect to the gameplay page (`/game/<id>/play`).

## Related Components

*   **Models:** `Template`, `Game`, `Campaign`, `GameState`, `User`, `GamePlayer`, `ApiUsageLog`
*   **Views:** `questforge/views/game.py` (Lobby, Play, History, Create Form, List), `questforge/views/campaign_api.py` (Game Create API)
*   **Services:** `questforge/services/campaign_service.py`, `questforge/services/ai_service.py`, `questforge/services/socket_service.py`, `questforge/services/game_state_service.py`
*   **Utils:** `questforge/utils/prompt_builder.py`
*   **UI:** Templates in `questforge/templates/game/`, related JavaScript (`create.html`, `lobby.html`, `play.html`, `socketClient.mjs`).
