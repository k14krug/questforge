import os
import json # Add json import
from openai import OpenAI
from flask import current_app
from questforge.models.game import Game
from questforge.models.game_state import GameState
from questforge.models.template import Template
from questforge.utils.prompt_builder import build_campaign_prompt, build_response_prompt
from questforge.utils.context_manager import build_context

class AIService:
    """Service for handling AI interactions, including campaign generation and responses."""

    def __init__(self):
        """Initializes the AI service, setting up the OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            app = current_app._get_current_object()
            app.logger.warning("OPENAI_API_KEY environment variable not set. AI service may not function.")
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
            app = current_app._get_current_object()
            app.logger.error(f"Error decoding AI JSON response: {e}")
            app.logger.error(f"Raw content: {generated_content}")
            return None
        except Exception as e:
            app = current_app._get_current_object()
            app.logger.error(f"Error calling OpenAI API or processing response: {e}")
            return None


    def get_response(self, game_state: GameState, player_action: str) -> dict | None:
        """
        Gets the AI's response to a player's action within the current game context.

        Args:
            game_state: The current GameState object.
            player_action: The action taken by the player (string).

        Returns:
            A dictionary containing the AI's narrative response ('content') and
            any resulting 'state_changes' (dictionary). Returns None on failure.
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

            # Basic validation for required keys
            if not all(k in parsed_data for k in ['content', 'state_changes']):
                 app.logger.error("AI response missing required keys ('content', 'state_changes').")
                 return None
            if not isinstance(parsed_data['state_changes'], dict):
                 app.logger.error("AI response 'state_changes' is not a dictionary.")
                 return None

            app.logger.info("--- AI Service: Parsed response data successfully ---")
            return parsed_data

        except json.JSONDecodeError as e:
            app = current_app._get_current_object()
            app.logger.error(f"Error decoding AI JSON response: {e}")
            app.logger.error(f"Raw content: {generated_content}")
            return None
        except Exception as e:
            app = current_app._get_current_object()
            app.logger.error(f"Error calling OpenAI API or processing response: {e}")
            return None

# Singleton instance
ai_service = AIService()
