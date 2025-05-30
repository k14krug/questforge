from questforge.models.game_state import GameState
from questforge.extensions import db
from typing import Dict, List, Optional

class InventoryService:
    """Handles player inventory operations including:
    - Managing player-specific inventories
    - Item transfers between players
    - Shared item handling
    """
    
    @staticmethod
    def get_player_inventory(game_state: GameState, player_id: str) -> List[Dict]:
        """Get a player's inventory from game state"""
        return game_state.state_data.get('inventories', {}).get(player_id, [])
    
    @staticmethod
    def add_item(game_state: GameState, player_id: str, item_name: str, is_shared: bool = False) -> None:
        """Add an item to a player's inventory"""
        if 'inventories' not in game_state.state_data:
            game_state.state_data['inventories'] = {}
            
        if player_id not in game_state.state_data['inventories']:
            game_state.state_data['inventories'][player_id] = []
            
        # Prevent adding item if it already exists in the player's inventory
        current_player_inventory = game_state.state_data['inventories'][player_id]
        if any(item['name'] == item_name for item in current_player_inventory):
            current_app.logger.debug(f"Item '{item_name}' already exists in player {player_id}'s inventory. Skipping addition.")
            return
            
        current_player_inventory.append({
            'name': item_name,
            'is_shared': is_shared,
            'owner_id': player_id
        })
    
    @staticmethod
    def remove_item(game_state: GameState, player_id: str, item_name: str) -> bool:
        """Remove an item from a player's inventory"""
        inventory = game_state.state_data.get('inventories', {}).get(player_id, [])
        for i, item in enumerate(inventory):
            if item['name'] == item_name:
                inventory.pop(i)
                return True
        return False
    
    @staticmethod
    def transfer_item(game_state: GameState, from_player: str, to_player: str, item_name: str) -> bool:
        """Transfer an item between players if it's shareable"""
        from_inventory = game_state.state_data.get('inventories', {}).get(from_player, [])
        item_to_transfer = None
        
        # Find the item in source inventory
        for i, item in enumerate(from_inventory):
            if item['name'] == item_name and item['is_shared']:
                item_to_transfer = from_inventory.pop(i)
                break
                
        if not item_to_transfer:
            return False
            
        # Add to target inventory
        if to_player not in game_state.state_data['inventories']:
            game_state.state_data['inventories'][to_player] = []
            
        game_state.state_data['inventories'][to_player].append(item_to_transfer)
        return True
    
    @staticmethod
    def get_shared_items(game_state: GameState, player_id: str) -> List[Dict]:
        """Get all items shared with a player (from other players)"""
        shared_items = []
        for owner_id, inventory in game_state.state_data.get('inventories', {}).items():
            if owner_id == player_id:
                continue
            shared_items.extend([item for item in inventory if item['is_shared']])
        return shared_items
