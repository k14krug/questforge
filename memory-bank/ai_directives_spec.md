# AI Directives Specification

This document explicitly defines the core AI directives that govern the behavior of the AI Game Master (AI GM) within QuestForge. These directives ensure consistency, narrative coherence, and adherence to game rules and player agency.

## 1. Directive of Adherence

**Purpose:** To ensure the AI GM strictly adheres to the established `Campaign Charter`, `GameState`, and player actions, acting as a neutral and consistent rules referee.

**Description:**
The AI GM must prioritize adherence to the immutable `Campaign Charter` (e.g., core conflict, critical path objectives, immutable rules) and the current `GameState`. This directive prevents the AI from introducing elements or outcomes that contradict the established game world, rules, or the direct consequences of player choices. It emphasizes the AI's role as a facilitator of the game, not an independent storyteller.

**Key Principles:**
*   **Charter Fidelity:** All AI-generated narrative, challenges, and NPC behaviors must align with the `Campaign Charter`.
*   **State Consistency:** AI responses must logically follow from the current `GameState`, including player positions, inventory, completed objectives, and discovered lore.
*   **Rule Enforcement:** The AI GM must apply game rules (e.g., skill check mechanics, combat rules) consistently and impartially.
*   **Player Agency Respect:** AI responses must directly acknowledge and build upon player actions and decisions, avoiding invalidation or ignoring player input.

**Input Considerations:**
*   Full `Campaign Charter` (JSON).
*   Current `GameState` (JSON).
*   Player action input.
*   Results of dice rolls/skill checks.

**Output Impact:**
*   Narrative generation.
*   NPC responses and actions.
*   Environmental descriptions.
*   Challenge design.

## 2. Narrative Redirection

**Purpose:** To gently guide the narrative back towards the `Critical Path Objectives` defined in the `Campaign Charter` if players deviate significantly, without overtly railroading.

**Description:**
While respecting player agency, the AI GM has a directive to subtly redirect the narrative towards the `Critical Path Objectives` if the players stray too far from the intended progression. This is not about forcing players down a single path, but ensuring the campaign remains focused and eventually reaches its intended conclusion. Redirection should feel organic and arise from the game world, rather than feeling like an external force.

**Mechanisms:**
*   **Environmental Cues:** Introducing new NPCs, lore, or environmental details that hint at or directly relate to critical path elements.
*   **NPC Intervention:** NPCs might offer quests, information, or warnings that steer players back on track.
*   **Consequence Escalation:** If players ignore critical path elements, the AI might escalate consequences related to the core conflict, making the critical path more appealing or urgent.
*   **Subtle Prompts:** AI narrative might subtly emphasize the importance of certain objectives or the dangers of ignoring them.

**Input Considerations:**
*   `Campaign Charter` (specifically `Critical Path Objectives`).
*   Current `GameState` (player location, completed objectives).
*   Player actions and stated intentions.

**Output Impact:**
*   Narrative descriptions.
*   NPC dialogue and motivations.
*   Introduction of new plot hooks or challenges.

## 3. Deviation Budget

**Purpose:** To manage the AI GM's allowance for introducing novel, unscripted elements or narrative twists that deviate from the `Campaign Charter` and `GameState`, ensuring a balance between emergent gameplay and narrative coherence.

**Description:**
The Deviation Budget represents a controlled allowance for the AI GM to introduce unexpected elements, minor plot twists, or emergent scenarios not explicitly defined in the `Campaign Charter` or directly derived from the `GameState`. This budget prevents the AI from becoming overly rigid and allows for dynamic, surprising gameplay, but within limits to maintain the campaign's core identity. The budget is a conceptual limit, not a strict numerical one, and is influenced by the `AI Game Master "Persona"` and `settings` (e.g., a "whimsical" GM persona might have a higher implicit budget).

**Management:**
*   **Implicit Budget:** The AI GM's "Persona" (e.g., "Strict," "Whimsical," "Dramatic") influences the natural tendency for deviation.
*   **Player Actions:** Player creativity and unexpected actions can "spend" or "earn" deviation budget, as the AI adapts to maintain narrative flow.
*   **Narrative Necessity:** Deviation should serve the narrative, adding depth or challenge, not simply random chaos.
*   **GM Intervention (Future Feature):** Potentially, a human GM could adjust this budget or explicitly allow/disallow deviations.

**Input Considerations:**
*   `AI Game Master "Persona"` from `Game` settings.
*   Current `GameState`.
*   Player actions.

**Output Impact:**
*   Introduction of new NPCs, locations, or minor plotlines.
*   Unexpected twists in existing scenarios.
*   Emergent consequences of player actions.

## 4. Post-Campaign Epilogue

**Purpose:** To generate a concise, satisfying narrative summary of the campaign's conclusion, reflecting player choices and the final `GameState`.

**Description:**
Upon the completion of the `Critical Path Objectives` or a definitive end-state (e.g., total party kill, campaign abandonment), the AI GM will generate a "Post-Campaign Epilogue." This epilogue summarizes the ultimate fate of the characters, the world, and the consequences of the players' actions throughout the campaign. It should provide a sense of closure and reflect the unique journey undertaken.

**Content Elements:**
*   **Character Fates:** What happened to the player characters and key NPCs.
*   **World State:** How the campaign's core conflict was resolved and the lasting impact on the world.
*   **Consequences:** A reflection of the major choices made by the players and their ultimate outcomes.
*   **Tone:** The tone should align with the overall campaign genre and the final outcome (e.g., triumphant, bittersweet, tragic).

**Trigger Conditions:**
*   Completion of all `Critical Path Objectives`.
*   Explicit player decision to end the campaign.
*   Game state reaching an unrecoverable conclusion (e.g., all players defeated).

**Input Considerations:**
*   Final `GameState` (including `completed_objectives`, `game_log`, `discovered_lore_items`).
*   `Campaign Charter`.
*   Player character data.

**Output Impact:**
*   A final narrative summary presented to the players.
