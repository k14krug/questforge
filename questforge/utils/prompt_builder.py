import json # Import the json module
from questforge.models.template import Template
from questforge.models.game_state import GameState # Import GameState for build_response_prompt later
from typing import Dict, Optional, Any, List # Import Dict, Optional, Any, List for type hinting

def build_campaign_prompt(template: Template, template_overrides: Optional[Dict[str, Any]] = None, creator_customizations: Optional[Dict[str, Any]] = None, player_details: Optional[Dict[str, Dict[str, str]]] = None) -> str:
    """
    Builds the prompt for the AI to generate a campaign based on a template, template overrides, creator customizations, and player details (name and description).

    Args:
        template: The Template object.
        template_overrides: Optional dictionary of fields to override from the template.
        creator_customizations: Optional dictionary of creator-provided customizations.
        player_details: Optional dictionary mapping user_id (str) to a dict containing 'name' (str or None) and 'description' (str).

    Returns:
        A string containing the prompt for the AI.
    """
    # Ensure overrides, customizations, and details are dictionaries if None
    template_overrides = template_overrides or {}
    creator_customizations = creator_customizations or {}
    player_details = player_details or {} # Ensure it's a dict

    # --- Logging Start ---
    import logging # Import logging locally for this function
    logger = logging.getLogger(__name__) # Get a logger instance
    logger.setLevel(logging.DEBUG) # Ensure debug messages are processed if handler level allows
    
    # Basic check if handlers are configured - assumes Flask setup adds handlers
    if not logging.getLogger().hasHandlers():
         logging.basicConfig(level=logging.DEBUG) # Basic config if no handlers found
         
    logger.debug("--- Building Campaign Prompt ---")
    logger.debug(f"Template ID: {template.id}")
    logger.debug(f"Template Overrides Received: {template_overrides}")
    logger.debug(f"Creator Customizations Received: {creator_customizations}")
    logger.debug(f"Player Details Received: {player_details}") # Log player details
    # --- Logging End ---

    prompt_lines = [
        "You are a creative and detailed Game Master designing a text-based adventure game campaign.",
        "Your goal is to generate a complete campaign structure based on the provided template guidance, template overrides, and creator customizations.",
        "---",
        "TEMPLATE GUIDANCE:",
    ]

    # Helper function to add line and log override status
    def add_line(field_key, field_label):
        template_value = getattr(template, field_key, None)
        override_value = template_overrides.get(field_key)
        final_value = override_value if override_value is not None else template_value
        
        log_msg = f"Field '{field_key}': Template='{template_value}', Override='{override_value}', Final='{final_value}'"
        logger.debug(log_msg)
        
        if final_value is not None and final_value != '': # Only add if there's a final value
            # Special handling for JSON fields like default_rules
            if field_key == 'default_rules' and isinstance(final_value, (dict, list)):
                 prompt_lines.append(f"- {field_label}: {json.dumps(final_value)}")
            elif isinstance(final_value, str): # Ensure it's a string otherwise
                 prompt_lines.append(f"- {field_label}: {final_value}")
            # Add more type checks if needed

    # Add fields using the helper
    add_line('name', 'Name')
    add_line('genre', 'Genre')
    add_line('core_conflict', 'Core Conflict/Goal')
    add_line('description', 'Description')
    add_line('theme', 'Theme')
    add_line('desired_tone', 'Desired Tone')
    add_line('world_description', 'World Description')
    add_line('scene_suggestions', 'Scene Suggestions')
    add_line('player_character_guidance', 'Player Character Guidance')
    
    # Handle Difficulty with more specific instructions
    difficulty_value = template_overrides.get('difficulty', getattr(template, 'difficulty', 'medium')) # Default to medium if not found
    if difficulty_value:
        prompt_lines.append(f"- Difficulty: {difficulty_value.capitalize()}")
        if str(difficulty_value).lower() == 'easy':
            prompt_lines.append("  - Interpretation: Generate a straightforward adventure. Resources should be relatively easy to find. Challenges should be simpler, and NPCs more helpful. Plot points should be clearly signposted.")
        elif str(difficulty_value).lower() == 'medium':
            prompt_lines.append("  - Interpretation: Generate a balanced adventure. Resources are available but may require some effort. Challenges are present but fair. NPCs offer a mix of help and hindrance. Plot points require some investigation.")
        elif str(difficulty_value).lower() == 'hard':
            prompt_lines.append("  - Interpretation: Generate a challenging scenario. Resources should be scarce or well-guarded. Adversaries should be cunning and obstacles significant. NPCs might be deceptive or unhelpful. Plot points may be obscure and require clever solutions. Consider fewer initial resources or more complex starting situations for the players.")
        elif str(difficulty_value).lower() == 'very hard':
            prompt_lines.append("  - Interpretation: Generate an extremely difficult scenario. Resources are exceptionally rare and dangerous to obtain. Adversaries are highly intelligent and unforgiving. Obstacles are numerous and complex. NPCs are likely hostile or misleading. Plot points are deeply hidden and require exceptional insight. The initial situation should be perilous.")
    
    add_line('estimated_length', 'Estimated Length')
    add_line('default_rules', 'Default Rules/Mechanics') # Handles JSON

    # Add Creator Customizations section
    if creator_customizations:
        prompt_lines.append("---")
        prompt_lines.append("CREATOR CUSTOMIZATIONS:")
        customization_added = False
        for key, value in creator_customizations.items():
            if value: # Only include if value is not empty
                prompt_lines.append(f"- {key.replace('_', ' ').title()}: {value}")
                customization_added = True
        if not customization_added:
                 prompt_lines.pop() # Remove "CREATOR CUSTOMIZATIONS:" header if nothing was added
                 prompt_lines.pop() # Remove "---" separator if nothing was added

    # Add Player Characters section if details exist
    if player_details:
        prompt_lines.append("---")
        prompt_lines.append("PLAYER CHARACTERS:")
        for user_id, details in player_details.items():
            name = details.get('name')
            description = details.get('description')
            player_label = f"Player (ID: {user_id})"
            name_display = f"Name: {name}" if name else "Name: (Not Provided)"
            prompt_lines.append(f"- {player_label} - {name_display}: {description}")
        if not player_details: # If dict was empty after filtering (unlikely here but safe)
             prompt_lines.pop() # Remove "PLAYER CHARACTERS:" header
             prompt_lines.pop() # Remove "---" separator

    # Add Task Description section
    prompt_lines.extend([
        "---",
        "YOUR TASK:",
        "Based primarily on the Template Guidance, Template Overrides, Creator Customizations, and Player Characters (if provided) above, generate a complete campaign structure. Be creative and fill in the details, ensuring the generated components align cohesively with all provided inputs.",
        "Generate the following components:",
        "1.  **campaign_objective:** A clear, concise overall objective for the players, directly derived from the `Core Conflict/Goal` field in the TEMPLATE GUIDANCE section above.",
        "2.  **generated_locations:** A JSON list of 3-5 key location objects. Inspired by `World Description` and `Scene Suggestions`, fitting `Theme` and `Desired Tone`, relevant to `campaign_objective`, and incorporating any locations from `Creator Customizations`. Each object: 'name', 'description'.",
        "    - Example: `[{\"name\": \"Whispering Caves\", \"description\": \"A dark, damp cave system rumored to hold the artifact.\"}, ...]`",
        "3.  **generated_characters:** A JSON list of 2-3 key NPC objects relevant to plot and `campaign_objective`. Align with `Theme` and `Desired Tone`, incorporating NPCs from `Creator Customizations`. Each object: 'name', 'role', 'description'.",
        "    - Example: `[{\"name\": \"Elara\", \"role\": \"Mysterious Guide\", \"description\": \"An old hermit who knows the mountain paths.\"}, ...]`",
        "4.  **generated_plot_points:** A JSON list outlining 3-5 major stages/events progressing towards `campaign_objective`. **CRITICAL: Each plot point MUST be ATOMIC**, representing a single, verifiable condition or achievement. Avoid compound objectives.",
        "    - Each item MUST be a JSON object with 'id' (string, unique, simple, e.g., \"pp_001\", \"obj_reactor\"), 'description' (string, clearly stating the single condition), and 'required' (boolean).",
        "    - Ensure 'id' values are unique. At least one plot point should be 'required: true'.",
        "    - **Atomicity Examples:**",
        "        - **GOOD (Atomic):** `{\"id\": \"pp_find_key\", \"description\": \"Player finds the rusty cell key.\", \"required\": true}`",
        "        - **GOOD (Atomic):** `{\"id\": \"pp_unlock_door\", \"description\": \"Player unlocks the cell door using the rusty key.\", \"required\": true}` (Depends on previous)",
        "        - **BAD (Compound):** `{\"id\": \"pp_key_and_door\", \"description\": \"Player finds the key and unlocks the door.\", \"required\": true}` (This should be two separate plot points)",
        "        - **GOOD (Atomic):** `{\"id\": \"pp_talk_guard\", \"description\": \"Player convinces the guard to share information about the escape route.\", \"required\": true}`",
        "        - **BAD (Vague/Multiple Outcomes):** `{\"id\": \"pp_interact_guard\", \"description\": \"Player interacts with the guard.\", \"required\": true}` (What is the specific, verifiable outcome?)",
        "    - Consider `Player Character Guidance` and `PLAYER CHARACTERS` details. Incorporate plot hooks from `Creator Customizations`.",
        "    - Example List: `[{\"id\": \"pp_001\", \"description\": \"Players learn about the stolen artifact from the village elder.\", \"required\": true}, {\"id\": \"pp_002\", \"description\": \"Players find a map fragment in the abandoned shack.\", \"required\": false}, {\"id\": \"pp_003\", \"description\": \"Players reach the entrance of the Whispering Caves.\", \"required\": true}, ...]`",
        "5.  **initial_scene:** A JSON object describing the start. 'description' sets the scene vividly (using `Theme`, `Desired Tone`, and incorporating the provided `PLAYER CHARACTERS` details, **referring to players by their provided names**). 'state' MUST include 'location'. 'goals' are 1-3 immediate actions. Align with relevant `Creator Customizations` (e.g., starting location).", # Updated instruction to use names
        "    - Example: `{\"description\": \"Torbin, the gruff warrior, and Lyra, the nimble rogue, awaken in a damp cellar...\", \"state\": {\"location\": \"Tavern Cellar\"}, \"goals\": [\"Look for a way out\", \"Search the barrels\", \"Listen at the door\"]}`", # Updated example to use names
        "6.  **campaign_summary (Optional):** Brief overall summary.",
        "7.  **conclusion_conditions:** JSON *list* of condition objects that MUST ALL be met. Each object: 'type' and parameters. Supported types: `state_key_equals`, `state_key_exists`, `state_key_contains`, `location_visited`.",
        "    - Example: `[{\"type\": \"state_key_equals\", \"key\": \"boss_defeated\", \"value\": true}, {\"type\": \"location_visited\", \"location\": \"Throne Room\"}]`",
        "8.  **possible_branches (Optional):** JSON object outlining 1-2 potential major narrative branches.",
        "9.  **special_rules (Optional):** JSON object or string outlining special rules, incorporating rules from `Creator Customizations`.",
        "10. **exclusions (Optional):** JSON list of strings outlining exclusions, incorporating exclusions from `Creator Customizations`.",
        "---",
        "OUTPUT FORMAT:",
        "Provide the entire response as a single, valid JSON object containing the keys corresponding to the numbered items above (e.g., `campaign_objective`, `generated_locations`, etc.). Ensure all nested values are valid JSON.",
        "---",
        "Generate the complete campaign structure JSON now:"
    ])

    # Clean up potential None values before joining
    final_prompt = "\n".join([str(line) for line in prompt_lines if line is not None])
    
    # --- Logging Start ---
    logger.debug("--- Final Campaign Prompt ---")
    logger.debug(final_prompt)
    logger.debug("-----------------------------")
    # --- Logging End ---
    
    return final_prompt


def build_response_prompt(context: str, player_action: str, is_stuck: bool = False, next_required_plot_point: Optional[str] = None, current_difficulty: Optional[str] = None) -> str:
    """
    Generates a prompt for the AI to respond to a player's action, given the game context.

    Args:
        context: A string containing the relevant game context (campaign info, current state, current objective).
        player_action: The action taken by the player as a string.
        is_stuck: Boolean indicating if the player might be stuck.
        next_required_plot_point: Optional string describing the next required plot point (used for hints).

    Returns:
        A string containing the formatted prompt for the AI.
    """
    prompt_lines = [
        "You are a Game Master for a text-based adventure game. This is Stage 1 of a multi-stage response generation.",
        "Your primary task is to: ",
        "  a) Generate a compelling narrative description of the direct and immediate result of the player's stated action. Detail what happens in this single moment or step.",
        "  b) Provide a comprehensive and DETAILED update to the general game state based on the action's outcome. This includes player location, inventory changes, NPC presence/status/relationships, and the state of relevant world objects or environmental conditions.",
        "Focus your response on what transpires in *this specific turn*. Do not narrate subsequent actions the player characters might take, or events that would logically follow *after* the immediate outcome, unless they are an unavoidable and instantaneous consequence.",
        "The narrative should pause, awaiting the next player input. After describing the outcome, ensure your 'available_actions' present clear choices for the player to drive the story forward.",
        "**IMPORTANT: Refer to players by their names as listed in the 'Players Present' section of the context.**",
        "DO NOT attempt to determine if a plot point has been completed. That will be handled by a separate process. Your focus is SOLELY on narrative and detailed general state updates.",
        "---",
        "Consider the following aspects while generating the response:",
        "1. **Narrative Consistency & Logic:** Ensure the response is consistent with the overall game state (location, inventory, character status, completed plot points, players present). Deny actions that are illogical (e.g., using an item not possessed). If an action attempts to bypass or ignore a clear objective from the 'Current Objective/Focus' without strong narrative justification, your response should explain *why* it's difficult or impossible at this time. Maintain narrative consistency with any defined plot points from the game context.",
        "2. **Narrative Description:** Provide a vivid and engaging description of the outcome. **Use the players' names when describing their actions or interactions.**",
    ]

    # Add difficulty-based instructions for handling unreasonable actions
    if current_difficulty:
        difficulty_instructions = {
            "easy": "3. **Difficulty - Easy:** The game master should be very forgiving. If the player's action is unreasonable or unlikely to succeed, gently guide them back or allow for a partial success / humorous outcome. Avoid harsh failures.",
            "normal": "3. **Difficulty - Normal:** If the player's action is unreasonable or unlikely to succeed, the game master should respond realistically. This might mean the action fails, has unintended consequences, or NPCs react appropriately to the absurdity. Provide a clear outcome.",
            "hard": "3. **Difficulty - Hard:** If the player's action is unreasonable or unlikely to succeed, the game master should be strict. The action should likely fail, potentially with negative consequences. NPCs should react strongly to foolish actions. Maintain a challenging environment."
        }
        # Default to Normal if difficulty is not recognized, or handle as an error/log
        instruction = difficulty_instructions.get(current_difficulty.lower(), difficulty_instructions["normal"])
        prompt_lines.append(instruction)
    else:
        # Default behavior if no difficulty is passed (should ideally always be passed)
        prompt_lines.append("3. **Difficulty - Normal (Default):** If the player's action is unreasonable or unlikely to succeed, the game master should respond realistically. This might mean the action fails, has unintended consequences, or NPCs react appropriately to the absurdity. Provide a clear outcome.")


    if is_stuck and next_required_plot_point: # This part can remain as it influences narrative
        prompt_lines.append(f"4. **Player Guidance (Subtle Hint):** The player might be stuck. If so, subtly weave a hint related to the 'Current Objective/Focus' ('{next_required_plot_point}') into your narrative description or suggest a relevant action. Make it feel natural.")
    
    prompt_lines.extend([
        "5. **Detailed State Changes:** Clearly outline ALL relevant changes to the general game state resulting from the action. Be thorough and specific. Examples of state keys to update if relevant:",
        "   - `location`: (string) The player's new location. **This is mandatory.**",
        "   - `inventory_changes`: (object, optional) e.g., `{\"items_added\": [{\"name\": \"key\", \"description\": \"A small brass key\"}], \"items_removed\": [\"ration\"]}`. Include item descriptions if new.",
        "   - `npc_status`: (object, optional) For EACH NPC affected or present: `{\"NPC Name\": {\"status\": \"hostile\"/\"friendly\"/\"neutral\"/\"unconscious\"/\"gone\", \"location\": \"current_location_if_moved_or_still_present\", \"relationship_to_player_X\": \"allied\"/\"suspicious\"}}`. Update status, location if they move, and relationships if they change.",
        "   - `world_object_states`: (object, optional) e.g., `{\"lever_A\": \"pulled\", \"ancient_door\": \"sealed\", \"computer_terminal\": {\"status\": \"online\", \"accessed_files\": [\"log_001\"]}}`.",
        "   - `environmental_conditions`: (object, optional) e.g., `{\"weather\": \"stormy\", \"time_of_day\": \"night\", \"light_level\": \"dim\"}`.",
        "   - `player_character_status`: (object, optional) e.g., `{\"Player1_ID\": {\"condition\": \"injured\", \"mana\": 50}, \"Player2_ID\": {\"carrying_npc_id\": \"npc_elara\"}}`.",
        "   - **Critical Event Flags for Conclusion:** Review the 'Conclusion Conditions' list provided in the Game Context. If the player's *single, current action directly results* in satisfying one of these conditions (e.g., the narrative describes a successful escape and a condition is `{'type': 'state_key_equals', 'key': 'escaped', 'value': true}`), YOU MUST include the corresponding key and value (e.g., `'escaped': true`) in your `state_changes` object. This is essential for the game to recognize the conclusion.",
        "   If an action is denied or has no significant effect, state changes might be minimal (e.g., only location if it didn't change, or an empty object for other categories).",
        "6. **Available Actions:** List relevant actions the player can take *after* this event, reflecting the new situation. These should be logical next steps based on the narrative and updated state.",
        "---",
        "Your response MUST be a JSON object containing three keys:",
        "1. 'content': A string describing the narrative outcome of the action.",
        "2. 'state_changes': A JSON object detailing ALL relevant general game state variables after the action. **Crucially, this object MUST ALWAYS include the 'location' key.** Do NOT include `achieved_plot_point_id`. Example: `{'location': 'Cave Entrance', 'inventory_changes': {'items_added': [{'name':'torch', 'description':'A lit torch'}]}, 'npc_status': {'Goblin Sentry': {'status':'unconscious', 'location':'Cave Entrance'}}, 'world_object_states': {'trap_A':'disarmed'}, 'bomb_disabled': true}`.",
        "3. 'available_actions': A JSON list of strings representing the actions the player can take next (e.g., `['Look around', 'Check inventory', 'Go north']`).",
        "---",
        "Game Context:",
        context, # Insert the pre-built context string
        "---",
        f"Player Action: {player_action}",
        "---",
        "Generate the JSON response now:"
    ])

    return "\n".join(prompt_lines)


def build_plot_completion_check_prompt(
    plot_point_id: str,
    plot_point_description: str,
    current_game_state_data: Dict[str, Any],
    player_action: str,
    stage_one_narrative: str
) -> str:
    """
    Builds the prompt for the AI to check if a specific atomic plot point was completed.
    This is for Stage 3 of the plot point completion strategy.

    Args:
        plot_point_id: The ID of the atomic plot point to check.
        plot_point_description: The description of the atomic plot point.
        current_game_state_data: The full current GameState.state_data dictionary.
        player_action: The player's original action from the current turn.
        stage_one_narrative: The narrative generated by the Stage 1 AI in the current turn.

    Returns:
        A string containing the prompt for the AI.
    """
    prompt_lines = [
        "You are an analytical AI assistant evaluating game events with high precision.",
        "Your task is to determine if a specific, single game objective (an atomic plot point) has been completed based on the provided information. Scrutinize all provided context.",
        "---",
        "OBJECTIVE TO EVALUATE:",
        f"  Plot Point ID: {plot_point_id}",
        f"  Description: \"{plot_point_description}\"",
        "---",
        "CRITERIA FOR COMPLETION (General Guidelines - adapt to the specific plot point description):",
        "  - **Location-based:** Is the player (or relevant entity) at the specified location AND has any other condition tied to that location in the plot point description been met? (e.g., 'Reach the Control Room and activate the console'). The `current_game_state_data.location` is key.",
        "  - **Item-based (Acquisition/Usage):** Has the player acquired the necessary item, or used it in the manner described? Check `current_game_state_data.inventory_changes` or other relevant state keys for item presence/usage.",
        "  - **NPC Interaction:** Has the specified interaction with an NPC occurred as described (e.g., 'Convince Guard Captain to help', 'Defeat the Goblin Sentry')? Look for changes in `current_game_state_data.npc_status` or narrative confirmation.",
        "  - **State Change:** Does the `current_game_state_data` reflect a specific condition mentioned in the plot point (e.g., 'Disable the security system' might be `current_game_state_data.security_system_status: \"disabled\"`)?",
        "  - **Action-based:** Did the player's action *directly and unambiguously* fulfill the plot point's requirement as described in the narrative and reflected in state changes?",
        "  - **Information Gathering:** Has the player obtained the specific piece of information mentioned in the plot point? This might be reflected in the narrative or a specific state variable.",
        "---",
        "CONTEXT FOR EVALUATION:",
        f"  1. Player's Action This Turn: \"{player_action}\"",
        f"  2. Narrative Result of Action (from Stage 1 AI): \"{stage_one_narrative}\"",
        "     - Pay close attention to explicit statements in the narrative that confirm or deny the objective's conditions.",
        "  3. Full Current Game State Data (this reflects changes from the player's action and Stage 1 AI):",
        f"     {json.dumps(current_game_state_data, indent=2)}",
        "     - This is the **primary source of truth** for objective conditions. The narrative should align with state changes.",
        "---",
        "INSTRUCTION:",
        f"Carefully consider the objective for plot point \"{plot_point_id}\" (Description: \"{plot_point_description}\").",
        "Evaluate if this specific atomic plot point was **directly and unambiguously** completed **THIS TURN** based on the player's action, the narrative result, AND, most importantly, the **Full Current Game State Data**.",
        "Do not infer completion if the state data does not support it, even if the narrative is suggestive. The state data is paramount.",
        "---",
        "Your response MUST be a single, valid JSON object with NO additional text before or after it. The JSON object must contain exactly these three keys:",
        "1. `plot_point_id`: The string ID of the plot point you evaluated (which MUST be \"{plot_point_id}\").",
        "2. `completed`: A boolean value (`true` or `false`). Set to `true` ONLY if all conditions of the plot point description are met according to the provided context, especially the game state data.",
        "3. `confidence_score`: A floating-point number between 0.0 (no confidence) and 1.0 (absolute confidence) representing your certainty in the `completed` status. Be conservative with high confidence unless completion is undeniable from the state and narrative.",
        "---",
        "Example of a valid JSON response (DO NOT include this example in your actual response):",
        "{\"plot_point_id\": \"pp_example_001\", \"completed\": true, \"confidence_score\": 0.85}",
        "---",
        "Generate the JSON response now for plot point \"{plot_point_id}\":"
    ]
    return "\n".join(prompt_lines)


def build_character_name_prompt(description: str) -> str:
    """
    Builds a prompt to ask the AI to generate a character name based on a description.

    Args:
        description: The character description provided by the player.

    Returns:
        A string containing the prompt for the AI.
    """
    prompt = f"""
Generate a single, suitable, creative fantasy character name based *only* on the following description.
Output *only* the name itself, with no extra text, labels, or quotation marks.

Description: "{description}"

Generated Name:"""
    return prompt.strip()


def build_hint_prompt(context: str, campaign_objective: Optional[str] = None, next_required_plot_point_desc: Optional[str] = None) -> str:
    """
    Builds a prompt for the AI to generate a game hint.

    Args:
        context: The current game context string (includes recent log, current location, etc.).
        campaign_objective: The overall campaign objective.
        next_required_plot_point_desc: The description of the next immediate required plot point.

    Returns:
        A string containing the prompt for the AI.
    """
    prompt_lines = [
        "You are a helpful Game Master for a text-based adventure game.",
        "A player has asked for a hint. Your goal is to provide a subtle, non-spoilery clue to help them progress.",
        "Consider the provided game context, the overall campaign objective, and especially the next immediate required plot point.",
        "---",
        "GAME CONTEXT:",
        context,
        "---"
    ]

    if campaign_objective:
        prompt_lines.append(f"Overall Campaign Objective: {campaign_objective}")
    
    if next_required_plot_point_desc:
        prompt_lines.append(f"Next Immediate Goal/Plot Point: {next_required_plot_point_desc}")
    
    prompt_lines.extend([
        "---",
        "YOUR TASK:",
        "Based on all the information above, provide one concise, subtle hint to guide the player. The hint should encourage exploration or thought related to their current situation or next objective.",
        "Do NOT give away direct solutions or spoil upcoming events.",
        "Output ONLY the hint text itself, as a single string. No extra labels, no JSON.",
        "---",
        "Hint:"
    ])
    return "\n".join(prompt_lines)


def build_summary_prompt(player_action: str, stage_one_narrative: str, state_changes: Dict[str, Any]) -> str:
    """
    Builds a prompt for the AI to summarize a game turn.

    Args:
        player_action: The action taken by the player.
        stage_one_narrative: The narrative response from the Stage 1 AI.
        state_changes: The state changes resulting from the action and Stage 1 AI.

    Returns:
        A string containing the prompt for the summarization AI.
    """
    prompt_lines = [
        "You are an AI assistant tasked with summarizing game events concisely.",
        "Based on the player's action, the resulting narrative, and any state changes, provide a single, concise sentence that captures the most significant outcome or event of this turn.",
        "Focus on what materially changed or what key information was revealed.",
        "Output ONLY the summary sentence itself, with no extra text, labels, or quotation marks.",
        "---",
        "PLAYER ACTION:",
        f"\"{player_action}\"",
        "---",
        "NARRATIVE RESULT (from main game AI):",
        f"\"{stage_one_narrative}\"",
        "---",
        "STATE CHANGES (key-value pairs of what changed):"
    ]

    if state_changes:
        for key, value in state_changes.items():
            prompt_lines.append(f"- {key}: {json.dumps(value)}")
    else:
        prompt_lines.append("No significant state changes occurred.")
    
    prompt_lines.extend([
        "---",
        "CONCISE SUMMARY SENTENCE:"
    ])
    return "\n".join(prompt_lines)
