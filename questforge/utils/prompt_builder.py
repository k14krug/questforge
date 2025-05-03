import json # Import the json module
from questforge.models.template import Template
from questforge.models.game_state import GameState # Import GameState for build_response_prompt later
from typing import Dict, Optional, Any # Import Dict, Optional, and Any for type hinting

def build_campaign_prompt(template: Template, template_overrides: Optional[Dict[str, Any]] = None, creator_customizations: Optional[Dict[str, Any]] = None) -> str:
    """
    Builds the prompt for the AI to generate a campaign based on a template, template overrides, and creator customizations.

    Args:
        template: The Template object.
        template_overrides: Optional dictionary of fields to override from the template.
        creator_customizations: Optional dictionary of creator-provided customizations.

    Returns:
        A string containing the prompt for the AI.
    """
    prompt_lines = [
        "You are a creative and detailed Game Master designing a text-based adventure game campaign.",
        "Your goal is to generate a complete campaign structure based on the provided template guidance, template overrides, and creator customizations.", # Updated guidance
        "---",
        "TEMPLATE GUIDANCE:",
        # Use template_overrides if available, otherwise use template data
        f"- Name: {template_overrides.get('name', template.name)}",
        f"- Genre: {template_overrides.get('genre', template.genre)}",
        f"- Core Conflict/Goal: {template_overrides.get('core_conflict', template.core_conflict)}",
    ]
    # Add optional fields, prioritizing overrides
    if template_overrides.get('description') is not None or template.description:
        prompt_lines.append(f"- Description: {template_overrides.get('description', template.description or '')}")
    if template_overrides.get('theme') is not None or template.theme:
        prompt_lines.append(f"- Theme: {template_overrides.get('theme', template.theme or '')}")
    if template_overrides.get('desired_tone') is not None or template.desired_tone:
        prompt_lines.append(f"- Desired Tone: {template_overrides.get('desired_tone', template.desired_tone or '')}")
    if template_overrides.get('world_description') is not None or template.world_description:
        prompt_lines.append(f"- World Description: {template_overrides.get('world_description', template.world_description or '')}")
    if template_overrides.get('scene_suggestions') is not None or template.scene_suggestions:
        prompt_lines.append(f"- Scene Suggestions: {template_overrides.get('scene_suggestions', template.scene_suggestions or '')}")
    if template_overrides.get('player_character_guidance') is not None or template.player_character_guidance:
        prompt_lines.append(f"- Player Character Guidance: {template_overrides.get('player_character_guidance', template.player_character_guidance or '')}")
    if template_overrides.get('difficulty') is not None or template.difficulty:
        prompt_lines.append(f"- Difficulty: {template_overrides.get('difficulty', template.difficulty or '')}")
    if template_overrides.get('estimated_length') is not None or template.estimated_length:
        prompt_lines.append(f"- Estimated Length: {template_overrides.get('estimated_length', template.estimated_length or '')}")
    # Handle default_rules which is JSON
    default_rules_data = template_overrides.get('default_rules')
    if default_rules_data is None and template.default_rules:
        default_rules_data = template.default_rules
    if default_rules_data:
         prompt_lines.append(f"- Default Rules/Mechanics: {json.dumps(default_rules_data)}")


    # Note: Player Characters are handled in the game creation endpoint, not here in prompt_builder

    if creator_customizations:
        prompt_lines.append("---")
        prompt_lines.append("CREATOR CUSTOMIZATIONS:")
        for key, value in creator_customizations.items():
            if value: # Only include if value is not empty
                prompt_lines.append(f"- {key.replace('_', ' ').title()}: {value}") # Format key nicely
    
    prompt_lines.extend([
        "---",
        "YOUR TASK:",
        "Based primarily on the Template Guidance, Template Overrides, and Creator Customizations (if provided) above, generate a complete campaign structure. Be creative and fill in the details, ensuring the generated components align cohesively with all provided inputs.", # Updated guidance
        "Generate the following components:",
        "1.  **campaign_objective:** A clear, concise overall objective for the players, directly derived from the `core_conflict` and potentially influenced by `template_overrides` and `creator_customizations`.", # Updated guidance
        "2.  **generated_locations:** A JSON list of 3-5 key location objects. These locations should be inspired by the `world_description` and `scene_suggestions` (if provided), fit the `theme` and `desired_tone`, be relevant to the `campaign_objective`, and **incorporate any locations specified in `template_overrides` or `creator_customizations`**. Each object must have 'name' and 'description' keys.", # Added guidance on using template fields and customizations
        "    - Example: `[{\"name\": \"Whispering Caves\", \"description\": \"A dark, damp cave system rumored to hold the artifact.\"}, ...]`",
        "3.  **generated_characters:** A JSON list of 2-3 key non-player character objects relevant to the plot and `campaign_objective`. Their descriptions and roles should align with the `theme` and `desired_tone`, and **incorporate any NPCs specified in `template_overrides` or `creator_customizations`**. Each object must have 'name', 'role', and 'description' keys.", # Added guidance on using template fields and customizations
        "    - Example: `[{\"name\": \"Elara\", \"role\": \"Mysterious Guide\", \"description\": \"An old hermit who knows the mountain paths.\"}, ...]`",
        "4.  **generated_plot_points:** A JSON list of 3-5 major plot point objects. These should outline the key stages or events progressing towards the `campaign_objective`, reflecting the `core_conflict`, considering `player_character_guidance`, and incorporating any plot hooks from `template_overrides` or `creator_customizations`. **Each object MUST have a 'description' (string) key and a 'required' (boolean) key.** The 'required' key indicates if this plot point MUST be completed for the campaign conclusion. Aim for 1-2 required points and several optional ones.",
        "    - Example: `[{\"description\": \"Investigate the initial theft.\", \"required\": true}, {\"description\": \"Track thieves to the Whispering Caves.\", \"required\": true}, {\"description\": \"Find the hidden map in the tavern cellar.\", \"required\": false}, ...]`",
        "5.  **initial_scene:** A JSON object describing the very start of the game. The 'description' should set the scene vividly, incorporating elements from the `theme`, `desired_tone`, and importantly, weaving in references to the provided `player_character_descriptions` (if available) to make the start feel personalized and grounded. The 'state' must include a 'location' key reflecting the starting point. The 'goals' should provide 1-3 immediate, relevant actions for the players based on the scene. **Ensure the initial scene aligns with any relevant `template_overrides` or `creator_customizations` (e.g., starting location).**", # Added guidance on personalization and relevance, and customizations
        "    - Example: `{\"description\": \"Torbin, the gruff warrior, and Lyra, the nimble rogue, awaken in a damp cellar...\", \"state\": {\"location\": \"Tavern Cellar\"}, \"goals\": [\"Look for a way out\", \"Search the barrels\", \"Listen at the door\"]}`", # Updated example
        "6.  **campaign_summary (Optional):** A brief overall summary of the generated campaign, highlighting the main arc.",
        "7.  **conclusion_conditions:** A JSON *list* of condition objects that MUST ALL be met for the campaign to conclude successfully. Each object MUST have a 'type' and relevant parameters. Supported types:",
        "    - `{\"type\": \"state_key_equals\", \"key\": \"<state_data_key>\", \"value\": <expected_value>}` (Checks if a key in state_data equals a specific value)",
        "    - `{\"type\": \"state_key_exists\", \"key\": \"<state_data_key>\"}` (Checks if a key exists in state_data)",
        "    - `{\"type\": \"state_key_contains\", \"key\": \"<state_data_key>\", \"value\": <value_to_contain>}` (Checks if a list/string in state_data contains a value)",
        "    - `{\"type\": \"location_visited\", \"location\": \"<location_name>\"}` (Checks if a specific location name exists in the 'visited_locations' list in state_data)",
        "    - Example: `[{\"type\": \"state_key_equals\", \"key\": \"boss_defeated\", \"value\": true}, {\"type\": \"location_visited\", \"location\": \"Throne Room\"}]`",
        "8.  **possible_branches (Optional):** A JSON object outlining 1-2 potential major narrative branches based on player choices or discoveries.", # Slightly enhanced example
        "9.  **special_rules (Optional):** A JSON object or string outlining any special rules or mechanics for this specific campaign, **incorporating any rules specified in `template_overrides` or `creator_customizations`**.", # Added new component for rules
        "10. **exclusions (Optional):** A JSON list of strings outlining any elements or themes that should be explicitly excluded from the campaign, **incorporating any exclusions specified in `template_overrides` or `creator_customizations`**.", # Added new component for exclusions
        "---",
        "OUTPUT FORMAT:",
        "Provide the entire response as a single, valid JSON object containing the keys corresponding to the numbered items above (e.g., `campaign_objective`, `generated_locations`, `generated_characters`, `generated_plot_points`, `initial_scene`, `special_rules`, `exclusions`, etc.). Ensure all nested values (like lists of locations/characters/plot points and the initial_scene's state/goals) are also valid JSON.",
        "---",
        "Generate the complete campaign structure JSON now:"
    ])

    # Clean up potential None values before joining (though most should be handled by conditional appends)
    clean_prompt_lines = [str(line) for line in prompt_lines if line is not None]
    return "\n".join(clean_prompt_lines)


# Corrected function signature with closing parenthesis
def build_response_prompt(context: str, player_action: str, is_stuck: bool = False, next_required_plot_point: Optional[str] = None) -> str:
    """
    Generates a prompt for the AI to respond to a player's action, given the game context,
    and potentially provides guidance if the player seems stuck.

    Args:
        context: A string containing the relevant game context (campaign info, current state).
        player_action: The action taken by the player as a string.
        is_stuck: Boolean indicating if the player might be stuck.
        next_required_plot_point: Optional string describing the next required plot point.

    Returns:
        A string containing the formatted prompt for the AI.
    """
    prompt_lines = [
        "You are a Game Master for a text-based adventure game.",
        "Based on the provided context and the player's action, describe what happens next.",
        "Consider the following aspects while generating the response:",
        "1. **Narrative Consistency & Logic:** Evaluate the player's action against the current game state (location, inventory, character status, plot points, current objective) and narrative consistency. Provide narrative consequences or deny actions that are illogical (e.g., using an item not possessed, finding something not present, interacting with something impossible). Prioritize realistic outcomes and narrative progression over simply executing the player's command verbatim. **Crucially, evaluate the action against the 'Current Objective/Focus' provided below. If the action attempts to bypass this objective (e.g., trying to achieve the final goal before completing a required intermediate step), your narrative response MUST explain why this is difficult or impossible at this time (e.g., 'The controls are unresponsive, perhaps main power needs stabilizing first?'), unless the context strongly justifies allowing the bypass.**",
        "2. **Narrative Description:** Provide a vivid and engaging description of the outcome, reflecting the consequences of the action based on the evaluation in point 1.",
        "3. **State Changes:** Clearly outline any changes to the game state resulting from the action. If an action is denied or has no effect, state changes might be minimal or empty.",
        "4. **Available Actions:** List the relevant actions the player can take *after* this event, reflecting the new situation.",
    ]

    # Add guidance instruction if player is stuck
    if is_stuck and next_required_plot_point:
        prompt_lines.append(f"5. **Guidance:** The player might be stuck. Subtly weave a hint related to the current objective ('{next_required_plot_point}') into your narrative description or suggest a relevant action.")

    # Ensuring clear separation before extend
    prompt_lines.extend([
        "---",
        "Your response MUST be a JSON object containing three keys:",
        "1. 'content': A string describing the narrative outcome of the action.",
        "2. 'state_changes': A JSON object detailing ALL relevant game state variables after the action. **Crucially, this object MUST ALWAYS include the 'location' key, reflecting the player's current location after this action, even if it hasn't changed from the context.** Other examples: `{'player_health': -10, 'location': 'Cave Entrance', 'items_added': ['torch']}`. **IMPORTANT: If the player's action directly leads to fulfilling a known campaign conclusion condition (e.g., defeating a boss, escaping, finding a key item), ensure the corresponding state key (like `boss_defeated: true`, `escape_successful: true`, `found_artifact: true`) is included and set correctly in this `state_changes` object.** **ACHIEVEMENT: If the player's action directly achieves the Current Objective/Focus provided in the context below, YOU MUST include `achieved_plot_point: \"Description of the achieved plot point\"` in this `state_changes` object.**",
        "3. 'available_actions': A JSON list of strings representing the actions the player can take next from the current state (e.g., `['Look around', 'Check inventory', 'Go north']`). If the game has concluded based on the action, this list might be empty or contain only a final message action.",
        "---",
        "Game Context:",
        context, # Insert the pre-built context string
        f"Current Objective/Focus: {next_required_plot_point or 'Focus on final objective'}", # Inject current objective
        "---",
        f"Player Action: {player_action}",
        "---",
        "Generate the JSON response now:"
    ])

    return "\n".join(prompt_lines)
