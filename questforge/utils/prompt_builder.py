import json # Import the json module
from questforge.models.template import Template
from questforge.models.game_state import GameState # Import GameState for build_response_prompt later
from typing import Dict # Import Dict for type hinting

def build_campaign_prompt(template: Template, player_descriptions: Dict[str, str]) -> str:
    """
    Generates a detailed prompt for the AI to create the full campaign structure
    based on a high-level template and player character descriptions.

    Args:
        template: The Template object containing the high-level guidance.
        player_descriptions: A dictionary mapping user_id (str) to character description (str).

    Returns:
        A string containing the formatted prompt for the AI.
    """
    prompt_lines = [
        "You are a creative and detailed Game Master designing a text-based adventure game campaign.",
        "Your goal is to generate a complete campaign structure based on the provided template guidance and the participating players.",
        "---",
        "TEMPLATE GUIDANCE:",
        f"- Name: {template.name}",
        f"- Genre: {template.genre}",
        f"- Core Conflict/Goal: {template.core_conflict}",
    ]
    # Add optional fields if they exist
    if template.description:
        prompt_lines.append(f"- Description: {template.description}")
    if template.theme:
        prompt_lines.append(f"- Theme: {template.theme}")
    if template.desired_tone:
        prompt_lines.append(f"- Desired Tone: {template.desired_tone}")
    if template.world_description:
        prompt_lines.append(f"- World Description: {template.world_description}")
    if template.scene_suggestions:
        prompt_lines.append(f"- Scene Suggestions: {template.scene_suggestions}")
    if template.player_character_guidance:
        prompt_lines.append(f"- Player Character Guidance: {template.player_character_guidance}")
    if template.difficulty:
        prompt_lines.append(f"- Difficulty: {template.difficulty}")
    if template.estimated_length:
        prompt_lines.append(f"- Estimated Length: {template.estimated_length}")

    prompt_lines.append("---")
    prompt_lines.append("PLAYER CHARACTERS:")
    if player_descriptions:
        for user_id, desc in player_descriptions.items():
            prompt_lines.append(f"- Player (ID {user_id}): {desc}")
    else:
        prompt_lines.append("No player character descriptions provided (assume generic adventurers).")

    prompt_lines.extend([
        "---",
        "YOUR TASK:",
        "Based *only* on the Template Guidance and Player Characters above, generate a complete campaign structure. Be creative and fill in the details!",
        "Generate the following components:",
        "1.  **campaign_objective:** A clear, concise overall objective for the players, derived from the Core Conflict.",
        "2.  **generated_locations:** A JSON list of 3-5 key location objects relevant to the campaign objective and theme. Each object should have 'name' and 'description' keys.",
        "    - Example: `[{\"name\": \"Whispering Caves\", \"description\": \"A dark, damp cave system rumored to hold the artifact.\"}, ...]`",
        "3.  **generated_characters:** A JSON list of 2-3 key non-player character objects relevant to the plot. Each object should have 'name', 'role', and 'description' keys.",
        "    - Example: `[{\"name\": \"Elara\", \"role\": \"Mysterious Guide\", \"description\": \"An old hermit who knows the mountain paths.\"}, ...]`",
        "4.  **generated_plot_points:** A JSON list outlining 3-5 major stages or events in the campaign related to the core conflict. Each item should be a descriptive string.",
        "    - Example: `[\"Players investigate the initial theft.\", \"Players track the thieves to the Whispering Caves.\", \"Players confront the guardian within the caves.\", ...]`",
        "5.  **initial_scene:** A JSON object describing the very start of the game, including:",
        "    - 'description': (String) A compelling opening paragraph setting the scene for the players.",
        "    - 'state': (JSON Object) The starting game state dictionary (e.g., `{\"location\": \"Tavern Cellar\", \"party_mood\": \"Suspicious\"}`). Must include 'location'.",
        "    - 'goals': (JSON List) 1-3 immediate goals or available actions for the players.",
        "    - Example: `{\"description\": \"You awaken in a damp cellar...\", \"state\": {\"location\": \"Tavern Cellar\"}, \"goals\": [\"Look for a way out\", \"Search the barrels\"]}`",
        "6.  **campaign_summary (Optional):** A brief overall summary of the generated campaign.",
        "7.  **conclusion_conditions (Optional):** A JSON object describing conditions for campaign conclusion (e.g. `{\"objective_met\": \"Defeat the Dragon\"}`).",
        "8.  **possible_branches (Optional):** A JSON object outlining potential major narrative branches.",
        "---",
        "OUTPUT FORMAT:",
        "Provide the entire response as a single, valid JSON object containing the keys corresponding to the numbered items above (e.g., `campaign_objective`, `generated_locations`, `generated_characters`, `generated_plot_points`, `initial_scene`, etc.). Ensure all nested values (like lists of locations/characters/plot points and the initial_scene's state/goals) are also valid JSON.",
        "---",
        "Generate the complete campaign structure JSON now:"
    ])

    # Clean up potential None values before joining (though most should be handled by conditional appends)
    clean_prompt_lines = [str(line) for line in prompt_lines if line is not None]
    return "\n".join(clean_prompt_lines)


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
        "Consider the following aspects while generating the response:",
        "1. Narrative: Provide a vivid and engaging description of the outcome.",
        "2. State Changes: Clearly outline any changes to the game state.",
        "3. Available Actions: List the relevant actions the player can take *after* this event.",
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
