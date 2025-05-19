/**
 * SocketIO Client Manager for QuestForge (Simplified - No Classes)
 * Handles real-time communication with game server
 */

// console.log("Initializing socketClient (no class)..."); // DEBUG REMOVED

let hasSetupListenersForCurrentConnection = false; // Flag to ensure setup runs once per connection

const socketClient = {
  socket: null,
  connected: false,
  isConnecting: false,
  gameId: null,
  hasJoinedRoom: false,
  // onConnectCallbacks: [], // Removed
  onDisconnectCallbacks: [],
  initialStateRequestedThisConnection: false, // New flag specific to a connection cycle

  // Method to setup listeners and request initial state
  setupListenersAndRequestState: function() {
      if (hasSetupListenersForCurrentConnection) { // Still use the module-level flag for overall idempotency per connection
          console.log("SocketClient: setupListenersAndRequestState - ALREADY RUN FOR THIS CONNECTION. Skipping.");
          return;
      }
      hasSetupListenersForCurrentConnection = true;
      console.log("SocketClient: this.setupListenersAndRequestState() called. GameID:", this.gameId);

      if (!this.socket) {
           console.error("SocketClient: setupListenersAndRequestState called but this.socket is NOT available! Aborting listener setup.");
          hasSetupListenersForCurrentConnection = false; 
           return;
      }
      console.log("SocketClient: this.socket IS available in this.setupListenersAndRequestState.");
      
      this.joinRoom(this.gameId); 

      console.log("SocketClient: Setting up 'game_state_update' and 'game_state' listeners on this.socket.");
      
      console.log("SocketClient: Checking this.socket right before attaching game_state/game_state_update listeners:", this.socket);
      if (!this.socket) {
          console.error("SocketClient: CRITICAL - this.socket is NULL or UNDEFINED before attaching game_state/game_state_update listeners! Aborting.");
          hasSetupListenersForCurrentConnection = false; 
          return; 
      }

      this.socket.off('game_state_update'); 
      this.socket.off('game_state'); 

      this.socket.on('game_state_update', (data) => {
          console.log("SocketClient: 'game_state_update' event received. Data object will be logged on next line.");
          console.log(data);
          updateGameState(data); 
          const plotProgressDisplay = document.getElementById('plot-progress-display');
          if (plotProgressDisplay) {
              if (typeof data.total_plot_points_display === 'number' && typeof data.completed_plot_points_display_count === 'number') {
                  plotProgressDisplay.textContent = `Plot Points: ${data.completed_plot_points_display_count} / ${data.total_plot_points_display}`;
                  console.log("SocketClient: Updated plot progress from 'game_state_update':", plotProgressDisplay.textContent);
              } else {
                  plotProgressDisplay.textContent = ''; 
                  console.log("SocketClient: Cleared plot progress from 'game_state_update' due to missing/invalid data.");
              }
          }
          if (data.newly_completed_plot_point_message) {
              console.log("SocketClient: Alerting for newly_completed_plot_point_message:", data.newly_completed_plot_point_message);
              alert(data.newly_completed_plot_point_message);
          }
      });

      this.socket.on('game_state', (state) => { 
          console.log("SocketClient: 'game_state' event received (initial). Data object will be logged on next line.");
          console.log(state);
          updateGameState(state); 
          const plotProgressDisplay = document.getElementById('plot-progress-display');
          if (plotProgressDisplay) {
              if (typeof state.total_plot_points_display === 'number' && typeof state.completed_plot_points_display_count === 'number') {
                  plotProgressDisplay.textContent = `Plot Points: ${state.completed_plot_points_display_count} / ${state.total_plot_points_display}`;
                  console.log("SocketClient: Updated plot progress from 'game_state' (initial):", plotProgressDisplay.textContent);
              } else {
                  plotProgressDisplay.textContent = ''; 
                  console.log("SocketClient: Cleared plot progress from 'game_state' (initial) due to missing/invalid data.");
              }
          }
      });

      this.socket.on('slash_command_response', (data) => {
          console.log("SocketClient: 'slash_command_response' event received:", data);
          appendSlashCommandResponseToLog(data);
      });

      this.socket.on('game_concluded', (data) => { /* ... existing handler ... */ });
      
      this.requestInitialState(); 
      this.setupDifficultyChangeListener(); // Call the new method
      
      if (typeof this.socket.onAny === 'function') {
          this.socket.onAny((eventName, ...args) => {
              console.log(`SocketClient: onAny - Event received: '${eventName}' with data:`, args);
          });
          console.log("SocketClient: Attached onAny listener to this.socket.");
      } else {
          console.warn("SocketClient: this.socket.onAny is not a function on this Socket.IO client version.");
      }
  },

  setupDifficultyChangeListener: function() {
    const difficultySelector = document.getElementById('difficultySelector');
    if (difficultySelector && this.socket) {
        difficultySelector.addEventListener('change', (event) => {
            const newDifficulty = event.target.value;
            if (this.gameId) {
                console.log(`SocketClient: Difficulty changed to ${newDifficulty}. Emitting 'change_difficulty'.`);
                this.socket.emit('change_difficulty', {
                    game_id: this.gameId,
                    new_difficulty: newDifficulty,
                    user_id: window.currentUserId // Pass user_id for validation on server
                });
            } else {
                console.error("SocketClient: gameId not set, cannot emit change_difficulty.");
            }
        });
        console.log("SocketClient: Attached change listener to difficultySelector.");
    } else {
        if (!difficultySelector) console.log("SocketClient: difficultySelector element not found, listener not attached.");
        if (!this.socket) console.log("SocketClient: socket not available, difficulty listener not attached.");
    }
  },

  requestInitialState: function() {
      const userId = document.getElementById('gameTitle')?.dataset.userId;
      console.log(`SocketClient: this.requestInitialState called. initialStateRequestedThisConnection: ${this.initialStateRequestedThisConnection}, socket: ${!!this.socket}, connected: ${this.connected}, userId: ${userId}`);

      if (!this.initialStateRequestedThisConnection && this.socket && this.connected && userId) {
          console.log(`SocketClient: Condition MET for emitting 'request_state'. GameID: ${this.gameId}, UserID: ${userId}`);
          this.socket.emit('request_state', { game_id: this.gameId, user_id: userId });
          this.initialStateRequestedThisConnection = true;
          console.log("SocketClient: Emitted 'request_state'. initialStateRequestedThisConnection set to true.");
      } else if (!this.initialStateRequestedThisConnection) {
           console.log(`SocketClient: Condition NOT MET for emitting 'request_state'. initialStateRequestedThisConnection: ${this.initialStateRequestedThisConnection}, socket: ${!!this.socket}, connected: ${this.connected}, userId: ${userId}`);
      } else {
          console.log("SocketClient: this.requestInitialState - initial state already requested for this connection.");
      }
  },

  connect: function(gameId) {
    // console.log(`socketClient.connect(${gameId}) called.`); // DEBUG REMOVED
    if (this.socket && this.connected && this.gameId === gameId) {
        console.log(`SocketClient: Connect called for game ${gameId}, but already connected to it. Triggering setup directly if needed.`);
        // If already connected, ensure setup runs if it hasn't for this connection cycle.
        // The hasSetupListenersForCurrentConnection flag handles idempotency.
        if (typeof this.setupListenersAndRequestState === 'function') {
             setTimeout(() => this.setupListenersAndRequestState(), 0);
        }
        return;
    }
    if (this.socket && this.gameId !== gameId) {
        console.log(`SocketClient: Switching game context. Disconnecting from ${this.gameId}.`);
        this.disconnect(); 
    }
    if (this.isConnecting && this.gameId === gameId) { // Check if connecting to the *same* game
         console.log("SocketClient: Connection attempt already in progress for this game.");
         return;
    }

    console.log(`SocketClient: Attempting to connect for gameId: ${gameId}`);
    this.gameId = gameId;
    this.isConnecting = true;
    this.initialStateRequestedThisConnection = false; // Reset for new connection attempt

    try {
      this.socket = io({ path: '/socket.io/' });
      const self = this; // self is socketClient

      this.socket.on('connect', () => {
        console.log("SocketClient: 'connect' event successfully fired. Setting up client state.");
        self.connected = true;
        self.isConnecting = false;
        self.hasJoinedRoom = false;
        hasSetupListenersForCurrentConnection = false; // Reset global flag for the new connection instance
        
        console.log(`SocketClient: SocketIO connected for game ${self.gameId}. Now calling setupListenersAndRequestState.`);
        if (typeof self.setupListenersAndRequestState === 'function') {
            self.setupListenersAndRequestState(); // Direct call
        } else {
            console.error("SocketClient: CRITICAL - self.setupListenersAndRequestState is not a function!");
        }
      });

      this.socket.on('disconnect', (reason) => {
        // console.log(`Socket disconnected: ${reason}`); // DEBUG REMOVED
        const wasConnected = self.connected;
        self.connected = false;
        self.isConnecting = false;
        self.hasJoinedRoom = false;
        if (wasConnected) {
            self.onDisconnectCallbacks.forEach(cb => cb());
        }
      });

      // Add other necessary listeners back
      this.socket.on('player_list', function(data) {
         // console.log(`Received player_list event for game ${self.gameId}:`, data); // DEBUG REMOVED
         const playerList = document.getElementById('player-list');
         if (playerList && data?.players) {
          playerList.innerHTML = ''; 
          data.players.forEach(player => {
            const playerItem = document.createElement('li');
            playerItem.className = 'list-group-item d-flex justify-content-between align-items-center';
            playerItem.dataset.userId = player.user_id;
            playerItem.innerHTML = `
              <span>
                ${player.username}
                <span class="ready-status ms-2">${player.is_ready ? '✅' : '❌'}</span>
              </span>
              ${player.user_id == window.currentUserId && !player.is_ready ? 
                '<button class="btn btn-sm btn-success ready-button">Ready Up</button>' : ''}
            `;
            playerList.appendChild(playerItem);
          });
           if (typeof checkAllPlayersReady === 'function') {
              checkAllPlayersReady();
          }
        }
      });

      this.socket.on('player_joined', function(data) {
          // console.log(`Received player_joined event for game ${self.gameId}:`, data); // DEBUG REMOVED
          const playerList = document.getElementById('player-list'); 
          if (playerList && data && data.username && data.user_id) {
             if (!playerList.querySelector(`li[data-user-id="${data.user_id}"]`)) {
                 const playerItem = document.createElement('li');
                 playerItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                 playerItem.dataset.userId = data.user_id;
                 playerItem.innerHTML = `
                     <span> ${data.username} <span class="ready-status ms-2">${data.is_ready ? '✅' : '❌'}</span> </span>
                     ${data.user_id == window.currentUserId && !data.is_ready ? '<button class="btn btn-sm btn-success ready-button">Ready Up</button>' : ''}
                 `;
                 playerList.appendChild(playerItem);
             }
             if (typeof checkAllPlayersReady === 'function') checkAllPlayersReady();
         }
      });

      this.socket.on('player_left', function(data) {
          // console.log(`Received player_left event for game ${self.gameId}:`, data); // DEBUG REMOVED
          const playerList = document.getElementById('player-list'); 
          if (playerList && data && data.user_id) {
             const playerItem = playerList.querySelector(`li[data-user-id="${data.user_id}"]`);
             if (playerItem) playerItem.remove();
             if (typeof checkAllPlayersReady === 'function') checkAllPlayersReady();
         }
      });

      this.socket.on('player_status_update', function(data) {
        // console.log(`Received player_status_update event:`, data); // DEBUG REMOVED
        if (data && data.user_id && typeof data.is_ready !== 'undefined') {
          const event = new CustomEvent('playerStatusUpdate', { detail: { userId: data.user_id, isReady: data.is_ready } });
          // console.log(`Dispatching playerStatusUpdate event for userId=${data.user_id}, isReady=${data.is_ready}`); // DEBUG REMOVED
          window.dispatchEvent(event);
          // Also call checkAllPlayersReady directly if needed in lobby context
          if (typeof checkAllPlayersReady === 'function') checkAllPlayersReady();
        }
      });

      this.socket.on('game_started', function(data) {
          // console.log(`Received game_started event for game ${self.gameId}:`, data); // DEBUG REMOVED
          if (data.game_id == self.gameId) {
             window.location.href = `/game/${self.gameId}/play`;
         }
      });

      // Error handling
      this.socket.on('connect_error', (err) => {
        self.isConnecting = false; 
        console.error('SocketIO connection error:', err);
        self.connected = false; 
        self.onDisconnectCallbacks.forEach(cb => cb()); 
      });
      this.socket.on('connect_timeout', () => {
         self.isConnecting = false;
         self.connected = false;
        console.error('SocketIO connection timeout');
         self.onDisconnectCallbacks.forEach(cb => cb());
      });
      this.socket.on('error', (err) => {
        console.error('SocketIO error:', err);
        // Check if the error object has a message property and display it
        if (err && typeof err === 'object' && err.message) {
          alert(`Error: ${err.message}`); // Display the error message to the user
        } else if (typeof err === 'string') {
          alert(`Error: ${err}`); // Handle cases where the error might just be a string
        }
        // Optionally, add more sophisticated UI error display here later
      });

    } catch (err) {
      console.error('Failed to initialize SocketIO:', err);
      this.isConnecting = false;
    }
  },

  joinRoom: function(gameId) {
    // console.log(`joinRoom(${gameId}) called. State: connected=${this.connected}, hasJoinedRoom=${this.hasJoinedRoom}`); // DEBUG REMOVED
    if (gameId !== this.gameId) {
      // console.warn(`joinRoom: ID mismatch.`); // DEBUG REMOVED
      return;
    }
    if (this.connected && this.socket && !this.hasJoinedRoom) {
       // console.log(`joinRoom: Emitting join_game for ${this.gameId}.`); // DEBUG REMOVED
       this.socket.emit('join_game', {
         game_id: this.gameId,
         user_id: window.currentUserId
       });
       this.hasJoinedRoom = true; // Set flag AFTER emitting
     } else if (this.hasJoinedRoom) {
       // console.warn(`joinRoom: Already attempted join for this connection cycle. Skipping emit.`); // DEBUG REMOVED
     } else {
       // console.warn(`joinRoom: Not connected or socket not available. Cannot emit join_game.`); // DEBUG REMOVED
     }
  },

  emitPlayerReady: function() {
    // console.log(`emitPlayerReady called. State: connected=${this.connected}, gameId=${this.gameId}`); // DEBUG REMOVED
    if (this.gameId && this.connected && this.socket) {
      // console.log(`Emitting player_ready for game ${this.gameId}, user ${window.currentUserId}`); // DEBUG REMOVED
      this.socket.emit('player_ready', {
        game_id: this.gameId,
        user_id: window.currentUserId
      });
    } else {
      // console.warn(`Conditions not met to emit player_ready.`); // DEBUG REMOVED
    }
  },

  // onConnect method is no longer needed as we call setupListenersAndRequestState directly.
  // onConnect: function(callback) { ... }, 

  // Add onDisconnect method (keep if used elsewhere, or remove if not)
  onDisconnect: function(callback) {
     console.log("SocketClient: socketClient.onDisconnect method CALLED.");
     if (typeof callback === 'function') this.onDisconnectCallbacks.push(callback);
  },

  // Add disconnect method
  disconnect: function() {
     console.log(`SocketClient: socketClient.disconnect() called. Current gameId: ${this.gameId}`);
     if (this.socket) {
       console.log(`SocketClient: Disconnecting socket instance for game ${this.gameId}`);
       this.socket.disconnect();
       this.socket = null; 
     }
     this.connected = false;
     this.isConnecting = false;
     this.gameId = null;
     this.hasJoinedRoom = false; 
     // this.onConnectCallbacks = []; // No longer used
     this.onDisconnectCallbacks = []; // Keep for now
     hasSetupListenersForCurrentConnection = false; // Reset this flag too
     this.initialStateRequestedThisConnection = false;
     console.log(`SocketClient: State after disconnect: connected=${this.connected}, isConnecting=${this.isConnecting}`);
   }
};

// console.log("socketClient object created."); // DEBUG REMOVED

// --- Game State Update Handlers ---
// These functions are called by the event handlers inside socketClient.setupListenersAndRequestState

// Revised function to update all relevant UI parts from state
function updateGameState(state) {
    console.log("--- updateGameState received state:", JSON.stringify(state, null, 2)); // Re-enable for debugging

    // 1. Update Action Controls
    updateActionControls(state?.actions || []);

    // 2. Update Game Log / Visualization Area
    // Extract log and location safely
    const logToShow = state?.log || [];
    const locationToShow = state?.state?.location; // Access nested location
    updateGameLog(logToShow, locationToShow); // Call the revised log function

    // 3. Update Player Locations Display
    // Create a player_locations object using the current user's location
    const currentUserId = window.currentUserId;
    const currentLocation = state?.state?.location;
    let playerLocations = null;
    
    if (currentUserId && currentLocation) {
        // Create a simple mapping of the current user to their location
        playerLocations = {
            [currentUserId]: currentLocation
        };
        console.log("Created playerLocations object:", playerLocations);
    }
    updatePlayerLocationsDisplay(playerLocations);

    // 4. Update Visited Locations Display
    updateVisitedLocationsDisplay(state?.state?.visited_locations || []); // Corrected path to state.state.visited_locations

    // 5. Update Inventory Display
    // Log the full state.state object to see all available keys
    console.log("Full state.state object:", state?.state);
    
    // Extract inventory from inventory_changes.items_added
    let inventory = null;
    if (state?.state?.inventory_changes?.items_added) {
        inventory = state.state.inventory_changes.items_added;
        console.log("Inventory data found at path: state.state.inventory_changes.items_added");
    } else if (state?.state?.current_inventory) {
        inventory = state.state.current_inventory;
        console.log("Inventory data found at path: state.state.current_inventory");
    } else if (state?.state?.inventory) {
        inventory = state.state.inventory;
        console.log("Inventory data found at path: state.state.inventory");
    } else if (state?.inventory) {
        inventory = state.inventory;
        console.log("Inventory data found at path: state.inventory");
    } else {
        console.log("No inventory found in any expected path");
    }
    
    console.log("Inventory data:", inventory);
    updateInventoryDisplay(inventory); // Pass null/undefined if not found

    // 6. Update Total Cost Display
    if (typeof state?.total_cost !== 'undefined') {
        updateTotalCostDisplay(state.total_cost);
    }

    // 7. Update Game Status (Example - if needed)
    // const gameStatusDisplay = document.getElementById('gameStatusDisplay');
    // if (gameStatusDisplay && state?.status) {
    //     gameStatusDisplay.textContent = state.status;
    // }

    // 8. Update Plot Point Display (Already handled in event handlers, but could be centralized here)
    // const plotProgressDisplay = document.getElementById('plot-progress-display');
    // if (plotProgressDisplay) {
    //     if (typeof state?.completed_plot_points_display_count === 'number' && typeof state?.total_plot_points_display === 'number') {
    //         plotProgressDisplay.textContent = `Plot Points: ${state.completed_plot_points_display_count} / ${state.total_plot_points_display}`;
    //     } else {
    //         plotProgressDisplay.textContent = '';
    //     }
    // }
}

// --- UI Update Functions ---

// Revised function to update the combined log/narrative display in gameStateVisualization
function updateGameLog(log, currentLocation) {
    const visualizationArea = document.getElementById('gameStateVisualization');
    if (!visualizationArea) {
        console.error("gameStateVisualization element not found"); // Keep error
        return;
    }
    visualizationArea.innerHTML = ''; // Clear previous content

    // Add Current Location at the top
    const locationElement = document.createElement('p');
    locationElement.className = 'static-location fw-bold mb-3'; // Added styling classes
    locationElement.innerText = `Current Location: ${currentLocation || "Unknown"}`;
    visualizationArea.appendChild(locationElement);

    // Add separator
    visualizationArea.appendChild(document.createElement('hr'));

    // Add log entries
    if (log && log.length > 0) {
        console.log("Rendering log entries:", log.length, "entries");
        log.forEach((item, index) => { // Added index for debugging
            const logEntry = document.createElement('div');
            logEntry.classList.add('log-entry');
            let content = '';
            let type = 'unknown';

            if (typeof item === 'object' && item !== null && item.content) {
                content = item.content;
                type = item.type || 'unknown';
                console.log(`Log entry ${index}: type=${type}, content=${content.substring(0, 30)}...`);
            } else {
                content = String(item); // Ensure it's a string
                console.log(`Log entry ${index}: simple string content=${content.substring(0, 30)}...`);
            }

            logEntry.innerText = content; // Use innerText to prevent potential HTML injection

            if (type === "player") {
                logEntry.classList.add('log-entry-player');
            } else if (type === "ai") {
                logEntry.classList.add('log-entry-ai');
            } else if (type === "system") { // Add system message styling if needed
                 logEntry.classList.add('log-entry-system', 'text-muted', 'fst-italic');
            }
            visualizationArea.appendChild(logEntry);
        });
    } else {
        const noLogEntry = document.createElement('div');
        noLogEntry.className = 'log-entry text-muted';
        noLogEntry.innerText = 'No log entries yet.';
        visualizationArea.appendChild(noLogEntry);
    }

    // Scroll to the bottom
    visualizationArea.scrollTop = visualizationArea.scrollHeight;
}

// New function to append slash command responses to the game log
function appendSlashCommandResponseToLog(data) {
    const visualizationArea = document.getElementById('gameStateVisualization');
    if (!visualizationArea) {
        console.error("gameStateVisualization element not found for slash command response");
        return;
    }

    if (data && data.lines && data.lines.length > 0) {
        const headerEntry = document.createElement('div');
        headerEntry.classList.add('log-entry', 'log-entry-system', 'fw-bold'); // System styling, bold header
        headerEntry.innerText = data.header || `${data.command} response:`; // Use provided header or default
        visualizationArea.appendChild(headerEntry);

        data.lines.forEach(line => {
            const lineEntry = document.createElement('div');
            lineEntry.classList.add('log-entry', 'log-entry-system', 'ms-2'); // System styling, indented
            lineEntry.innerText = line;
            visualizationArea.appendChild(lineEntry);
        });
         visualizationArea.appendChild(document.createElement('hr')); // Add a separator after the response
    } else if (data && data.message) { // Handle simple message responses
        const messageEntry = document.createElement('div');
        messageEntry.classList.add('log-entry', 'log-entry-system');
        messageEntry.innerText = data.message;
        visualizationArea.appendChild(messageEntry);
        visualizationArea.appendChild(document.createElement('hr'));
    } else {
        console.warn("Received slash_command_response with no lines or message to display:", data);
    }
    visualizationArea.scrollTop = visualizationArea.scrollHeight;
}


// New function to update the total cost display
function updateTotalCostDisplay(cost) {
    const costElement = document.getElementById('totalCostDisplay'); // Need to add this ID to the HTML element
    if (costElement) {
        // Format cost to 4 decimal places
        costElement.textContent = `Cost: $${cost.toFixed(4)}`;
    } else {
        // console.warn("totalCostDisplay element not found."); // DEBUG REMOVED
    }
}

function updateActionControls(actions) {
    const actionControls = document.getElementById('actionControls');
     if (!actionControls) {
        // console.error("actionControls element not found"); // DEBUG REMOVED
        return;
    }
    actionControls.innerHTML = ''; // Clear previous actions
    if (actions && Array.isArray(actions)) {
        actions.forEach(action => {
            const button = document.createElement('button');
            button.className = 'btn btn-primary mb-2 w-100'; // Make buttons full width
            // TODO: Use a more descriptive property than 'name' if available
            button.innerText = typeof action === 'object' ? action.name || JSON.stringify(action) : action;
            button.onclick = () => socketClient.performAction(action); // Ensure calling the method
            actionControls.appendChild(button);
        });
    } else {
        // console.warn("No valid actions received to update controls."); // DEBUG REMOVED
        actionControls.innerHTML = '<p class="text-muted">No actions available.</p>';
    }
}

// New function to update Player Locations display
function updatePlayerLocationsDisplay(playerLocations) {
    // console.log("--- updatePlayerLocationsDisplay received:", JSON.stringify(playerLocations, null, 2)); // DEBUG REMOVED
    const displayElement = document.getElementById('playerLocationsDisplay');
    if (!displayElement) {
        console.error("playerLocationsDisplay element not found"); // Keep error for debugging
        return;
    }
    let html = '<ul class="list-unstyled mb-0">';
    // Access playerDetails globally (assuming it's set by play.html)
    const playerDetails = window.playerDetails || {};
    if (playerLocations && Object.keys(playerLocations).length > 0) {
        for (const [userId, location] of Object.entries(playerLocations)) {
            const details = playerDetails[userId];
            const displayName = details?.character_name || details?.username || `User ${userId}`;
            html += `<li>${displayName}: ${location || 'Unknown'}</li>`;
        }
    } else if (playerLocations === null) {
        html += '<li class="text-muted">Player location data not available from server.</li>';
    } else {
        html += '<li class="text-muted">No player location data.</li>';
    }
    html += '</ul>';
    displayElement.innerHTML = html;
}

// New function to update Visited Locations display
function updateVisitedLocationsDisplay(visitedLocations) {
    console.log("--- updateVisitedLocationsDisplay received:", JSON.stringify(visitedLocations, null, 2));
    const displayElement = document.getElementById('locationHistoryDisplay');
    if (!displayElement) {
        console.error("locationHistoryDisplay element not found"); // Keep error
        return;
    }
    let html = '<ul class="list-unstyled mb-0">';
    if (visitedLocations && visitedLocations.length > 0) {
        visitedLocations.forEach(location => {
            html += `<li>${location}</li>`;
        });
    } else {
        html += '<li class="text-muted">No locations visited yet.</li>';
    }
    html += '</ul>';
    displayElement.innerHTML = html;
    console.log("Visited locations display updated with HTML:", html);
}

// New function to update Inventory display
function updateInventoryDisplay(inventory) {
    console.log("--- updateInventoryDisplay received:", JSON.stringify(inventory, null, 2)); // Re-enable for debugging
    const displayElement = document.getElementById('inventoryDisplay');
    if (!displayElement) {
        console.error("inventoryDisplay element not found"); // Keep error
        return;
    }
    let html = '<ul class="list-unstyled mb-0">';
    
    // Handle different inventory data structures
    if (inventory === null || inventory === undefined) { 
        // Case 1: No inventory data
        html += '<li class="text-muted">Inventory data not available from server.</li>';
    } else if (Array.isArray(inventory) && inventory.length > 0) { 
        // Case 2: Array of items
        inventory.forEach(item => {
            if (typeof item === 'object' && item !== null && item.name) {
                html += `<li>${item.name}</li>`; // Object with name property
            } else {
                html += `<li>${item}</li>`; // String or other primitive
            }
        });
    } else if (typeof inventory === 'object' && inventory !== null && Object.keys(inventory).length > 0) {
        // Case 3: Object with key-value pairs (possibly a dictionary of items)
        for (const [key, value] of Object.entries(inventory)) {
            if (typeof value === 'object' && value !== null) {
                // If value is an object, try to extract a name or description
                const itemName = value.name || value.description || key;
                html += `<li>${itemName}</li>`;
            } else {
                // If value is a primitive, use the key as the item name
                html += `<li>${key}</li>`;
            }
        }
    } else {
        // Case 4: Empty inventory
        html += '<li class="text-muted">Inventory is empty.</li>';
    }
    
    html += '</ul>';
    displayElement.innerHTML = html;
}


// --- Action Emission ---

// This performAction will now be a method of socketClient and handle slash command differentiation
// function performAction(actionInputText) { // Becomes a method
socketClient.performAction = function(actionInputText) {
    const rawInput = actionInputText;
    const trimmedActionText = actionInputText ? actionInputText.trim() : "";

    // console.log(`[socketClient.mjs] socketClient.performAction START. Raw: "${rawInput}", Trimmed: "${trimmedActionText}"`);

    if (!trimmedActionText) {
        // console.log("[socketClient.mjs] socketClient.performAction: Trimmed text is empty. Exiting.");
        return;
    }

    const isSlashCommand = trimmedActionText.startsWith('/');
    // console.log(`[socketClient.mjs] socketClient.performAction: isSlashCommand = ${isSlashCommand} (checked on "${trimmedActionText}")`);

    if (isSlashCommand) {
        // console.log("[socketClient.mjs] Slash command DETECTED by socketClient.performAction:", trimmedActionText);
        const parts = trimmedActionText.substring(1).split(' ');
        const command = parts[0].toLowerCase();
        const args = parts.slice(1);
        
        // gameId needs to be accessible. Assuming it's set on socketClient or globally by play.html
        // For safety, let's try to get it from the DOM if socketClient.gameId isn't reliable here.
        const gameIdForEmit = socketClient.gameId || document.getElementById('gameTitle')?.dataset.gameId;
        const userIdForEmit = window.currentUserId || document.getElementById('gameTitle')?.dataset.userId;


        if (!gameIdForEmit) {
            // console.error("[socketClient.mjs] CRITICAL: gameIdForEmit is undefined for slash command."); // DEBUG REMOVED
            return; 
        }
        if (!userIdForEmit) {
            // console.error("[socketClient.mjs] CRITICAL: userIdForEmit is undefined for slash command."); // DEBUG REMOVED
            return;
        }

        if (socketClient.socket && socketClient.connected) {
            socketClient.socket.emit('slash_command', {
                game_id: gameIdForEmit,
                user_id: userIdForEmit,
                command: command,
                args: args
            });
            // console.log(`[socketClient.mjs] Emitted slash_command: ${command} with args: ${JSON.stringify(args)}`);
        } else {
            // console.error("[socketClient.mjs] socketClient not available/connected for slash_command emission."); // DEBUG REMOVED
        }
    } else {
        // console.log("[socketClient.mjs] Regular action DETECTED by socketClient.performAction:", trimmedActionText);
        const gameTitleElement = document.getElementById('gameTitle');
        if (!gameTitleElement) {
             // console.error("[socketClient.mjs] gameTitle element not found for regular action."); // DEBUG REMOVED
             return;
        }
        const game_id = gameTitleElement.dataset.gameId;
        const user_id = gameTitleElement.dataset.userId;
        
        if (socketClient.socket && socketClient.connected) {
            socketClient.socket.emit('player_action', {
                game_id: game_id,
                user_id: user_id,
                action: trimmedActionText
            });
            // console.log("[socketClient.mjs] Emitted player_action:", trimmedActionText);
        } else {
             // console.error("[socketClient.mjs] socketClient not available/connected for player_action emission."); // DEBUG REMOVED
        }
    }
    // Responsibility of clearing the input field should ideally be with the direct event handler in play.html
    // This method shouldn't assume it needs to clear it.
    // console.log("[socketClient.mjs] socketClient.performAction END.");
}; // End of performAction method

// --- State Rendering ---

// Removed renderCurrentScene function as it's integrated into updateGameLog

// Optional: Function to render other state details if needed elsewhere
// function renderOtherStateData(stateData) { ... }

// --- Initial Setup ---
// The functions requestInitialState and setupListenersAndRequestState are now methods of socketClient.
// The main connection logic is now more self-contained within socketClient.

const gameId = document.getElementById('gameTitle')?.dataset.gameId; 

if (gameId) {
    console.log("SocketClient: Initializing for gameId:", gameId);
    // The connect call will handle setting up listeners via its internal 'connect' event handler,
    // which now directly calls this.setupListenersAndRequestState.
    socketClient.connect(gameId); 
} else {
    console.error("SocketClient: Game ID not found in DOM, cannot initialize socket connection.");
}

// --- Custom Action Input Handler ---
const customActionInput = document.getElementById('customActionInput');
const submitCustomActionButton = document.getElementById('submitCustomAction');

if (customActionInput && submitCustomActionButton) {
    // Handle button click
    submitCustomActionButton.addEventListener('click', () => {
        const actionText = customActionInput.value.trim();
        if (actionText) {
            socketClient.performAction(actionText); // Ensure calling the method
            customActionInput.value = ''; // Clear the input field
        }
    });

    // Handle Enter key press in the input field
    customActionInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent default form submission if it were in a form
            submitCustomActionButton.click(); // Trigger the button click handler
        }
    });
} else {
    // console.error("Custom action input elements not found."); // DEBUG REMOVED
}

export default socketClient;
// console.log("socketClient exported."); // DEBUG REMOVED
