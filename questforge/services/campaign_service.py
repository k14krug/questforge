import logging
import json # Import the json module
from flask import current_app
from questforge.models.game import Game
from questforge.models.campaign import Campaign
from questforge.models.template import Template
from questforge.models.game_state import GameState
from questforge.models.api_usage_log import ApiUsageLog # Import the new model
from questforge.extensions import db
from questforge.services.ai_service import ai_service # Import the singleton instance
from typing import Dict, List, Optional, Tuple # Import typing helpers
from decimal import Decimal # For accurate cost calculation

# --- Commenting out the old create_campaign function ---
# def create_campaign(game_id: int, template_id: int, user_inputs: dict):
#     """
#     Creates a new campaign structure and initial game state for a given game,
#     using a template and user inputs processed by the AI service.
#     (DEPRECATED in favor of generate_campaign_structure)
#     """
#     logger = current_app.logger
#     try:
#         logger.info('Starting campaign creation process')
#         logger.debug(f'Input parameters - game_id: {game_id}, template_id: {template_id}')
#         # ... (rest of old implementation) ...
#         return None


def generate_campaign_structure(game: Game, template: Template, player_descriptions: Dict[str, str], creator_customizations: Optional[Dict] = None) -> bool:
    """
    Generates the full campaign structure and initial game state using the AI service,
    triggered after players are ready in the lobby.

    Args:
        game: The Game object.
        template: The Template object being used.
        player_descriptions: A dictionary mapping user_id (str) to character description (str).
        creator_customizations: An optional dictionary containing creator-provided customizations.

    Returns:
        True if campaign and initial state were successfully generated and saved, False otherwise.
    using a template and user inputs processed by the AI service.

    """
    logger = current_app.logger
    game_id = game.id # Get game_id from the game object
    try:
        logger.info(f"Starting campaign structure generation for game {game_id}")

        # 1. Generate campaign data using AI service
        # Note: ai_service.generate_campaign will need updating in Phase 3
        # to accept player_descriptions and use the revised prompt builder.
        # For now, we pass player_descriptions, assuming the service/prompt handles it.
        logger.info(f"Requesting campaign generation for game {game_id} using template {template.id}")
        # Update call to handle new return signature: (parsed_data, model_used, usage_data)
        ai_result = ai_service.generate_campaign(template, player_descriptions, creator_customizations) # Pass descriptions and customizations

        if not ai_result:
            logger.error(f"AI service failed to generate campaign data for game {game_id}")
            return False
            
        # Unpack the result
        ai_response_data, model_used, usage_data = ai_result

        logger.info(f"Received campaign data from AI ({model_used}) for game {game_id}")
        # logger.debug(f"AI Response Data: {ai_response_data}") # Optional detailed logging

        # Log API Usage
        if usage_data:
            try:
                logger.info(f"Attempting to log usage for model: '{model_used}'") 
                
                # Revised Pricing Lookup Logic
                pricing_config = current_app.config.get('OPENAI_PRICING', {})
                pricing_info = None
                matched_key = None

                # 1. Try exact match first
                if model_used in pricing_config:
                    pricing_info = pricing_config[model_used]
                    matched_key = model_used
                    logger.info(f"Found exact pricing key '{matched_key}' for model '{model_used}'")
                else:
                    # 2. Iteratively remove suffix components
                    model_parts = model_used.split('-')
                    for i in range(len(model_parts) - 1, 0, -1):
                        potential_key = '-'.join(model_parts[:i])
                        if potential_key in pricing_config:
                            pricing_info = pricing_config[potential_key]
                            matched_key = potential_key
                            logger.info(f"Found partial pricing key '{matched_key}' for model '{model_used}'")
                            break # Use the first partial match found

                cost = None
                prompt_tokens = usage_data.prompt_tokens
                completion_tokens = usage_data.completion_tokens
                total_tokens = usage_data.total_tokens

                if pricing_info:
                    prompt_cost = (Decimal(prompt_tokens) / 1000) * Decimal(pricing_info['prompt'])
                    completion_cost = (Decimal(completion_tokens) / 1000) * Decimal(pricing_info['completion'])
                    cost = prompt_cost + completion_cost
                    logger.info(f"Calculated cost for game {game_id} API call: ${cost:.6f}")
                else:
                    logger.warning(f"No pricing info found for model '{model_used}'. Cost will be null.")

                usage_log = ApiUsageLog(
                    game_id=game_id,
                    model_name=model_used,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost=cost
                )
                db.session.add(usage_log)
                # Don't commit yet, part of the larger transaction
                logger.info(f"Created ApiUsageLog entry for game {game_id} (Initial Campaign Gen)")
            except Exception as log_e:
                logger.error(f"Failed to create ApiUsageLog entry for game {game_id}: {log_e}", exc_info=True)
                # Decide if this should prevent campaign creation (maybe not?)
        else:
            logger.warning(f"No usage data returned from AI service for game {game_id} campaign generation.")


        # 2. Validate AI response (using placeholder validation for now)
        # TODO: Update template.validate_ai_response in Phase 3 for the new structure
        # Use ai_response_data now
        if not template.validate_ai_response(ai_response_data):
            logger.error(f"AI response failed validation for game {game_id}. Check model validation logs.")
            return False
        logger.info(f"AI Response structure validation passed (using placeholder validation) for game {game_id}.")

        # 3. Create and save Campaign structure
        logger.info(f"Mapping AI response to Campaign model for game {game_id}")
        # Map AI response to Campaign model fields based on the *expected* new structure
        # Use ai_response_data now
        new_campaign = Campaign(
            game_id=game_id,
            template_id=template.id, # Store template ID for reference
            campaign_data=ai_response_data.get('campaign_summary', {}), # Or a more structured summary
            objectives=ai_response_data.get('campaign_objective', []),
            key_locations=ai_response_data.get('generated_locations', []),
            key_characters=ai_response_data.get('generated_characters', []),
            major_plot_points=ai_response_data.get('generated_plot_points', []),
            conclusion_conditions=ai_response_data.get('conclusion_conditions', {}),
            possible_branches=ai_response_data.get('possible_branches', {}) # If AI generates branches
        )
        db.session.add(new_campaign)
        db.session.flush() # Flush to get the new_campaign.id for GameState
        logger.info(f"Created Campaign object (ID: {new_campaign.id}) for game {game_id}")

        # 4. Create initial GameState
        # Use ai_response_data now
        initial_scene_data = ai_response_data.get('initial_scene', {}) # Expecting a dict like {'description': '...', 'state': {...}, 'goals': [...]}
        initial_state_dict = initial_scene_data.get('state', {})
        initial_narrative = initial_scene_data.get('description', 'The adventure begins...')
        initial_actions = initial_scene_data.get('goals', []) # Use initial goals as first actions

        if not initial_state_dict or not isinstance(initial_state_dict, dict):
             logger.error(f"Invalid or missing 'initial_scene.state' in AI response for game {game_id}")
             db.session.rollback() # Rollback campaign creation
             return False

        initial_game_state = GameState(
            game_id=game_id,
            state_data=initial_state_dict
        )
        # Set attributes *after* object creation
        initial_game_state.campaign_id = new_campaign.id
        initial_game_state.current_location = initial_state_dict.get('location')

        # --- Format and add conclusion conditions to initial log ---
        conditions_text = "INFO: To conclude this adventure, the following conditions must be met:"
        if new_campaign.conclusion_conditions and isinstance(new_campaign.conclusion_conditions, list):
            for condition in new_campaign.conclusion_conditions:
                if isinstance(condition, dict):
                    cond_type = condition.get('type')
                    if cond_type == 'state_key_equals':
                        conditions_text += f"\n- State key '{condition.get('key', 'N/A')}' must equal '{condition.get('value', 'N/A')}'"
                    elif cond_type == 'state_key_exists':
                        conditions_text += f"\n- State key '{condition.get('key', 'N/A')}' must exist"
                    elif cond_type == 'state_key_contains':
                        conditions_text += f"\n- State key '{condition.get('key', 'N/A')}' must contain '{condition.get('value', 'N/A')}'"
                    elif cond_type == 'location_visited':
                        conditions_text += f"\n- Location '{condition.get('location', 'N/A')}' must be visited"
                    else:
                        conditions_text += f"\n- Unknown condition type: {json.dumps(condition)}"
                else:
                    conditions_text += f"\n- Malformed condition: {condition}"
        else:
            conditions_text += "\n- No specific conclusion conditions defined."
        
        # Combine conditions text with the initial narrative
        combined_initial_log = [conditions_text, initial_narrative]
        initial_game_state.game_log = combined_initial_log
        # --- End conclusion conditions formatting ---

        initial_game_state.available_actions = initial_actions
        db.session.add(initial_game_state)
        logger.info(f"Created initial GameState object for game {game_id}")

        # 5. Commit transaction
        db.session.commit()
        logger.info(f"Successfully created campaign and initial state for game {game_id} in DB.")

        # 6. Initialize state in GameStateService memory
        # Import the service instance here to avoid circular import at top level
        from .game_state_service import game_state_service
        game_state_service.join_game(game_id, 'system') # Ensure game entry exists
        # Ensure the initial state includes turns_since_plot_progress
        if 'turns_since_plot_progress' not in initial_state_dict:
            initial_state_dict['turns_since_plot_progress'] = 0
        game_state_service.active_games[game_id]['state'] = initial_state_dict
        game_state_service.active_games[game_id]['log'] = combined_initial_log # Use the combined log
        game_state_service.active_games[game_id]['actions'] = initial_actions
        game_state_service.active_games[game_id]['version'] = 1 # Initial version
        logger.info(f"Initialized game state in memory for game {game_id}")

        return True

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during campaign structure generation for game {game_id}: {str(e)}", exc_info=True)
        return False

def update_campaign_state(game_state: GameState, player_action: str):
    """
    Updates the campaign state based on the player's action and the AI's response.

    Args:
        game_state: The current GameState object.
        player_action: The action taken by the player (string).

    Returns:
        True if the state was updated successfully, False otherwise.
    """
    logger = current_app.logger
    try:
        logger.info(f"Updating campaign state for game {game_state.game_id}, campaign {game_state.campaign_id}")

        # 1. Get AI response
        ai_response = ai_service.get_response(game_state, player_action)
        if not ai_response:
            logger.error(f"AI service failed to generate response for game {game_state.game_id}")
            return False

        logger.debug(f"AI Response Data: {ai_response}")

        # 2. Update GameState
        state_changes = ai_response.get('state_changes')
        if state_changes:
            logger.info("Applying state changes from AI response")
            game_state.state_data.update(state_changes)
            db.session.add(game_state)
        else:
            logger.info("No state changes in AI response")

        # 3. Update current location
        new_location = ai_response.get('new_location')
        if new_location:
            logger.info(f"Updating current location to {new_location}")
            game_state.current_location = new_location

        # 4. Commit transaction
        db.session.commit()
        logger.info(f"Successfully updated campaign state for game {game_state.game_id}")
        return True

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during campaign state update for game {game_state.game_id}: {str(e)}", exc_info=True) # Corrected log message
        return False

# Updated function signature
def check_conclusion(game_id: int, campaign_conditions: List[Dict], major_plot_points: List[Dict], current_state_data: Dict, completed_plot_points: List[str]) -> bool:
    """
    Checks if the game has reached a conclusion based on required plot points
    and specific conclusion conditions being met in the current state data.

    Args:
        game_id: The ID of the game (for logging).
        campaign_conditions: A list of conclusion condition dictionaries from the Campaign.
        major_plot_points: The list of plot point objects (with 'description' and 'required' keys).
        current_state_data: The current state data dictionary to check against.
        completed_plot_points: A list of descriptions of the plot points already completed.


    Returns:
        True if the game has concluded, False otherwise.
    """
    logger = current_app.logger
    try:
        logger.info(f"Checking conclusion for game {game_id}")
        state_data = current_state_data or {} # Ensure state_data is a dict
        completed_plots_set = set(completed_plot_points or []) # Use a set for efficient lookup

        # --- Pre-Check 1: Check if all REQUIRED plot points are completed ---
        if isinstance(major_plot_points, list):
            for plot_point in major_plot_points:
                if isinstance(plot_point, dict) and plot_point.get('required') is True:
                    description = plot_point.get('description')
                    if not description:
                        logger.warning(f"Game {game_id}: Found required plot point with no description: {plot_point}. Cannot check completion.")
                        return False # Treat malformed required plot point as failure
                    if description not in completed_plots_set:
                        logger.info(f"Game {game_id}: Conclusion check failed: Required plot point not completed: '{description}'")
                        return False # A required plot point is not yet completed
            logger.debug(f"Game {game_id}: All required plot points completed.")
        else:
            logger.warning(f"Game {game_id}: Major plot points data is not a list: {major_plot_points}. Cannot check required points.")
            # Decide if this should prevent conclusion - likely yes if plot points are expected
            return False

        # --- Pre-Check 2: Check if ANY conclusion conditions are defined ---
        # If all required plot points are done, but no specific conditions exist,
        # the game might conclude based on plot points alone.
        # However, the original logic implies conditions are needed if present.
        if not campaign_conditions:
            logger.info(f"Game {game_id}: All required plot points completed, and no specific conclusion conditions defined. Concluding.")
            # If reaching this point means all required plot points are done,
            # and there are no other conditions, the game concludes.
            # However, let's stick to the original flow: if conditions *are* defined, they *must* be met.
            # If no conditions are defined, maybe it shouldn't conclude automatically?
            # For now, let's assume if conditions list is empty/invalid, we proceed as if they are met (vacuously true).
            # Revisit this logic if needed. Let's log a warning if conditions are missing but required plots are done.
            logger.warning(f"Game {game_id}: All required plot points met, but no specific conclusion_conditions defined in campaign. Proceeding as if conditions met.")
            # return True # Uncomment this if completing all required plot points is sufficient when no conditions exist

        # --- Check Specific Conclusion Conditions (Only if defined) ---
        if not isinstance(campaign_conditions, list):
            logger.warning(f"Conclusion conditions for game {game_id} are not a list: {campaign_conditions}. Treating as met (vacuously true).")
            # If conditions are malformed, maybe treat as met? Or fail? Let's treat as met for now.
            all_conditions_met = True
        elif not campaign_conditions: # Empty list
             logger.debug(f"Game {game_id}: No specific conclusion conditions to check.")
             all_conditions_met = True # No conditions means they are all met
        else:
            # Conditions list exists and is not empty, evaluate them
            all_conditions_met = True # Assume true until a condition fails
            logger.debug(f"Evaluating conclusion conditions for game {game_id} against state_data: {json.dumps(state_data)}") # Log the state being checked

            for i, condition in enumerate(campaign_conditions): # Add index for logging
                logger.debug(f"Game {game_id}: Checking condition #{i+1}: {condition}") # Log the condition being checked
                if not isinstance(condition, dict):
                    logger.warning(f"Game {game_id}: Skipping invalid condition #{i+1} (not a dict): {condition}")
                    all_conditions_met = False
                    break # If one condition is invalid, we can't be sure, so fail the check

                condition_type = condition.get('type')
                condition_met = False # Assume false for this specific condition

                try:
                    if condition_type == 'state_key_equals':
                        key = condition.get('key')
                        expected_value = condition.get('value')
                        actual_value = state_data.get(key) # Get actual value once
                        if key is not None:
                            # Special handling for boolean comparison if expected value is bool
                            if isinstance(expected_value, bool):
                                condition_met = str(actual_value).lower() == str(expected_value).lower()
                            else:
                                condition_met = actual_value == expected_value
                            logger.debug(f"  Game {game_id}: Condition #{i+1} [state_key_equals]: key='{key}', expected='{expected_value}' (type: {type(expected_value)}), actual='{actual_value}' (type: {type(actual_value)}), met={condition_met}")
                        else:
                            logger.warning(f"  Game {game_id}: Condition #{i+1} [state_key_equals]: Invalid (missing key): {condition}")

                    elif condition_type == 'state_key_exists':
                        key = condition.get('key')
                        if key is not None:
                            condition_met = key in state_data
                            logger.debug(f"  Game {game_id}: Condition #{i+1} [state_key_exists]: key='{key}', exists={condition_met}")
                        else:
                            logger.warning(f"  Game {game_id}: Condition #{i+1} [state_key_exists]: Invalid (missing key): {condition}")

                    elif condition_type == 'state_key_contains':
                        key = condition.get('key')
                        value_to_contain = condition.get('value')
                        actual_value = state_data.get(key) # Get actual value once
                        if key is not None and value_to_contain is not None:
                            # Convert expected value to string for robust comparison
                            value_to_contain_str = str(value_to_contain)
                            if isinstance(actual_value, list):
                                # Check if any item in the list *equals* the value_to_contain_str
                                condition_met = any(str(item) == value_to_contain_str for item in actual_value)
                            elif isinstance(actual_value, str):
                                # Check if the string *contains* the value_to_contain_str
                                condition_met = value_to_contain_str in actual_value
                            else: # Handle other types like bool or int stored in state
                                condition_met = value_to_contain_str == str(actual_value)

                            logger.debug(f"  Game {game_id}: Condition #{i+1} [state_key_contains]: key='{key}', expected_to_contain='{value_to_contain_str}', actual='{actual_value}', met={condition_met}")
                        else:
                            logger.warning(f"  Game {game_id}: Condition #{i+1} [state_key_contains]: Invalid (missing key or value): {condition}")

                    elif condition_type == 'location_visited':
                        location_name = condition.get('location')
                        # Ensure 'visited_locations' exists and is a list in state_data
                        visited_locations = state_data.get('visited_locations')
                        if location_name is not None and isinstance(visited_locations, list):
                            condition_met = location_name in visited_locations
                            logger.debug(f"  Game {game_id}: Condition #{i+1} [location_visited]: location='{location_name}', visited={visited_locations}, met={condition_met}")
                        elif not isinstance(visited_locations, list):
                             logger.warning(f"  Game {game_id}: Condition #{i+1} [location_visited]: Invalid - 'visited_locations' in state_data is not a list or missing. Value: {visited_locations}")
                             condition_met = False # Explicitly set to false
                        else: # location_name is None
                            logger.warning(f"  Game {game_id}: Condition #{i+1} [location_visited]: Invalid (missing location): {condition}")

                    else:
                        logger.warning(f"  Game {game_id}: Condition #{i+1}: Unsupported type: {condition_type}")

                except Exception as eval_e:
                     logger.error(f"  Game {game_id}: Condition #{i+1}: Error evaluating condition {condition}: {eval_e}", exc_info=True)
                     condition_met = False # Treat evaluation errors as condition not met

                if not condition_met:
                    all_conditions_met = False
                    logger.info(f"Game {game_id}: Conclusion check failed: Condition #{i+1} not met: {condition}")
                    break # No need to check further if one condition fails

        # --- Final Decision ---
        # Conclusion requires all required plot points AND all defined conditions to be met.
        # If we passed the plot point check and all_conditions_met is still True, conclude.
        if all_conditions_met: # This is True if all required plot points passed AND all defined conditions passed (or no conditions were defined)
            logger.info(f"Conclusion check PASSED for game {game_id}.")
            return True
        else:
            # Failure was already logged (either missing required plot point or failed condition)
            return False

    except Exception as e:
        logger.error(f"Error checking conclusion for game {game_id}: {str(e)}", exc_info=True)
        return False

# TODO: Implement other campaign service functions as needed
