import os
import json # Add json import
from openai import OpenAI
from flask import current_app
from questforge.models.game import Game
from questforge.models.game_state import GameState
from questforge.models.template import Template
from questforge.utils.prompt_builder import build_campaign_prompt, build_response_prompt
# We will need a new prompt builder function, import placeholder
# from questforge.utils.prompt_builder import build_initial_scene_prompt
from questforge.utils.context_manager import build_context

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
            self.model = os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo"
            self.temperature = float(os.getenv("OPENAI_TEMPERATURE") or 0.7)
            self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS") or 1024)

    def generate_campaign(self, template: Template, user_inputs: dict):
        """
        Generates the initial campaign structure based on a template and user inputs.

        Args:
            template: The Template object used as a base.
            user_inputs: A dictionary of user responses to template questions.

        Returns:
            A dictionary representing the generated campaign structure (e.g., description, initial state)
            or None if generation fails.
        """
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot generate campaign.")
            return None

        prompt = build_campaign_prompt(template, user_inputs)
        app.logger.debug(f"--- AI Service: Generating campaign with prompt ---\n{prompt}\n-------------------------------------------------")

        generated_content = "" # Initialize to handle potential errors before assignment
        try:
            response = self.client.chat.completions.create(
                model=self.model,
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

            # TODO: Implement more robust validation, potentially using template.validate_ai_response
            if not all(k in parsed_data for k in ['initial_description', 'initial_state', 'goals']):
                 app.logger.error("AI response missing required keys.")
                 # Consider adding 'key_npcs' validation if it becomes mandatory
                 return None

            # Basic validation passed (structure-wise)
            app.logger.info("--- AI Service: Parsed campaign data successfully ---")
            return parsed_data

        except json.JSONDecodeError as e:
            # Log the error and the content that failed to parse
            app.logger.error(f"Error decoding AI JSON response: {e}")
            app.logger.error(f"Raw content that failed JSON parsing: {generated_content}")
            return None
        except Exception as e:
            # Log other potential errors
            app.logger.error(f"Error calling OpenAI API or processing response: {e}", exc_info=True)
            return None # Fixed the syntax error here

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
        try:
            app.logger.info(f"Attempting OpenAI API call for initial scene (Game {game.id})...")
            response = self.client.chat.completions.create(
                model=self.model,
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
            # Return only narrative and actions as per the function's goal
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

    def get_response(self, game_state: GameState, player_action: str) -> dict | None:
        """
        Gets the AI's response to a player's action within the current game context.

        Args:
            game_state: The current GameState object.
            player_action: The action taken by the player (string).

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
        context = build_context(game_state)
        if context.startswith("Error:"):
            app.logger.error(f"Error building context: {context}")
            return None

        # 2. Build Prompt
        prompt = build_response_prompt(context, player_action)
        app.logger.debug(f"--- AI Service: Getting response with prompt ---\n{prompt}\n---------------------------------------------")

        generated_content = "" # Initialize
        # 3. Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
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
            return {
                'narrative': parsed_data['content'],
                'state_changes': parsed_data['state_changes'],
                'available_actions': parsed_data['available_actions']
            }


        except json.JSONDecodeError as e:
            app.logger.error(f"Error decoding AI JSON response: {e}")
            app.logger.error(f"Raw content: {generated_content}")
            return None
        except Exception as e:
            app.logger.error(f"Error calling OpenAI API or processing response: {e}", exc_info=True)
            return None

# Singleton instance
ai_service = AIService()
