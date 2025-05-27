# Plan: QuestForge Game Enhancements Leveraging 128k AI Context

This document outlines a phased approach to enhance QuestForge's AI capabilities and game depth by leveraging the 128,000 token context window of the `gpt-4.1` model. The goal is to make the game more efficient, better, and smarter through deeper memory, richer world simulation, and more intelligent AI reasoning.

## Current State as Reference

Before outlining the proposed changes, it's important to understand the current state of relevant components:

*   **AI Models**:
    *   `OPENAI_MODEL_LOGIC` (e.g., `gpt-4.1`): Used for critical logic-heavy calls (`ai_service.get_response`, `ai_service.generate_campaign`). Processes prompts typically in the 2,000-3,500 token range.
    *   `OPENAI_MODEL_MAIN` (e.g., `gpt-4.1-mini`): Used for less critical calls (`ai_service.generate_character_name`, `ai_service.get_ai_hint`, `ai_service.check_atomic_plot_completion`, `ai_service.generate_historical_summary`). Processes prompts typically in the 400-1,800 token range.
    *   **Context Window**: Both `gpt-4.1` and its `mini` variants have a 128,000 token context window. Current usage is a small fraction of this capacity.

*   **Game State (`GameState.state_data`)**:
    *   A JSONB field storing dynamic game information.
    *   `location`: Current player location (string).
    *   `inventory`: List of item names (strings).
    *   `npc_states`: Dictionary of NPC IDs/names to basic states (e.g., location, simple status).
    *   `world_objects`: Dictionary of object IDs to basic states (e.g., location, interactable flag).
    *   `completed_plot_points`: List of completed plot point objects (ID, description, required).
    *   `historical_summary`: List of single-sentence AI-generated summaries of past turns. Limited by `MAX_HISTORICAL_SUMMARIES` (default 20).
    *   `turns_since_plot_progress`: Counter for narrative guidance.

*   **AI Interaction Points**:
    *   `ai_service.generate_campaign`: Generates initial campaign structure.
    *   `ai_service.get_response`: Main game turn AI, generates narrative and general state changes.
    *   `ai_service.generate_historical_summary`: Summarizes turns for historical context.
    *   `ai_service.check_atomic_plot_completion`: Checks if atomic plot points are completed.
    *   `ai_service.generate_character_name`: Generates NPC names.
    *   `ai_service.get_ai_hint`: Provides hints to the player.

*   **Context Building (`questforge/utils/context_manager.py`)**:
    *   `build_context`: Constructs the prompt context for AI calls, including game state, recent events, and historical summary.

*   **Prompt Building (`questforge/utils/prompt_builder.py`)**:
    *   Functions like `build_response_prompt` format the final prompts sent to AI models.

## Phased Approach to Game Enhancements

### Phase 1: Enhanced Historical Summaries & Context Integration

*   **Goal**: Provide the AI with a richer, more detailed understanding of past game events, forming the foundation for deeper memory.
*   **Key Changes**:
    *   **Modify `ai_service.generate_historical_summary`**:
        *   **Current**: Generates a single-sentence summary.
        *   **Proposed**: Prompt the AI to generate a more detailed, multi-sentence or multi-paragraph summary of the turn's events. This summary should explicitly highlight:
            *   Key player actions and their immediate consequences.
            *   Significant changes to the game state (e.g., new items acquired, location changes, NPC status updates).
            *   Any notable plot progression or character interactions.
        *   **Implementation**: Adjust the prompt in `questforge/utils/prompt_builder.py` (`build_summary_prompt`) to request this richer format.
    *   **Adjust `MAX_HISTORICAL_SUMMARIES` in `config.py`**: Increase this value significantly (e.g., from 20 to 50 or 100) to allow a much longer history of these detailed summaries to persist in `GameState.state_data['historical_summary']`.
    *   **Refine `context_manager.build_context`**: Ensure that the expanded `historical_summary` is effectively integrated into the AI's main prompt. This might involve presenting it as a numbered list of "Key Past Events" or a "Game Recap" section, placed prominently in the context.
*   **Affected Files**:
    *   `config.py`
    *   `questforge/services/ai_service.py` (specifically `generate_historical_summary`)
    *   `questforge/utils/prompt_builder.py`
    *   `questforge/utils/context_manager.py`

### Phase 2: Persistent NPC Memory & Complex Object States (Data Structure & Initial Context)

*   **Goal**: Establish the data structures and initial context integration for NPCs and world objects to support more complex states and persistent memory.
*   **Key Changes**:
    *   **Update `GameState.state_data` for NPCs**:
        *   **Current**: `npc_states` might be simple (e.g., "present").
        *   **Proposed**: Modify the structure of `npc_states` within `GameState.state_data` to include more granular attributes for each NPC. This could include:
            *   `disposition`: How the NPC feels about the player (e.g., "friendly", "suspicious", "hostile").
            *   `knowledge`: Specific pieces of information the NPC knows or has learned.
            *   `recent_interactions`: A brief, AI-summarized log of the player's last few interactions with *this specific NPC*.
            *   `current_goal`: What the NPC is currently trying to achieve.
        *   **Implementation**: This will require changes to how NPCs are generated (likely in `ai_service.generate_campaign`) and how their states are updated (`ai_service.get_response`). This will involve updates to the JSON schema expected from the AI.
    *   **Update `GameState.state_data` for World Objects**:
        *   **Current**: `world_objects` might be basic descriptions.
        *   **Proposed**: Enhance `world_objects` to include dynamic attributes:
            *   `condition`: (e.g., "pristine", "damaged", "broken", "repaired").
            *   `status`: (e.g., "locked", "unlocked", "open", "closed", "active", "inactive").
            *   `contents`: For containers (e.g., a chest, a backpack).
            *   `properties`: Special attributes (e.g., "magical", "cursed", "charged").
        *   **Implementation**: Similar to NPCs, this will involve changes in campaign generation (`ai_service.generate_campaign`) and `ai_service.get_response` to track and update these states. This will also involve updates to the JSON schema expected from the AI.
    *   **Refine `context_manager.build_context`**: Integrate these richer NPC and object states into the AI's prompt. This might involve dedicated sections for "NPC Status" and "Key World Objects in Current Location" to ensure the AI has immediate access to this detailed information.
*   **Affected Files**:
    *   `questforge/models/game_state.py` (for `state_data` structure documentation/implications)
    *   `questforge/services/ai_service.py` (for `generate_campaign`, `get_response` logic)
    *   `questforge/utils/prompt_builder.py` (for prompts related to campaign generation and response generation)
    *   `questforge/utils/context_manager.py`
    *   Potentially `questforge/templates/game/play.html` for displaying new details.

### Phase 3: Complex Goals & Goal Tracking

*   **Goal**: Implement a system for defining, tracking, and evaluating multi-part, hierarchical player goals, allowing for more intricate campaign design.
*   **Key Changes**:
    *   **Define Complex Goal Structure**:
        *   **Current**: `major_plot_points` are relatively flat.
        *   **Proposed**: Introduce a more sophisticated data structure for `objectives` and `major_plot_points` within the `Campaign` model and `GameState.state_data`. This could involve:
            *   **Hierarchical Goals**: A main campaign objective broken down into several sub-objectives, each with its own description and completion criteria.
            *   **Dependencies**: Sub-objectives that must be completed before others.
            *   **Progress Indicators**: A way to track partial progress towards a goal (e.g., "3/5 items collected").
        *   **Implementation**: This will require schema changes (migrations), and updates to `ai_service.generate_campaign` to generate these complex structures.
    *   **Modify `ai_service.check_atomic_plot_completion`**:
        *   **Current**: Checks atomic plot points.
        *   **Proposed**: Adapt this function (or create a new `check_complex_goal_progress` function) to evaluate progress against these more complex goal structures. The AI would need to analyze the current game state, player action, and narrative to determine if a sub-goal has been met or if overall progress has been made.
    *   **Update `prompt_builder`**: Ensure prompts for AI (especially `get_response` and `check_atomic_plot_completion`) include the detailed structure of current active goals and their progress.
    *   **Frontend Display**: Update `questforge/templates/game/play.html` to visually represent these complex goals and the player's progress towards them.
*   **Affected Files**:
    *   `questforge/models/campaign.py` (for `major_plot_points` structure)
    *   `questforge/models/game_state.py` (for `state_data` structure documentation/implications)
    *   `migrations/versions/...` (new migration file for schema changes)
    *   `questforge/services/ai_service.py` (for `generate_campaign`, `check_atomic_plot_completion` or new function)
    *   `questforge/utils/prompt_builder.py`
    *   `questforge/templates/game/play.html`

### Phase 4: AI-Driven Dynamic Behavior (Leveraging Persistent Memory)

*   **Goal**: Make NPCs and the world react more dynamically and intelligently based on the accumulated historical context and complex states.
*   **Key Changes**:
    *   **NPC Behavior Logic**:
        *   **Current**: NPC behavior is largely reactive to the immediate prompt.
        *   **Proposed**: Implement logic (potentially within `socket_service.handle_player_action` or a new `npc_service`) that uses the AI to determine NPC reactions, dialogue, and even proactive actions based on their:
            *   Persistent memory of past player interactions.
            *   Current disposition towards the player.
            *   Knowledge of the world and plot.
            *   Their own internal goals.
        *   **Implementation**: This would involve new AI calls or more complex prompt engineering within existing calls to generate NPC responses and actions.
    *   **World State Evolution**:
        *   **Current**: World changes are primarily direct results of player actions.
        *   **Proposed**: Allow the AI to drive subtle, background changes in the world based on past events and object states, making the environment feel more alive and reactive to the passage of time or player inaction.
        *   **Implementation**: This might involve periodic AI calls or specific triggers to update world object conditions or introduce new elements.
    *   **Adaptive Narrative**:
        *   **Current**: Narrative is generated per turn.
        *   **Proposed**: The AI can use the deep context to generate narratives that are highly tailored to the player's unique journey, past decisions, and the evolving state of NPCs and objects. This could include branching storylines or personalized challenges.
*   **Affected Files**:
    *   `questforge/services/socket_service.py` (for orchestrating AI calls and state updates)
    *   `questforge/services/ai_service.py` (for new AI functions or enhanced existing ones)
    *   Potentially new service files (e.g., `questforge/services/npc_service.py`, `questforge/services/world_service.py`)
    *   `questforge/utils/prompt_builder.py`

This detailed plan provides a roadmap for leveraging the large context window. Each phase builds upon the previous one, ensuring a structured and manageable implementation process.
