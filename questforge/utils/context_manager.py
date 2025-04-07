import json
from questforge.models.game_state import GameState

def build_context(game_state: GameState) -> str:
    """
    Builds a context string for the AI based on the current game state and
    associated campaign information.

    Args:
        game_state: The current GameState object.

    Returns:
        A string containing formatted context information for the AI prompt.
        Returns an error message string if essential data is missing.
    """
    if not game_state:
        return "Error: Invalid game state provided."

    campaign = game_state.campaign
    if not campaign:
        # This shouldn't happen if data is consistent, but good to check
        return "Error: Could not find associated campaign for the game state."

    context_lines = []

    # 1. Campaign Overview
    context_lines.append("--- Campaign Context ---")
    # Assuming campaign_data stores the initial description
    description = campaign.campaign_data.get('description', 'No overall description available.')
    context_lines.append(f"Overall Description: {description}")
    if campaign.objectives:
        objectives_str = ", ".join(map(str, campaign.objectives)) # Handle non-string objectives
        context_lines.append(f"Current Objectives: {objectives_str}")
    else:
        context_lines.append("Current Objectives: None defined.")

    # 2. Current Game State
    context_lines.append("\n--- Current Game State ---")
    if game_state.state_data and isinstance(game_state.state_data, dict):
        # Format the state dictionary nicely
        for key, value in game_state.state_data.items():
            # Simple formatting, could be enhanced (e.g., handling lists better)
            context_lines.append(f"- {key.replace('_', ' ').title()}: {json.dumps(value)}")
    else:
        context_lines.append("No detailed state data available.")

    # 3. Recent History
    context_lines.append("\n--- Recent Events ---")
    # Assuming game_state.recent_events stores the last N events/actions
    if hasattr(game_state, 'recent_events') and game_state.recent_events:
        for event in game_state.recent_events:
            context_lines.append(f"- {event}")
    else:
        context_lines.append("No recent events available.")

    context_lines.append("\n--- End Context ---")

    return "\n".join(context_lines)
