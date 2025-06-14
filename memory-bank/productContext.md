# Product Context

QuestForge aims to provide a platform for creating and playing AI-generated cooperative RPGs, addressing the need for dynamic, mechanically engaging, and narratively consistent experiences.

## Core Functionality:
- **User Authentication:** Secure user registration, login, and profile management, including storage of character backstories.
- **Template Management:** CRUD interface for campaign templates, defining genre, conflict, world, AI GM Persona, and Core Skills.
- **Game Management:** Creation of new games from templates, with customizable AI GM Persona and AI models. Stores game-specific settings like `enable_visual_dice_roller` and `expected_session_length_minutes`. Manages `GamePlayer` data including character name, description, backstory, portrait URL, ready status, and AI-generated `character_sheet` (skills and stats).
- **Campaign Structure & Charter:** Generates an immutable "Campaign Charter" upon game start, outlining core conflict, objectives, world elements, immutable rules, interactive map layout, and NPC generation.
- **AI Game Master (AI GM):** Manages AI interactions via an `AIService` layer. Assembles context packages for AI models. Generates campaign charters, player/NPC images, backstories, "Story So Far" summaries, and character sheets. Implements a two-step action resolution system: first, AI identifies if a skill check is needed and provides a structured JSON response; second, after server resolution, AI narrates the outcome. Adheres to core directives like Adherence, Narrative Redirection, Deviation Budget, and Post-Campaign Epilogue.
- **Game State Tracking:** The `GameState` model tracks the live game state. The `GameStateService` acts as the Rules Referee, handling action resolution: receiving AI skill check requests, looking up player skills, simulating dice rolls, calculating results, and initiating AI outcome narration.
- **Real-Time Communication:** Utilizes Socket.IO for real-time communication within game rooms, managing events for joining, readying up, starting games, and submitting actions. Broadcasts events for skill checks, dice rolls, and results.

## User Interface (UI) & User Experience (UX) Flow:
- **Main Layout:** Persistent navigation for Dashboard, Templates, and Games.
- **Core Screens:** Dashboard, Template Management, Game Management, Lobby Screen, Create Game Screen (with "Enable Visual Dice Roller" toggle and "Expected Session Length" input).
- **"Play" Screen:**
    - **Static Panels:** Game Log (main narrative, includes system messages for skill checks, rolls, and results), Action Input (persistent text input), Game Status Header (campaign title, GM Persona, summary button, campaign cost).
    - **Information Panel (Right, Tabbed):** World & Map (interactive map), Party & NPCs (player character sheets, known NPCs), Objectives & Lore (quest log, documents), Comms & Chat (player-to-player chat).
    - **Visual Overlays:** Visual Dice Roller (3D die rolling modal for skill checks, if enabled).

## Administrative & History Tools:
- Players can view non-interactive history of completed games.
- Admin pages for inspecting raw game state, charters, and application management.
