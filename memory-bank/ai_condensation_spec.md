# AI Condensation Specification: "Story So Far" Summaries & NPC Memory

This document provides clear input/output formats and condensation criteria for AI-generated "Story So Far" summaries and `npc_memory` condensation within the QuestForge application. These processes are managed by the `AIService` layer, utilizing secondary AI models for efficiency.

## 1. AI-Generated "Story So Far" Summaries

The "Story So Far" summary provides a concise, narrative overview of the game's progression, intended to be used as part of the AI's context package for generating new narrative turns and for players to quickly catch up.

### 1.1 Input Format for AI

The AI will receive a structured context package to generate the summary. This package will primarily consist of:

*   **Campaign Charter (Immutable):** The full `campaign_charter` JSON object, providing the foundational context of the game (core conflict, world elements, objectives, etc.).
*   **Recent Game Log Entries:** A specified number of the most recent `game_log` entries (e.g., the last 20-50 entries, or entries from the last 1-2 in-game "days" if a time system is implemented). These entries will be provided in their structured JSON format.
*   **Current Game State Snapshot:** Key mutable elements from the `GameState` model, including:
    *   `current_location`: The party's current location.
    *   `completed_objectives`: Current status of critical path objectives.
    *   `discovered_lore_items`: Recently discovered lore items.
    *   `active_npcs`: A list of currently active NPCs and their most recent `condensed_memory` (if available).
    *   `player_states`: High-level summaries of player character states (e.g., health, major status effects, current location if different from party).

### 1.2 Output Format from AI

The AI is expected to return a plain text string for the "Story So Far" summary.

*   **Format:** A concise, narrative paragraph or a short series of bullet points summarizing key events.
*   **Length:** Aim for 100-300 words.
*   **Tone:** Should match the `ai_gm_persona` defined in the Campaign Charter.

### 1.3 Condensation Criteria & Generation Triggers

*   **Trigger:**
    *   **On Demand:** When explicitly requested by the `AIService` as part of the context package for a new AI turn.
    *   **Periodic:** Potentially after a certain number of turns (e.g., every 5-10 turns) or when a major objective is completed, to update the `current_story_summary` field in the `GameState` model.
*   **Criteria:**
    *   **Focus on Plot Progression:** Prioritize events that advance the main narrative, critical path objectives, and significant character interactions.
    *   **Summarize, Don't Detail:** Avoid re-telling every minor event. Condense sequences of actions into their overall outcome.
    *   **Key Information Only:** Include only information relevant to understanding the current state and immediate future of the campaign.
    *   **Maintain Consistency:** Ensure the summary aligns with the Campaign Charter and previously established narrative.
    *   **NPC Relevance:** Briefly mention active NPCs and their current status if they are central to the summarized events.

## 2. AI-Generated `npc_memory` Condensation

`npc_memory` condensation is crucial for maintaining consistent NPC behavior and responses without overwhelming the AI with excessive historical dialogue or observations. Each active NPC in the `GameState`'s `active_npcs` JSON field will have a `condensed_memory` sub-field.

### 2.1 Input Format for AI

The AI will receive specific context for condensing an individual NPC's memory:

*   **NPC's Core Profile:** Name, description, and any immutable traits from the Campaign Charter.
*   **Current `condensed_memory` (if exists):** The NPC's last condensed memory string.
*   **Recent Interactions:** A selection of recent `game_log` entries where this specific NPC was involved (e.g., direct dialogue, observations made by/about the NPC). This could be filtered by `actor` or by mentions of the NPC's name.
*   **Relevant Game State Changes:** Any recent changes in the `GameState` that directly affect this NPC (e.g., a quest they are involved in was completed, a key item they possess was taken).
*   **Current Location Context:** The `current_location` from `GameState` and its description from the Campaign Charter, if relevant to the NPC's recent activities.

### 2.2 Output Format from AI

The AI is expected to return a plain text string for the `condensed_memory`.

*   **Format:** A concise, factual summary of the NPC's recent experiences, observations, and current disposition. It should be written from an omniscient perspective, not the NPC's internal monologue.
*   **Length:** Aim for 50-150 words.
*   **Tone:** Neutral and informative, focusing on key facts.

### 2.3 Condensation Criteria & Generation Triggers

*   **Trigger:**
    *   **After Significant Interaction:** When an NPC has had a notable interaction with players or other NPCs (e.g., after a dialogue exchange, a combat encounter, or a quest update involving them).
    *   **Periodic:** Potentially after a certain number of turns or when the `GameState` is updated in a way that impacts the NPC's context.
*   **Criteria:**
    *   **Prioritize Impactful Events:** Focus on events that change the NPC's relationship with players, their knowledge, their physical state, or their immediate goals.
    *   **Summarize Dialogue:** Condense long conversations into key takeaways or decisions made.
    *   **Remove Redundancy:** Eliminate repetitive information or minor observations that don't contribute to the NPC's current state or future actions.
    *   **Maintain Key Facts:** Ensure critical information about quests, relationships, or recent events is retained.
    *   **Focus on "What Happened":** The memory should reflect what the NPC experienced or observed, not their internal thoughts or feelings unless those directly led to an observable action.
    *   **Conciseness:** Be as brief as possible while retaining essential information.
