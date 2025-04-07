# QuestForge SocketIO API Documentation

## Connection Management
- **Event:** `connect`  
  **Description:** Automatically handled when client connects  
  **Response:** `connection_response` with status

- **Event:** `disconnect`  
  **Description:** Automatically handled when client disconnects

## Game Room Operations
- **Event:** `joinGame`  
  **Payload:**  
  ```json
  {
    "game_id": "string",
    "user_id": "string"
  }
  ```
  **Response:** `gameStateUpdate` with full game state

- **Event:** `leaveGame`  
  **Payload:**  
  ```json
  {
    "game_id": "string",
    "user_id": "string"
  }
  ```
  **Broadcast:** `player_left` to room

## Game State Management
- **Event:** `playerAction`  
  **Payload:**  
  ```json
  {
    "game_id": "string",
    "user_id": "string",
    "action": "object",
    "state_version": "number"
  }
  ```
  **Responses:**  
  - `gameUpdate`: Broadcast to all players with action results
  - `gameStateUpdate`: Sent to acting player with full state
  - `stateConflict`: If version mismatch occurs

## State Update Events
- **Event:** `gameStateUpdate`  
  **Payload:**  
  ```json
  {
    "game": "object",
    "state": {
      "version": "number",
      "state": "object"
    },
    "player_state": "object"
  }
  ```

- **Event:** `stateConflict`  
  **Payload:**  
  ```json
  {
    "message": "string",
    "server_state": "object",
    "state_diff": "object",
    "client_version": "number",
    "server_version": "number"
  }
  ```

## Error Handling
- **Event:** `error`  
  **Payload:**  
  ```json
  {
    "message": "string"
  }
  ```

## Implementation Notes
1. All game-specific events use room-based broadcasting
2. State versioning prevents race conditions
3. Conflict resolution provides:
   - Server state snapshot
   - State changes since client's version
4. Client should:
   - Track local state version
   - Handle conflict resolution
   - Apply optimistic updates
