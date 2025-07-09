import logging
import random
from database import db # Import db directly from database
from models import Game, GameState, GamePlayer
from services.ai_service import AIService
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GameStateService:
    def __init__(self, ai_service: AIService, socketio_instance=None): # Add socketio_instance
        self.ai_service = ai_service
        self.socketio = socketio_instance # Store it

    def get_current_game_state(self, game_id):
        """Retrieves the current GameState for a given game."""
        game = Game.query.get(game_id)
        if not game:
            return None, "Game not found"
        
        logging.info(f"Attempting to retrieve GameState for game_id: {game_id}, current_game_state_id: {game.current_game_state_id}")
        game_state = GameState.query.get(game.current_game_state_id) if game.current_game_state_id else None
        
        if not game_state:
            logging.error(f"GameState not found for game {game_id} with current_game_state_id: {game.current_game_state_id}. Game might not have started or state is missing.")
            return None, "Current game state not found. Game might not have started or state is corrupted."
        
        return game_state, None

    def process_player_action(self, game_id, game_player_id, action_text):
        """
        Processes a player's action, potentially triggering AI skill checks and narrative.
        This is the core of the Action Resolution Workflow.
        """
        game = Game.query.get(game_id)
        if not game:
            return None, "Game not found"

        game_player = GamePlayer.query.get(game_player_id)
        if not game_player or game_player.game_id != game_id:
            return None, "Game player not found or not in this game"

        # Get current game state and charter for AI context
        current_game_state_obj = GameState.query.get(game.current_game_state_id) if game.current_game_state_id else None
        current_game_state_data = {
            "turn_number": current_game_state_obj.turn_number if current_game_state_obj else 0,
            "current_location": current_game_state_obj.current_location if current_game_state_obj else None,
            "active_npcs": current_game_state_obj.active_npcs if current_game_state_obj else [],
            "player_states": current_game_state_obj.player_states if current_game_state_obj else [],
            "game_log": current_game_state_obj.game_log if current_game_state_obj else [],
        }
        logging.debug(f"Debug: current_game_state_data passed to AI: {current_game_state_data}")
        campaign_charter = game.campaign_charter

        total_ai_cost = 0.0
        game_log_entries = []
        room_name = f"game_{game_id}" # Define room name for emits

        # 1. Simulate AI Step 1: Check Identification
        ai_step1_response, cost_step1, _, _ = self.ai_service.process_action_step1_check_identification(
            player_action_text=action_text,
            game_state=current_game_state_data,
            charter=campaign_charter,
            character_sheet=game_player.character_sheet
        )
        total_ai_cost += cost_step1

        # Add player action to log
        player_action_log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "PLAYER_ACTION",
            "actor": game_player.character_name,
            "content": action_text,
            "details": {}
        }
        game_log_entries.append(player_action_log_entry)

        ai_narrative_response = ""

        if ai_step1_response.get("action_requires_roll"):
            skill_needed = ai_step1_response.get("skill")
            difficulty = ai_step1_response.get("difficulty")
            narration_prompt = ai_step1_response.get("narration_prompt")

            # Emit skill_check_initiated event
            if self.socketio:
                self.socketio.emit('skill_check_initiated', {
                    'game_id': game_id,
                    'game_player_id': game_player_id,
                    'character_name': game_player.character_name,
                    'skill_needed': skill_needed,
                    'difficulty': difficulty,
                    'message': f"{game_player.character_name} attempts a {skill_needed} check (Difficulty: {difficulty})."
                }, to=room_name)

            # 2. Look up player's skill bonus
            skill_bonus = game_player.character_sheet.get('skills', {}).get(skill_needed, 0)

            # 3. Simulate dice roll (1d20)
            dice_roll = random.randint(1, 20)
            
            # 4. Calculate final result
            total_result = dice_roll + skill_bonus

            # 5. Compare result to difficulty for outcome
            outcome = "Success" if total_result >= difficulty else "Failure"
            if dice_roll == 20:
                outcome = "Critical Success"
            elif dice_roll == 1:
                outcome = "Critical Failure"

            logging.info(f"Skill Check: {skill_needed}, Roll: {dice_roll}, Bonus: {skill_bonus}, Total: {total_result}, Difficulty: {difficulty}, Outcome: {outcome}")

            roll_result_data = {
                "skill": skill_needed,
                "roll": dice_roll,
                "skill_bonus": skill_bonus,
                "total_result": total_result,
                "difficulty": difficulty,
                "outcome": outcome
            }

            # Add system message for roll result to log
            game_log_entries.append({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "SYSTEM_MESSAGE",
                "actor": "System",
                "content": f"Roll: {dice_roll} + {skill_needed}({skill_bonus}) = {total_result} (Difficulty: {difficulty}) -> {outcome}",
                "details": roll_result_data
            })
            
            # Emit dice_roll_result event
            if self.socketio:
                self.socketio.emit('dice_roll_result', {
                    'game_id': game_id,
                    'game_player_id': game_player_id,
                    'character_name': game_player.character_name,
                    **roll_result_data # Unpack the roll_result_data dictionary
                }, to=room_name)

            # Simulate AI Step 2: Outcome Narration
            ai_narrative_response, cost_step2, _, _ = self.ai_service.process_action_step2_outcome_narration(
                roll_result=roll_result_data,
                narration_prompt=narration_prompt,
                game_state=current_game_state_data,
                charter=campaign_charter
            )
            total_ai_cost += cost_step2

        else:
            # If no roll is required, AI directly narrates the outcome from Step 1's narration_prompt
            ai_narrative_response = ai_step1_response.get("narration_prompt")

        # Add AI narrative to game log
        game_log_entries.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": "GM_NARRATIVE",
            "actor": "AI",
            "content": ai_narrative_response,
            "details": {}
        })

        # Update game's cumulative cost and save the new game log
        game.cumulative_cost += total_ai_cost
        current_game_state_obj.game_log = (current_game_state_obj.game_log or []) + game_log_entries
        current_game_state_obj.updated_at = datetime.utcnow()
        db.session.add(game)
        db.session.add(current_game_state_obj)
        db.session.commit()

        # Advance the turn to the next player
        self._advance_turn(game, current_game_state_obj)

        # After advancing the turn, emit the full game state to all clients
        if self.socketio:
            self.broadcast_game_state(game_id)

        return {
            "message": "Action processed",
            "ai_narrative": ai_narrative_response,
            "ai_cost": total_ai_cost,
            "game_log_entries": game_log_entries
        }, None

    def broadcast_game_state(self, game_id):
        """Fetches the current game state and broadcasts it to the room."""
        game = Game.query.get(game_id)
        if not game:
            logging.error(f"broadcast_game_state: Game not found for game_id {game_id}")
            return

        game_state, error = self.get_current_game_state(game_id)
        if error:
            logging.error(f"broadcast_game_state: Could not get game state for game_id {game_id}: {error}")
            return

        state_dict = game_state.to_dict()
        state_dict['players'] = [player.to_dict() for player in game.game_players]
        state_dict['campaign_charter'] = game.campaign_charter

        logging.info(f"Broadcasting game_state_update for game {game_id} with data: {state_dict}")

        room_name = f"game_{game_id}"
        self.socketio.emit('game_state_update', state_dict, to=room_name)
        logging.info(f"Broadcasted game_state_update for game {game_id} to room {room_name}")

    def _advance_turn(self, game, current_game_state):
        """
        Advances the turn to the next player in the game.
        """
        players = sorted(game.game_players, key=lambda p: p.id) # Ensure consistent order
        if not players:
            logging.warning(f"Cannot advance turn in game {game.id}: no players found.")
            return

        current_player_id = current_game_state.current_player_id
        try:
            current_player_index = [p.user_id for p in players].index(current_player_id)
            next_player_index = (current_player_index + 1) % len(players)
        except ValueError:
            # If current player not found (e.g., they left), default to the first player
            next_player_index = 0

        next_player = players[next_player_index]
        
        # Update the game state
        current_game_state.current_player_id = next_player.user_id
        current_game_state.turn_number += 1
        current_game_state.updated_at = datetime.utcnow()
        db.session.add(current_game_state)
        db.session.commit()

        logging.info(f"Game {game.id} advanced to turn {current_game_state.turn_number}. Current player is now User ID: {next_player.user_id}")

    # NPC Management Methods

    def update_npc_status(self, game_id, npc_id, new_status):
        """
        Updates the status of an NPC in the current game state.
        
        Args:
            game_id: ID of the game
            npc_id: ID of the NPC to update
            new_status: New status for the NPC
            
        Raises:
            ValueError: If the NPC is not found
        """
        game_state, error = self.get_current_game_state(game_id)
        if error:
            raise ValueError(error)
            
        npcs = game_state.active_npcs or []
        npc = next((n for n in npcs if n.get('id') == npc_id), None)
        if not npc:
            raise ValueError(f"NPC {npc_id} not found")
            
        npc['status'] = new_status
        game_state.active_npcs = npcs
        db.session.add(game_state)
        db.session.commit()
        
        # Emit socket event
        if self.socketio:
            room_name = f"game_{game_id}"
            self.socketio.emit('npc_state_update', {
                'npc_id': npc_id,
                'update_type': 'status',
                'new_status': new_status,
                'timestamp': datetime.utcnow().isoformat()
            }, to=room_name)

    def move_npc(self, game_id, npc_id, new_location):
        """
        Moves an NPC to a new location in the current game state.
        
        Args:
            game_id: ID of the game
            npc_id: ID of the NPC to move
            new_location: New location for the NPC
            
        Raises:
            ValueError: If the NPC is not found
        """
        game_state, error = self.get_current_game_state(game_id)
        if error:
            raise ValueError(error)
            
        npcs = game_state.active_npcs or []
        npc = next((n for n in npcs if n.get('id') == npc_id), None)
        if not npc:
            raise ValueError(f"NPC {npc_id} not found")
            
        npc['location'] = new_location
        game_state.active_npcs = npcs
        db.session.add(game_state)
        db.session.commit()
        
        # Emit socket event
        if self.socketio:
            room_name = f"game_{game_id}"
            self.socketio.emit('npc_state_update', {
                'npc_id': npc_id,
                'update_type': 'location',
                'new_location': new_location,
                'timestamp': datetime.utcnow().isoformat()
            }, to=room_name)

    def add_npc_to_scene(self, game_id, npc_data):
        """
        Adds a new NPC to the current game state.
        
        Args:
            game_id: ID of the game
            npc_data: Dictionary containing NPC data
        """
        game_state, error = self.get_current_game_state(game_id)
        if error:
            raise ValueError(error)
            
        # Ensure NPC has required fields
        if 'id' not in npc_data:
            npc_data['id'] = str(uuid.uuid4())
        if 'status' not in npc_data:
            npc_data['status'] = 'active'
            
        npcs = game_state.active_npcs or []
        npcs.append(npc_data)
        game_state.active_npcs = npcs
        db.session.add(game_state)
        db.session.commit()
        
        # Emit socket event
        if self.socketio:
            room_name = f"game_{game_id}"
            self.socketio.emit('npc_added_to_scene', {
                'npc': npc_data,
                'timestamp': datetime.utcnow().isoformat()
            }, to=room_name)

    def remove_npc_from_scene(self, game_id, npc_id):
        """
        Removes an NPC from the current game state.
        
        Args:
            game_id: ID of the game
            npc_id: ID of the NPC to remove
            
        Raises:
            ValueError: If the NPC is not found
        """
        game_state, error = self.get_current_game_state(game_id)
        if error:
            raise ValueError(error)
            
        npcs = game_state.active_npcs or []
        new_npcs = [n for n in npcs if n.get('id') != npc_id]
        
        if len(new_npcs) == len(npcs):
            raise ValueError(f"NPC {npc_id} not found")
            
        game_state.active_npcs = new_npcs
        db.session.add(game_state)
        db.session.commit()
        
        # Emit socket event
        if self.socketio:
            room_name = f"game_{game_id}"
            self.socketio.emit('npc_removed_from_scene', {
                'npc_id': npc_id,
                'timestamp': datetime.utcnow().isoformat()
            }, to=room_name)

    def modify_npc_details(self, game_id, npc_id, updated_fields):
        """
        Modifies details of an existing NPC in the current game state.
        
        Args:
            game_id: ID of the game
            npc_id: ID of the NPC to update
            updated_fields: Dictionary of fields to update
            
        Raises:
            ValueError: If the NPC is not found
        """
        game_state, error = self.get_current_game_state(game_id)
        if error:
            raise ValueError(error)
            
        npcs = game_state.active_npcs or []
        npc = next((n for n in npcs if n.get('id') == npc_id), None)
        if not npc:
            raise ValueError(f"NPC {npc_id} not found")
            
        # Update fields
        for key, value in updated_fields.items():
            npc[key] = value
            
        game_state.active_npcs = npcs
        db.session.add(game_state)
        db.session.commit()
        
        # Emit socket event
        if self.socketio:
            room_name = f"game_{game_id}"
            self.socketio.emit('npc_details_updated', {
                'npc_id': npc_id,
                'updated_fields': updated_fields,
                'timestamp': datetime.utcnow().isoformat()
            }, to=room_name)
