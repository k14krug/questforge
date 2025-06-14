# QuestForge Development Roadmap

This document outlines the entire development process for the QuestForge application, from initial setup and specification refinement to the implementation of core modules, game logic, real-time communication, frontend integration, and administrative tools. Each bullet point within the phases is intended to represent a separate, distinct task.

## Phase 0: Specification Refinement & Setup

*   **Address Pending Specification Refinement Tasks:**
    *   Define explicit database schemas for all models (e.g., `Game`, `GamePlayer`, `GameState`, `Template`, `User`), including fields, data types, relationships, and primary/foreign keys.
    *   Specify precise API endpoints, HTTP methods, and JSON request/response structures for all backend interactions (e.g., template CRUD, game creation, AI service calls).
    *   Detail exact names and data structures for all Socket.IO real-time communication events (e.g., `join_game`, `ready_up`, `submit_action`, `skill_check_initiated`, `dice_roll_result`).
    *   Provide clear input/output formats and condensation criteria for AI-generated "Story So Far" summaries and `npc_memory` condensation.
    *   Explicitly define the "Directive of Adherence," "Narrative Redirection," "Deviation Budget," and "Post-Campaign Epilogue" features.
    *   Establish guidelines for error handling, including how various errors (e.g., AI API failures, invalid input, network issues) should be handled, logged, and communicated to users.
    *   Provide a detailed JSON schema for the "node-based JSON structure of locations and their connections" for the interactive map.
*   **Set up Initial Project Environment:**
    *   Create the basic Flask project structure.
    *   Install initial basic dependencies.
*   **Establish AI Model Configuration:**
    *   Create the `config.json` file to serve as the single source of truth for available AI models, their tier, API identifiers, and token costs.

## Phase 1: Core Backend Modules

*   **Implement User Authentication Module:**
    *   Develop user registration functionality.
    *   Implement user login and session management.
    *   Create user profile management, including storing generated character backstories.
    *   Integrate bcrypt for secure password hashing.
*   **Implement Template Module:**
    *   Develop CRUD (Create, Read, Update, Delete) operations for campaign templates.
    *   Implement fields for genre, core conflict, world description, AI Game Master "Persona," and Core Skills.
*   **Implement Game Management Module:**
    *   Develop functionality for users to create new games from a template.
    *   Implement overriding settings like AI GM Persona and selecting AI models during game creation.
    *   Define and implement the `Game` model linking creator, template, and players.
    *   Implement the `settings` JSON field in the `Game` model for game-specific options (e.g., `{"enable_visual_dice_roller": true}`, `{"expected_session_length_minutes": 120}`).
    *   Implement the `GamePlayer` association to store player-specific data: character name, description, AI-generated backstory, character portrait URL, "Ready" status, and `character_sheet` (JSON object for stats/skills).
*   **Implement AI Model Management & Economy:**
    *   Develop the `AIService` layer to manage all calls to external AI models.
    *   Implement integration with primary (creative core) and secondary (utility & speed) AI models.
    *   Develop cost tracking mechanisms within the `GameStateService` to calculate and accumulate AI call costs in the `Game` model's `cumulative_cost` field.

## Phase 2: Core Game Logic & AI Integration

*   **Implement Campaign Structure Module & The Campaign Charter:**
    *   Develop the logic to generate the "Campaign Charter" (immutable JSON object) upon game start.
    *   Implement the generation of all Charter Components: Core Conflict & Ultimate Goal, Critical Path Objectives, Key World Elements, Immutable Rules, Interactive Map Layout (node-based JSON), and NPC Generation (with descriptions and AI-generated portraits).
*   **Implement Game State Tracking Module:**
    *   Define and implement the `GameState` model to represent the mutable, live state of the game.
    *   Develop the `GameStateService` to act as the Rules Referee, responsible for executing game mechanics.
    *   Implement the Action Resolution Workflow: receiving AI's JSON request for skill checks, looking up player skill bonuses, simulating dice rolls (e.g., 1d20), calculating results, comparing to difficulty, and determining outcome (Success/Failure).
*   **Implement AI Game Master Module (Action Resolution & Generation):**
    *   Implement the two-step action resolution system:
        1.  **Step 1 (Check Identification):** AI analyzes player action and responds with structured JSON for skill checks.
        2.  **Step 2 (Outcome Narration):** AI receives roll result and `narration_prompt` to generate narrative outcome.
    *   Implement AI generation capabilities for Player & NPC Images, AI-Assisted Backstory, and "Story So Far" Summaries.
    *   Implement Character Sheet Generation: AI generates a balanced set of skills for a player's `character_sheet` based on keywords.
*   **Implement Core Directives:**
    *   Integrate the Directive of Adherence, Narrative Redirection, Deviation Budget, and Post-Campaign Epilogue features into the AI GM's operation.

## Phase 3: Real-Time Communication & Frontend Integration

*   **Implement Real-Time Communication Module:**
    *   Set up and configure Socket.IO for real-time communication in distinct game rooms.
    *   Implement event handling for joining games, readying up, starting games, and submitting player actions.
    *   Implement broadcasting of events to all clients for skill check initiation, dice roll simulation, and final results before AI narrative responses.
*   **Develop User Interface (UI) & User Experience (UX) Flow (Frontend):**
    *   **Main Application Layout & Navigation:** Implement a persistent main navigation bar for Dashboard, Templates, and Games.
    *   **Core Application Screens:**
        *   Develop the Dashboard screen.
        *   Develop the Template Management screen.
        *   Develop the Game Management screen.
        *   Develop the Lobby Screen.
        *   Develop the Create Game Screen, including the "Enable Visual Dice Roller" toggle and "Expected Session Length" input.
    *   **The "Play" Screen:**
        *   Implement Static (Always Visible) Panels: Game Log Panel (displaying GM narrative and system messages for skill checks/rolls), Action Input Panel (persistent text input), Game Status Header (campaign title, GM Persona, summary button, campaign cost).
        *   Implement The Information Panel (Right Side, Tabbed Interface): Tab 1 (World & Map with interactive map and location-populating action input), Tab 2 (Party & NPCs with player Character Sheets and known NPCs), Tab 3 (Objectives & Lore with quest log and discovered documents), Tab 4 (Comms & Chat for player-to-player text chat).
        *   Implement Visual Overlays: Visual Dice Roller modal overlay (3D die rolling, calculation display) if enabled in game settings.
    *   **Frontend Technology Note:** All frontend development will use native web technologies (HTML, CSS, Vanilla JavaScript), explicitly excluding modern frameworks like React, Vue, or Angular.

## Phase 4: Administrative Tools, History & Refinement

*   **Implement Administrative & History Tools:**
    *   Develop administrative pages for inspecting raw game state, charters, and application management.
    *   Implement a full, non-interactive history view for completed games.
*   **Testing, Bug Fixing, and Optimization:**
    *   Conduct comprehensive unit, integration, and end-to-end testing.
    *   Address identified bugs and issues.
    *   Perform performance profiling and optimization across the application.
    *   Refine UI/UX based on testing and feedback.
