# System Patterns

## Architecture Overview:
QuestForge is a web application with a Python-based backend (e.g., Flask) utilizing Socket.IO for real-time communication. It employs a tiered system of AI language models for content generation and a dynamic action resolution system.

## Key Modules and Their Relationships:

### 1. User Authentication Module:
- Handles standard user management (registration, login, profiles).
- Uses bcrypt for secure password hashing.
- Stores character backstories within user profiles.

### 2. Template Module:
- Provides CRUD operations for campaign templates.
- Templates define foundational AI guidance (genre, conflict, world, AI GM Persona, Core Skills).

### 3. Game Management Module:
- Creates new games from templates, allowing overrides for AI GM Persona and AI models.
- `Game` model links creator, template, and players.
- `Game` model includes a `settings` JSON field for game-specific options (e.g., `{"enable_visual_dice_roller": true}`, `{"expected_session_length_minutes": 120}`).
- `GamePlayer` association stores player-specific data: character name, description, AI-generated backstory, portrait URL, "Ready" status, and `character_sheet` (JSON object for stats/skills).

### 4. Campaign Structure Module & The Campaign Charter:
- Generates the "Campaign Charter" (immutable JSON) upon game start.
- Charter Components: Core Conflict & Ultimate Goal, Critical Path Objectives, Key World Elements, Immutable Rules, Interactive Map Layout (node-based JSON), NPC Generation (with portraits).

### 5. AI Game Master Module (`AIService` layer):
- Manages all calls to external AI models.
- **Context Management:** Assembles a "context package" for the primary AI model per turn (Campaign Charter, current GameState, "Story So Far" Summary, last 1-2 raw exchanges).
- **Generation Capabilities:** Campaign Charter, Player & NPC Images, AI-Assisted Backstory, "Story So Far" Summaries, Character Sheet Generation.
- **Two-Step Action Resolution:**
    1. **Step 1 (Check Identification):** AI analyzes player action, responds with structured JSON if skill check is needed (e.g., `{"action_requires_roll": true, "skill": "Persuasion", "difficulty": 15, "narration_prompt": "..."}`).
    2. **Step 2 (Outcome Narration):** AI receives roll result (Success/Failure) and `narration_prompt`, then generates narrative outcome.
- **Core Directives:** Adherence, Narrative Redirection, Deviation Budget, Post-Campaign Epilogue.

### 6. Game State Tracking Module (`GameState` model & `GameStateService`):
- `GameState` model represents the mutable, live state of the game.
- `GameStateService` acts as the Rules Referee, executing game mechanics.
- **Action Resolution Workflow:**
    1. Receives AI's JSON request for skill check.
    2. Looks up player's skill bonus from `character_sheet` in `GamePlayer`.
    3. Simulates dice roll (e.g., 1d20).
    4. Calculates final result (dice roll + skill bonus).
    5. Compares result to difficulty for outcome (Success/Failure).
    6. Initiates Step 2 of AI interaction with outcome for narration.

### 7. Real-Time Communication Module (Socket.IO):
- Manages real-time communication in distinct game rooms.
- Handles events: joining, readying up, starting game, submitting actions.
- Broadcasts events for skill check initiation, dice roll simulation, and final result before AI narrative.

## AI Model Management & Economy:

### Tiered Model Usage:
- **Primary Models (Creative Core):** State-of-the-art (e.g., GPT-4o) for high-creativity tasks (Campaign Charter, per-turn narrative, epilogue).
- **Secondary Models (Utility & Speed):** Faster, lower-cost (e.g., GPT-3.5 Turbo) for structured tasks (backstory, "Story So Far" summaries, `npc_memory` condensation, AI Response Validation).

### Model Dictionary:
- `config.json` (developer-maintained) as single source of truth for AI models, tier, API identifiers, and token costs.

### Cost Tracking & Calculation:
- `GameStateService` calculates cost of each AI call using token usage and `Model Dictionary`.
- Cost added to `cumulative_cost` field in `Game` model. Initial Campaign Charter cost is first recorded.
