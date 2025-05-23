import json
from questforge.models.game_state import GameState
from questforge.models.game import GamePlayer # Import GamePlayer
from questforge.models.user import User # Import User
from sqlalchemy.orm import joinedload # Import joinedload
from typing import Optional # Import Optional for type hinting

def build_context(game_state: GameState, next_required_plot_point: Optional[str] = None) -> str:
    """
    Builds a context string for the AI based on the current game state and
    associated campaign information.

    Args:
        game_state: The current GameState object.
        next_required_plot_point: Optional string describing the next required plot point.

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
        context_lines.append("Major Plot Points (Format: {\"id\": \"...\", \"description\": \"...\", \"required\": ...}):")
        # Ensure major_plot_points is a list of dicts
        if isinstance(campaign.major_plot_points, list):
            for plot_point in campaign.major_plot_points:
                if isinstance(plot_point, dict):
                    # Construct a string representation of the plot point dictionary
                    # This ensures the AI sees the structure including the ID.
                    plot_point_str = json.dumps(plot_point) 
                    context_lines.append(f"- {plot_point_str}")
                else:
                    context_lines.append(f"- Invalid plot point format: {str(plot_point)}")
        else:
            context_lines.append("- No plot points available or in unexpected format.")

    if campaign.conclusion_conditions:
        context_lines.append("Conclusion Conditions (all must be met):")
        if isinstance(campaign.conclusion_conditions, list):
            for cond in campaign.conclusion_conditions:
                context_lines.append(f"- {json.dumps(cond)}")
        elif isinstance(campaign.conclusion_conditions, dict): # Should be a list, but handle if it's a single dict
            context_lines.append(f"- {json.dumps(campaign.conclusion_conditions)}")
        else:
            context_lines.append(f"- {str(campaign.conclusion_conditions)}") # Fallback for other types
    else:
        context_lines.append("Conclusion Conditions: None specifically defined beyond completing required plot points.")


    # 2. Current Game State & Progress
    context_lines.append("\n--- Current Game State ---")
    current_state_dict = game_state.state_data or {}
    context_lines.append(f"Current Location: {current_state_dict.get('location', 'Unknown')}") # Get location from state_data

    # --- Add Players Present Section ---
    context_lines.append("\n--- Players Present ---")
    # Eager load user relationship for username fallback
    player_associations = GamePlayer.query.options(joinedload(GamePlayer.user)).filter_by(game_id=game_state.game_id).all()
    if player_associations:
        for assoc in player_associations:
            player_name = assoc.character_name if assoc.character_name else assoc.user.username # Use name, fallback to username
            description = assoc.character_description or "(No description provided)"
            context_lines.append(f"- {player_name}: {description}")
    else:
        context_lines.append("No player information available.")
    # --- End Players Present Section ---

    context_lines.append("\n--- Other State Details ---") # Renamed section header slightly
    if current_state_dict:
        # context_lines.append("Other State Details:") # Removed redundant header
        has_other_details = False
        for key, value in current_state_dict.items():
            if key != 'location': # Avoid duplicating location
                context_lines.append(f"- {key.replace('_', ' ').title()}: {json.dumps(value)}") # Use json.dumps for complex values
                has_other_details = True
        if not has_other_details:
             context_lines.append("(No other specific state details)") # Message if only location was present
    else:
         context_lines.append("(No state details available)") # Changed message

    # Include Progress Markers
    if game_state.completed_objectives:
         context_lines.append(f"Completed Objectives: {json.dumps(game_state.completed_objectives)}")
    if game_state.discovered_locations:
         context_lines.append(f"Discovered Locations: {json.dumps(game_state.discovered_locations)}")
    if game_state.encountered_characters:
         context_lines.append(f"Encountered Characters: {json.dumps(game_state.encountered_characters)}")
    if game_state.completed_plot_points:
         context_lines.append(f"Completed Plot Points: {json.dumps(game_state.completed_plot_points)}")

    # X. Historical Summary (New Section)
    # current_state_dict is game_state.state_data
    historical_summary = current_state_dict.get('historical_summary')
    if historical_summary and isinstance(historical_summary, list) and len(historical_summary) > 0:
        context_lines.append("\n--- Game History Summary ---") # Renamed section header as per plan
        for i, summary_entry in enumerate(historical_summary):
            context_lines.append(f"{i+1}. {str(summary_entry)}") # Numbered list
        # No explicit "---" end marker here, as the next section will start with its own "---"
    # else: No historical summary or it's empty, so we add nothing.

    # Section for Recent Game Log has been removed as per plan Task 4.1

    # 4. Current Objective/Focus
    context_lines.append("\n--- Current Objective/Focus ---")
    if next_required_plot_point:
        context_lines.append(f"Next Objective: {next_required_plot_point}")
    elif campaign.objectives: # Fallback to overall campaign objective if no specific next plot point
        # Assuming campaign.objectives is a list, take the first one as a general guide
        # Or if it's a string, use it directly
        overall_obj_display = ""
        if isinstance(campaign.objectives, list) and campaign.objectives:
            overall_obj_display = str(campaign.objectives[0])
        elif isinstance(campaign.objectives, str):
            overall_obj_display = campaign.objectives
        
        if overall_obj_display:
            context_lines.append(f"Focus on the overall campaign objective: {overall_obj_display}")
        else:
            context_lines.append("Focus on exploring and interacting with the world.")
            
    else: # If no next required plot point and no campaign objectives
        context_lines.append("Focus on exploring and interacting with the world.")


    context_lines.append("\n--- End Context ---")

    return "\n".join(context_lines)
