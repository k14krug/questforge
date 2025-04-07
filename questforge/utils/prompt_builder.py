from questforge.models.template import Template
from questforge.models.game_state import GameState # Import GameState for build_response_prompt later

def build_campaign_prompt(template: Template, user_inputs: dict) -> str:
    """
    Generates a detailed prompt for the AI to create the initial campaign structure
    based on a template and user answers to setup questions.

    Args:
        template: The Template object containing the game blueprint.
        user_inputs: A dictionary where keys are question texts (or identifiers)
                     and values are the user's answers.

    Returns:
        A string containing the formatted prompt for the AI.
    """
    # Basic prompt structure - can be significantly enhanced
    prompt_lines = [
        "You are a creative Game Master designing the beginning of a text-based adventure game.",
"Your goal is to create an engaging and immersive experience for the player.",
"Consider the following aspects while generating the campaign:",
"1. Setting: Describe the environment and atmosphere.",
"2. Characters: Introduce key characters with distinct personalities.",
"3. Plot: Outline the main storyline and conflicts.",
        f"The game is based on the '{template.name}' template.",
        f"Template Description: {template.description}",
        "---",
        "Template Rules/Setting:",
        template.default_rules if template.default_rules else "No specific rules provided.",
        "---",
        "User Customization:",
        "The player answered the following setup questions:",
    ]

    # Add user inputs to the prompt
    if user_inputs:
        for question, answer in user_inputs.items():
            prompt_lines.append(f"- {question}: {answer}")
    else:
        prompt_lines.append("No specific user customizations provided.")

    prompt_lines.extend([
        "---",
"Your Task:",
"Based on the template description, rules, and user customization, generate the following:",
"1.  **Initial Description:** A compelling opening paragraph setting the scene for the player.",
"    - Example: 'You find yourself in a dimly lit tavern, the smell of ale and smoke filling the air. The bartender eyes you suspiciously as you take a seat.'",
"2.  **Initial State:** A JSON object representing the starting game state (e.g., `{'location': 'tavern', 'health': 100, 'inventory': ['map']}`). Include relevant starting attributes.",
"    - Example: {\"location\": \"tavern\", \"health\": 100, \"inventory\": [\"map\"]}",
"3.  **Goals:** A short list (1-3 items) of initial objectives or goals for the player.",
"    - Example: ['Find the hidden map', 'Talk to the bartender', 'Leave the tavern']",
"4.  **Key NPCs (Optional):** A list of 1-2 important non-player characters the player might encounter early on, with brief descriptions.",
"    - Example: [{\"name\": \"Bartender\", \"description\": \"A gruff man with a scar over his left eye.\"}]",
        "---",
        "Output Format:",
        "Please provide the response as a JSON object with the keys: 'initial_description', 'initial_state', 'goals', 'key_npcs'. Ensure the 'initial_state' value is also a valid JSON object.",
        "---",
        "Example 'initial_state': {\"location\": \"Dark Forest Entrance\", \"time_of_day\": \" Dusk\", \"player_mood\": \"Anxious\"}",
        "---",
        "Generate the campaign details now:"
    ])

    return "\n".join(prompt_lines)


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
        "Your response MUST be a JSON object containing two keys:",
        "1. 'content': A string describing the narrative outcome of the action.",
        "2. 'state_changes': A JSON object detailing the changes to the game state as key-value pairs (e.g., `{'player_health': -10, 'location': 'Cave Entrance', 'items_added': ['torch']}`). Only include keys for state variables that actually change.",
        "---",
        "Game Context:",
        context, # Insert the pre-built context string
        "---",
        f"Player Action: {player_action}",
        "---",
        "Generate the JSON response now:",
"Ensure the response is consistent with the provided context and player action."
    ]

    return "\n".join(prompt_lines)
