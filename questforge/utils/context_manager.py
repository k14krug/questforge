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

    # Access campaign via game relationship
    if not game_state.game:
         return "Error: GameState object does not have a valid 'game' relationship."
    
    campaign = game_state.game.campaign
    if not campaign:
        # This shouldn't happen if data is consistent, but good to check
        return f"Error: Could not find associated campaign for game {game_state.game_id}."

    context_lines = []

    # 1. Campaign Overview & Goals
    context_lines.append("--- Campaign Context ---")
    
    # Ensure campaign_data is treated as a dictionary
    campaign_data_raw = campaign.campaign_data
    campaign_data_dict = {}
    if isinstance(campaign_data_raw, str):
        try:
            campaign_data_dict = json.loads(campaign_data_raw)
        except json.JSONDecodeError:
            # Log error or handle case where string is not valid JSON
            campaign_data_dict = {} # Default to empty dict on error
    elif isinstance(campaign_data_raw, dict):
        campaign_data_dict = campaign_data_raw
    else:
         campaign_data_dict = {} # Default if it's None or unexpected type

    summary = campaign_data_dict.get('campaign_summary', 'No overall summary available.') # Use campaign_summary if available
    context_lines.append(f"Campaign Summary: {summary}")

    # Format objectives clearly
    if campaign.objectives:
        context_lines.append("Overall Objective(s):")
        # Assuming objectives is a list of strings or simple dicts
        if isinstance(campaign.objectives, list):
            for obj in campaign.objectives:
                context_lines.append(f"- {str(obj)}") # Convert to string just in case
        else: # Handle case where it might be a single string/dict
             context_lines.append(f"- {str(campaign.objectives)}")
    else:
        context_lines.append("Overall Objective(s): None defined.")

    # Include AI-generated Key Elements from Campaign
    if campaign.key_locations:
        context_lines.append("Key Locations:")
        for loc in campaign.key_locations:
             context_lines.append(f"- {loc.get('name', 'Unknown Location')}: {loc.get('description', 'No description')}")
    if campaign.key_characters:
        context_lines.append("Key Characters:")
        for char in campaign.key_characters:
             context_lines.append(f"- {char.get('name', 'Unknown Character')} ({char.get('role', 'Unknown Role')}): {char.get('description', 'No description')}")
    if campaign.major_plot_points:
        context_lines.append("Major Plot Points:")
        for i, plot in enumerate(campaign.major_plot_points):
             context_lines.append(f"- Stage {i+1}: {str(plot)}") # Assuming plot points are strings

    # 2. Current Game State & Progress
    context_lines.append("\n--- Current Game State ---")
    current_state_dict = game_state.state_data or {}
    context_lines.append(f"Current Location: {current_state_dict.get('location', 'Unknown')}") # Get location from state_data
    if current_state_dict:
        context_lines.append("Other State Details:")
        for key, value in current_state_dict.items():
            if key != 'location': # Avoid duplicating location if it exists
                context_lines.append(f"- {key.replace('_', ' ').title()}: {json.dumps(value)}") # Use json.dumps for complex values
    else:
         context_lines.append("Other State Details: None available.")

    # Include Progress Markers
    if game_state.completed_objectives:
         context_lines.append(f"Completed Objectives: {json.dumps(game_state.completed_objectives)}")
    if game_state.discovered_locations:
         context_lines.append(f"Discovered Locations: {json.dumps(game_state.discovered_locations)}")
    if game_state.encountered_characters:
         context_lines.append(f"Encountered Characters: {json.dumps(game_state.encountered_characters)}")
    if game_state.completed_plot_points:
         context_lines.append(f"Completed Plot Points: {json.dumps(game_state.completed_plot_points)}")


    # 3. Recent History (Game Log)
    context_lines.append("\n--- Recent Events (Game Log) ---")
    # Use game_state.game_log for recent history
    if game_state.game_log:
        # Show last few log entries (e.g., last 5)
        num_log_entries = 5 
        recent_log = game_state.game_log[-num_log_entries:]
        for entry in recent_log:
             # Ensure entry is a string before appending
             context_lines.append(f"- {str(entry)}") 
    else:
        context_lines.append("No recent events available.")

    context_lines.append("\n--- End Context ---")

    return "\n".join(context_lines)
