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
    add_line('difficulty', 'Difficulty')
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
        "4.  **generated_plot_points:** A JSON list outlining 3-5 major stages/events progressing towards `campaign_objective`, reflecting `Core Conflict/Goal`. Consider `Player Character Guidance` and the provided `PLAYER CHARACTERS` details (names and descriptions). Incorporate plot hooks from `Creator Customizations`. Each item: descriptive string.", # Updated reference to PLAYER CHARACTERS
        "    - Example: `[\"Players investigate the initial theft.\", \"Players track the thieves to the Whispering Caves.\", \"Players confront the guardian within the caves.\", ...]`",
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


def build_response_prompt(context: str, player_action: str) -> str:
    """
    Generates a prompt for the AI to respond to a player's action, given the game context.

    Args:
        context: A string containing the relevant game context (campaign info, current state).
        player_action: The action taken by the player as a string.

    Returns:
        A string containing the formatted prompt for the AI.
    """
    prompt_lines = [
        "You are a Game Master for a text-based adventure game.",
        "Based on the provided context and the player's action, describe what happens next.",
        "**IMPORTANT: Refer to players by their names as listed in the 'Players Present' section of the context.**", # Added instruction
        "Consider the following aspects while generating the response:",
        "1. **Narrative Consistency & Logic:** Evaluate the player's action against the current game state (location, inventory, character status, plot points, players present) and narrative consistency. Provide narrative consequences or deny actions that are illogical (e.g., using an item not possessed, finding something not present, interacting with something impossible). Prioritize realistic outcomes and narrative progression over simply executing the player's command verbatim.",
        "2. **Narrative Description:** Provide a vivid and engaging description of the outcome, reflecting the consequences of the action based on the evaluation in point 1. **Use the players' names when describing their actions or interactions.**", # Added instruction
        "3. **State Changes:** Clearly outline any changes to the game state resulting from the action. If an action is denied or has no effect, state changes might be minimal or empty.",
        "4. **Available Actions:** List the relevant actions the player can take *after* this event, reflecting the new situation.",
        "---",
        "Your response MUST be a JSON object containing three keys:",
        "1. 'content': A string describing the narrative outcome of the action.",
        "2. 'state_changes': A JSON object detailing ALL relevant game state variables after the action. **Crucially, this object MUST ALWAYS include the 'location' key, reflecting the player's current location after this action, even if it hasn't changed from the context.** Other examples: `{'player_health': -10, 'location': 'Cave Entrance', 'items_added': ['torch']}`.",
        "3. 'available_actions': A JSON list of strings representing the actions the player can take next from the current state (e.g., `['Look around', 'Check inventory', 'Go north']`).",
        "---",
        "Game Context:",
        context, # Insert the pre-built context string
        "---",
        f"Player Action: {player_action}",
        "---",
        "Generate the JSON response now:"
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
