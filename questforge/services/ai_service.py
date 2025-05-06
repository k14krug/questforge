import os
import json # Add json import
from openai import OpenAI
from flask import current_app
from questforge.models.game import Game
from questforge.models.game_state import GameState
from questforge.models.template import Template
from questforge.utils.prompt_builder import build_campaign_prompt, build_response_prompt, build_character_name_prompt # Added build_character_name_prompt
# We will need a new prompt builder function, import placeholder
# from questforge.utils.prompt_builder import build_initial_scene_prompt
from questforge.utils.context_manager import build_context
from typing import Dict, Optional, Tuple, Any # Import Dict, Optional, Tuple, and Any for type hinting
import requests # Import requests for API calls
from decimal import Decimal # Import Decimal for cost calculation
from ..models.api_usage_log import ApiUsageLog # Import ApiUsageLog
from ..extensions import db # Import db

class AIService:
    """Service for handling AI interactions, including campaign generation and responses."""

    def __init__(self):
        """Initializes the AI service, setting up the OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Use Flask's application context to get the logger safely
            try:
                 app = current_app._get_current_object()
                 app.logger.warning("OPENAI_API_KEY environment variable not set. AI service may not function.")
            except RuntimeError:
                 # Handle cases where service might be initialized outside app context (e.g., tests)
                 print("Warning: OPENAI_API_KEY not set and running outside Flask app context.")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
            # Remove self.model initialization here - fetch dynamically later
            # self.model = os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo" 
            # Keep temperature and max_tokens if they are static per service instance
            self.temperature = float(os.getenv("OPENAI_TEMPERATURE") or 0.7)
            self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS") or 1024)

    def generate_campaign(self, template: Template, template_overrides: Optional[Dict[str, Any]] = None, creator_customizations: Optional[Dict[str, Any]] = None, player_details: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Generates campaign data using the AI based on a template, template overrides, creator customizations, and player details.

        Args:
            template: The Template object to base the campaign on.
            template_overrides: Optional dictionary of fields to override from the template.
            creator_customizations: Optional dictionary of creator-provided customizations.
            player_details: Optional dictionary mapping user_id (str) to a dict containing 'name' and 'description'.

        Returns:
            A dictionary containing the generated campaign data, model used, and usage data, or an error dict.
        """
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot generate campaign.")
            return {"error": "AI service not available."}

        # Build the prompt using the prompt_builder, passing overrides, customizations, and player details
        prompt = build_campaign_prompt(template, template_overrides, creator_customizations, player_details) # Pass details here
        app.logger.debug(f"--- AI Service: Generating campaign with prompt ---\n{prompt}\n-------------------------------------------------")

        generated_content = "" # Initialize to handle potential errors before assignment
        try:
            # Fetch model from app config at time of call
            model_to_use = app.config.get('OPENAI_MODEL', 'gpt-4o') # Default to gpt-4o if not in config
            app.logger.debug(f"Using model from config for generate_campaign: {model_to_use}")
            
            response = self.client.chat.completions.create(
                model=model_to_use, # Use dynamically fetched model
                messages=[
                    {"role": "system", "content": "You are a creative game master designing the beginning of a text-based adventure game according to the user's template and inputs. Output ONLY the requested JSON object."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }, # Request JSON output
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            generated_content = response.choices[0].message.content
            app.logger.debug(f"--- AI Service: Received raw response ---\n{generated_content}\n------------------------------------------")

            # Parse the JSON response
            parsed_data = json.loads(generated_content)

            # Validate the response structure based on the *new* expected keys from the revised prompt
            required_top_level_keys = [
                'campaign_objective', 
                'generated_locations', 
                'generated_characters', 
                'generated_plot_points', 
                'initial_scene'
            ]
            missing_keys = [k for k in required_top_level_keys if k not in parsed_data]
            if missing_keys:
                app.logger.error(f"AI campaign response missing required top-level keys: {missing_keys}")
                app.logger.debug(f"Received data: {parsed_data}") # Log what was received
                return {"error": f"AI response missing required keys: {', '.join(missing_keys)}"}

            # Validate the structure of 'initial_scene'
            initial_scene = parsed_data.get('initial_scene', {})
            if not isinstance(initial_scene, dict) or not all(k in initial_scene for k in ['description', 'state', 'goals']):
                app.logger.error("AI campaign response 'initial_scene' is missing required keys ('description', 'state', 'goals') or is not a dictionary.")
                app.logger.debug(f"Received initial_scene: {initial_scene}")
                return {"error": "Invalid 'initial_scene' structure in AI response."}
            if not isinstance(initial_scene.get('state'), dict):
                 app.logger.error("AI campaign response 'initial_scene.state' is not a dictionary.")
                 app.logger.debug(f"Received initial_scene state: {initial_scene.get('state')}")
                 return {"error": "Invalid 'initial_scene.state' structure in AI response."}
            if not isinstance(initial_scene.get('goals'), list):
                 app.logger.error("AI campaign response 'initial_scene.goals' is not a list.")
                 app.logger.debug(f"Received initial_scene goals: {initial_scene.get('goals')}")
                 return {"error": "Invalid 'initial_scene.goals' structure in AI response."}
            
            # Optional: Add basic type checks for other generated lists if needed
            if not isinstance(parsed_data.get('generated_locations'), list):
                 app.logger.warning("AI campaign response 'generated_locations' is not a list.") # Warning for now
            if not isinstance(parsed_data.get('generated_characters'), list):
                 app.logger.warning("AI campaign response 'generated_characters' is not a list.") # Warning for now
            
            # Validate generated_plot_points structure
            plot_points = parsed_data.get('generated_plot_points')
            if not isinstance(plot_points, list):
                app.logger.error("AI campaign response 'generated_plot_points' is not a list.")
                return {"error": "Invalid 'generated_plot_points' structure: not a list."}
            for i, pp in enumerate(plot_points):
                if not isinstance(pp, dict) or not all(k in pp for k in ['description', 'required']):
                    app.logger.error(f"AI campaign response 'generated_plot_points' item {i} is not a dict or missing 'description'/'required' keys.")
                    return {"error": f"Invalid 'generated_plot_points' item structure at index {i}."}
                if not isinstance(pp.get('description'), str):
                    app.logger.error(f"AI campaign response 'generated_plot_points' item {i} 'description' is not a string.")
                    return {"error": f"Invalid 'generated_plot_points' item {i} 'description' type."}
                if not isinstance(pp.get('required'), bool):
                    app.logger.error(f"AI campaign response 'generated_plot_points' item {i} 'required' is not a boolean.")
                    return {"error": f"Invalid 'generated_plot_points' item {i} 'required' type."}


            # Validation passed for the new structure
            app.logger.info("--- AI Service: Parsed campaign data successfully (new structure) ---")
            # Extract usage data
            usage_data = response.usage if response.usage else None
            model_used = response.model
            
            # Log API usage - need game_id here, but it's not available. Log against template creator for now.
            # This logging needs to be moved to the game creation endpoint where game_id is known.
            # For now, just return the data.
            # log_api_usage(...) 

            # Return parsed data, model used, and usage data
            return parsed_data, model_used, usage_data

        except json.JSONDecodeError as e:
            # Log the error and the content that failed to parse
            app.logger.error(f"Error decoding AI JSON response: {e}")
            app.logger.error(f"Raw content that failed JSON parsing: {generated_content}")
            return {"error": "AI response content is not valid JSON", "raw_content": generated_content}
        except Exception as e:
            # Log other potential errors
            app.logger.error(f"Error calling OpenAI API or processing response: {e}", exc_info=True)
            return {"error": f"Failed to call AI service: {e}"}

    def generate_initial_scene(self, game: Game) -> dict | None:
        """
        Generates the initial narrative description and available actions for a new game.

        Args:
            game: The Game object, expected to have its 'campaign' relationship loaded.

        Returns:
            A dictionary containing 'narrative' and 'actions' or None on failure.
        """
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot generate initial scene.")
            return None
        if not game.campaign:
             app.logger.error(f"Game {game.id} has no associated campaign loaded. Cannot generate initial scene.")
             return None

        # Fetch the associated GameState to get the initial state data
        # Note: This assumes the GameState record was created *before* this method is called
        # The handle_start_game logic should ensure this.
        game_state = GameState.query.filter_by(game_id=game.id).first()
        if not game_state:
             app.logger.error(f"Cannot generate initial scene for game {game.id}: Corresponding GameState not found.")
             return None

        # For now, let's create a basic prompt here:
        # Access description from the campaign_data JSON field
        campaign_data_dict = game.campaign.campaign_data or {}
        campaign_desc = campaign_data_dict.get('description', "A new adventure.") # Get description from JSON
        # Get initial state from the GameState record
        initial_state_dict = game_state.state_data or {}
        initial_state_desc = json.dumps(initial_state_dict, indent=2)

        prompt = (
            f"You are a game master starting a text adventure based on the following campaign:\n"
            f"Description: {campaign_desc}\n"
            f"Initial State: {initial_state_desc}\n\n"
            f"Generate the very first scene description (narrative) and the initial set of available actions for the player(s). "
            f"Output ONLY a JSON object with the keys 'narrative' (string, the opening scene description) and 'actions' (list of strings, the first available actions)."
        )
        app.logger.debug(f"--- AI Service: Generating initial scene with prompt ---\n{prompt}\n-------------------------------------------------")

        generated_content = "" # Initialize
        # 3. Call OpenAI API
        try:
            # Fetch model from app config at time of call
            model_to_use = app.config.get('OPENAI_MODEL', 'gpt-3.5-turbo') # Default if not in config
            app.logger.debug(f"Using model from config for generate_initial_scene: {model_to_use}")
            
            app.logger.info(f"Attempting OpenAI API call for initial scene (Game {game.id})...")
            response = self.client.chat.completions.create(
                model=model_to_use, # Use dynamically fetched model
                messages=[
                    # No specific system message needed if included in user prompt
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" },
                temperature=self.temperature, # Use existing temp/tokens
                max_tokens=self.max_tokens
            )
            app.logger.info(f"OpenAI API call successful for initial scene (Game {game.id}).")
            generated_content = response.choices[0].message.content
            app.logger.debug(f"--- AI Service: Received raw initial scene response ---\n{generated_content}\n------------------------------------------")

            app.logger.info(f"Attempting to parse JSON for initial scene (Game {game.id})...")
            parsed_data = json.loads(generated_content)
            app.logger.info(f"JSON parsing successful for initial scene (Game {game.id}).")

            # Validate response structure
            if not all(k in parsed_data for k in ['narrative', 'actions']):
                 app.logger.error("Initial scene response missing required keys ('narrative', 'actions').")
                 return None
            if not isinstance(parsed_data.get('narrative'), str) or not isinstance(parsed_data.get('actions'), list):
                 app.logger.error("Initial scene response has incorrect types for 'narrative' or 'actions'.")
                 return None

            app.logger.info(f"--- AI Service: Parsed initial scene successfully for game {game.id} ---")
            # Return narrative, actions, model, and usage
            usage_data = response.usage if response.usage else None
            model_used = response.model
            
            # Log API usage - need game_id here, which is available
            # log_api_usage(
            #     user_id=game.created_by, # Log against the game creator
            #     model_name=model_used,
            #     prompt_tokens=usage_data.prompt_tokens if usage_data else 0,
            #     completion_tokens=usage_data.completion_tokens if usage_data else 0,
            #     total_tokens=usage_data.total_tokens if usage_data else 0,
            #     cost=calculate_cost(model_used, {'prompt_tokens': usage_data.prompt_tokens if usage_data else 0, 'completion_tokens': usage_data.completion_tokens if usage_data else 0}),
            #     endpoint='generate_initial_scene',
            #     game_id=game.id
            # )

            return {
                'narrative': parsed_data['narrative'],
                'actions': parsed_data['actions']
            }


        except json.JSONDecodeError as e:
            app.logger.error(f"Error decoding initial scene JSON response: {e}")
            app.logger.error(f"Raw content: {generated_content}")
            return None
        except Exception as e:
            app.logger.error(f"Error generating initial scene: {e}", exc_info=True)
            return None

    def get_response(self, game_state: GameState, player_action: str, is_stuck: bool = False, next_required_plot_point: Optional[str] = None) -> dict | None:
        """
        Gets the AI's response to a player's action within the current game context.

        Args:
            game_state: The current GameState object.
            player_action: The action taken by the player (string).
            is_stuck: Boolean indicating if the player might be stuck.
            next_required_plot_point: Optional string describing the next required plot point.

        Returns:
            A dictionary containing the AI's narrative response ('content') and
            any resulting 'state_changes' (dictionary), and 'available_actions' (list).
            Returns None on failure.
        """
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot get response.")
            return None

        # 1. Build Context
        # Pass next_required_plot_point to build_context
        context = build_context(game_state, next_required_plot_point)
        if context.startswith("Error:"):
            app.logger.error(f"Error building context: {context}")
            return None
        
        # Log the built context before building the prompt
        app.logger.debug(f"--- AI Service: Context built for get_response ---\n{context}\n-------------------------------------------------")

        # 2. Build Prompt
        # Pass is_stuck and next_required_plot_point to build_response_prompt
        prompt = build_response_prompt(context, player_action, is_stuck, next_required_plot_point)
        app.logger.debug(f"--- AI Service: Getting response with prompt ---\n{prompt}\n---------------------------------------------")

        generated_content = "" # Initialize
        # 3. Call OpenAI API
        try:
            # Fetch model from app config at time of call
            model_to_use = app.config.get('OPENAI_MODEL', 'gpt-3.5-turbo') # Default if not in config
            app.logger.debug(f"Using model from config for get_response: {model_to_use}")
            
            response = self.client.chat.completions.create(
                model=model_to_use, # Use dynamically fetched model
                messages=[
                    # System message is now part of the prompt builder
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }, # Request JSON output
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            generated_content = response.choices[0].message.content
            app.logger.debug(f"--- AI Service: Received raw response ---\n{generated_content}\n------------------------------------------")

            # 4. Parse and Validate Response
            parsed_data = json.loads(generated_content)

            # Basic validation for required keys - now includes 'available_actions'
            if not all(k in parsed_data for k in ['content', 'state_changes', 'available_actions']):
                 app.logger.error("AI response missing required keys ('content', 'state_changes', 'available_actions').")
                 return None
            if not isinstance(parsed_data.get('state_changes'), dict):
                 app.logger.error("AI response 'state_changes' is not a dictionary.")
                 return None
            if not isinstance(parsed_data.get('available_actions'), list):
                 app.logger.error("AI response 'available_actions' is not a list.")
                 return None


            app.logger.info("--- AI Service: Parsed response data successfully ---")
            # Rename 'content' to 'narrative' for consistency
            usage_data = response.usage if response.usage else None
            model_used = response.model
            
            # Log API usage - need game_id here, which is available via game_state.game_id
            # log_api_usage(
            #     user_id=game_state.game.created_by, # Log against the game creator
            #     model_name=model_used,
            #     prompt_tokens=usage_data.prompt_tokens if usage_data else 0,
            #     completion_tokens=usage_data.completion_tokens if usage_data else 0,
            #     total_tokens=usage_data.total_tokens if usage_data else 0,
            #     cost=calculate_cost(model_used, {'prompt_tokens': usage_data.prompt_tokens if usage_data else 0, 'completion_tokens': usage_data.completion_tokens if usage_data else 0}),
            #     endpoint='get_response',
            #     game_id=game_state.game_id
            # )
            
            response_dict = {
                'narrative': parsed_data['content'],
                'state_changes': parsed_data['state_changes'],
                'available_actions': parsed_data['available_actions']
            }

            # Return the dictionary, model used, and usage data as a tuple
            return response_dict, model_used, usage_data


        except json.JSONDecodeError as e:
            app.logger.error(f"Error decoding AI JSON response: {e}")
            app.logger.error(f"Raw content: {generated_content}")
            return None
        except Exception as e:
            app.logger.error(f"Error generating response: {e}", exc_info=True)
            return None

    def generate_character_name(self, description: str) -> str | None:
        """
        Generates a character name using the AI based on a description.

        Args:
            description: The character description provided by the player.

        Returns:
            The generated character name as a string, or None on failure.
        """
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot generate character name.")
            return None

        # Build the prompt using the specific prompt builder
        prompt = build_character_name_prompt(description)
        app.logger.debug(f"--- AI Service: Generating character name with prompt ---\n{prompt}\n-------------------------------------------------")

        generated_name = None # Initialize
        try:
            # Fetch model from app config - use a potentially cheaper/faster model for this simple task?
            # Or stick with the main one? Let's use the main one for now for consistency.
            model_to_use = app.config.get('OPENAI_MODEL', 'gpt-4o')
            app.logger.debug(f"Using model from config for generate_character_name: {model_to_use}")

            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=[
                    # System message is implicit in the prompt builder's structure
                    {"role": "user", "content": prompt}
                ],
                # No specific response format needed, just expect plain text
                temperature=self.temperature, # Use existing temp
                max_tokens=50 # Limit tokens for just a name
            )
            generated_name = response.choices[0].message.content.strip()
            app.logger.debug(f"--- AI Service: Received raw name response ---\n{generated_name}\n------------------------------------------")

            # Basic validation/cleanup (remove quotes if AI added them)
            generated_name = generated_name.strip('"\'')

            if not generated_name:
                app.logger.warning("AI generated an empty character name.")
                return None # Treat empty name as failure

            app.logger.info(f"--- AI Service: Generated character name successfully: {generated_name} ---")

            # Log API Usage - Requires game_id and user_id, which aren't directly available here.
            # This logging should ideally happen where this function is called (e.g., campaign_service).
            # We'll return the name and let the caller handle logging.
            # usage_data = response.usage if response.usage else None
            # model_used = response.model
            # log_api_usage(...)

            return generated_name

        except Exception as e:
            # Log potential errors
            app.logger.error(f"Error calling OpenAI API or processing name response: {e}", exc_info=True)
            return None


# Helper functions for API calls and cost calculation (moved from game.py)
def call_openai_api(prompt: str, model: str = 'gpt-4o') -> Tuple[Dict[str, Any], Decimal]:
    """
    Calls the OpenAI API with the given prompt and model.
    
    Args:
        prompt: The prompt string to send to the AI.
        model: The name of the OpenAI model to use.
        
    Returns:
        A tuple containing the JSON response from the API and the calculated cost.
    """
    api_key = current_app.config.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not configured.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": { "type": "json_object" } # Request JSON object output
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        response_data = response.json()
        
        # Calculate cost
        cost = calculate_cost(model, response_data.get('usage', {}))
        
        return response_data, cost

    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        raise # Re-raise the exception after logging

def calculate_cost(model: str, usage: Dict[str, int]) -> Decimal:
    """
    Calculates the cost of an API call based on the model and token usage.
    
    Args:
        model: The name of the model used.
        usage: A dictionary containing 'prompt_tokens' and 'completion_tokens'.
        
    Returns:
        The calculated cost as a Decimal.
    """
    pricing = current_app.config.get('OPENAI_PRICING', {})
    
    prompt_tokens = usage.get('prompt_tokens', 0)
    completion_tokens = usage.get('completion_tokens', 0)
    
    # Get pricing per 1M tokens
    prompt_cost_per_million = pricing.get(model, {}).get('prompt', 0)
    completion_cost_per_million = pricing.get(model, {}).get('completion', 0)
    
    # Calculate cost
    prompt_cost = (Decimal(prompt_tokens) / Decimal(1_000_000)) * Decimal(prompt_cost_per_million)
    completion_cost = (Decimal(completion_tokens) / Decimal(1_000_000)) * Decimal(completion_cost_per_million)
    
    total_cost = prompt_cost + completion_cost
    
    return total_cost.quantize(Decimal('0.000001')) # Quantize to 6 decimal places

def log_api_usage(user_id: int, model_name: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cost: Decimal, endpoint: str, game_id: Optional[int] = None):
    """
    Logs API usage to the database.
    
    Args:
        user_id: The ID of the user who initiated the action.
        model_name: The name of the AI model used.
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        total_tokens: Total number of tokens.
        cost: The calculated cost of the API call.
        endpoint: A string identifying the API endpoint or action.
        game_id: Optional ID of the game associated with the usage.
    """
    log_entry = ApiUsageLog(
        user_id=user_id,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost=cost,
        endpoint=endpoint,
        game_id=game_id
    )
    db.session.add(log_entry)
    db.session.commit() # Commit immediately for logging


# Singleton instance
ai_service = AIService()
