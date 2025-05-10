/**
 * SocketIO Client Manager for QuestForge (Simplified - No Classes)
 * Handles real-time communication with game server
 */

// console.log("Initializing socketClient (no class)..."); // DEBUG REMOVED

const socketClient = {
  socket: null,
  connected: false,
  isConnecting: false,
  gameId: null,
  hasJoinedRoom: false,
  onConnectCallbacks: [],
  onDisconnectCallbacks: [],

  connect: function(gameId) {
    // console.log(`socketClient.connect(${gameId}) called.`); // DEBUG REMOVED
    if (this.socket && this.connected && this.gameId === gameId) {
        // console.log(`Socket already connected for game ${gameId}.`); // DEBUG REMOVED
        // Trigger connect callbacks immediately if someone registers later
        setTimeout(() => this.onConnectCallbacks.forEach(cb => cb()), 0);
        return;
    }
    if (this.socket && this.gameId !== gameId) {
        // console.log(`Switching game context. Disconnecting from ${this.gameId}.`); // DEBUG REMOVED
        this.disconnect(); 
    }
    if (this.isConnecting) {
         // console.log("Connection attempt already in progress."); // DEBUG REMOVED
         return;
    }

    this.gameId = gameId;
    this.isConnecting = true;

    try {
      this.socket = io({ path: '/socket.io/' });
      const self = this;

      this.socket.on('connect', () => {
        // console.log("Socket connected event"); // DEBUG REMOVED
        self.connected = true;
        self.isConnecting = false;
        self.hasJoinedRoom = false;
        // console.log(`SocketIO connected successfully for game ${self.gameId}. Triggering connect callbacks.`); // DEBUG REMOVED
        self.onConnectCallbacks.forEach(function(cb) { if (typeof cb === 'function') cb(); });
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

  // Add onConnect method for compatibility with existing calls
  onConnect: function(callback) {
    if (typeof callback === 'function') {
        if (this.connected) setTimeout(callback, 0); // Call immediately if already connected
        else this.onConnectCallbacks.push(callback);
    }
  },

  // Add onDisconnect method
  onDisconnect: function(callback) {
     if (typeof callback === 'function') this.onDisconnectCallbacks.push(callback);
  },

  // Add disconnect method
  disconnect: function() {
     // console.log(`socketClient.disconnect() called. Current gameId: ${this.gameId}`); // DEBUG REMOVED
     if (this.socket) {
       // console.log(`Disconnecting socket instance for game ${this.gameId}`); // DEBUG REMOVED
       this.socket.disconnect();
       this.socket = null; 
     }
     this.connected = false;
     this.isConnecting = false;
     // console.log(`State after disconnect: connected=${this.connected}, isConnecting=${this.isConnecting}`); // DEBUG REMOVED
     this.gameId = null;
     this.hasJoinedRoom = false; 
     this.onConnectCallbacks = []; 
     this.onDisconnectCallbacks = [];
   }
};

// console.log("socketClient object created."); // DEBUG REMOVED

// --- Game State Update Handlers ---
// Listeners will be added inside the onReady callback

function updateGameState(state) {
    // console.log("Updating game state display with:", state);  // DEBUG REMOVED
    
    // Update Action Controls
    if (state && state.actions) {
        updateActionControls(state.actions);
    } else {
        updateActionControls([]); // Clear actions if none provided
    }

    // Update Game Log History Panel
    if (state && state.log) {
        updateGameLog(state.log); // Update the history panel
    } else {
        updateGameLog([]); // Clear log if none provided
    }

    // Update Main Game State Visualization (Current Scene)
    const gameStateVisualization = document.getElementById('gameStateVisualization');
    if (gameStateVisualization) {
        // Preserve or create a static location element
        let staticLocation = gameStateVisualization.querySelector('.static-location');
        if (!staticLocation) {
            staticLocation = document.createElement('p');
            staticLocation.className = 'static-location';
            // Prepend static location to existing content
            gameStateVisualization.prepend(staticLocation);
        }
        staticLocation.innerText = `Current Location: ${state.state.location || "Unknown"}`;

        // Update narrative section without overwriting the static location
        let narrativeElem = gameStateVisualization.querySelector('.current-scene');
        const narrative = (state && state.log && state.log.length > 0) ? state.log[state.log.length - 1] : "";
        const narrativeHtml = renderCurrentScene(narrative);
        if (narrativeElem) {
            narrativeElem.outerHTML = narrativeHtml;
        } else {
            gameStateVisualization.insertAdjacentHTML('beforeend', narrativeHtml);
        }
    } else {
        console.error("gameStateVisualization element not found");
    }

    // Optionally, render other state data if needed separately
    // renderOtherStateData(state.state); // Example if you have another function/area

    // Update total cost display if present in the update
    if (state && typeof state.total_cost !== 'undefined') {
        updateTotalCostDisplay(state.total_cost);
    }

    // Update Location History Display
    if (state && state.visited_locations) {
        updateLocationHistory(state.visited_locations);
    } else {
        updateLocationHistory([]); // Clear history if none provided
    }

    // Update Player Locations Display
    if (state && state.player_locations) {
        updatePlayerLocations(state.player_locations);
    } else {
        updatePlayerLocations({}); // Clear locations if none provided
    }
}

// --- UI Update Functions ---

function updateGameLog(log) {
    const gameLog = document.getElementById('gameLog');
    if (!gameLog) {
        // console.error("gameLog element not found"); // DEBUG REMOVED
        return;
    }
    gameLog.innerHTML = ''; // Clear previous logs
    log.forEach(item => {
        const logEntry = document.createElement('div');
        logEntry.classList.add('log-entry');
        if (typeof item === 'object' && item !== null && item.type) {
            logEntry.innerText = item.content;
            if (item.type === "player") {
                logEntry.classList.add('log-entry-player');
            } else if (item.type === "ai") {
                logEntry.classList.add('log-entry-ai');
            }
        } else {
            logEntry.innerText = item;
        }
        gameLog.appendChild(logEntry);
    });
    gameLog.scrollTop = gameLog.scrollHeight;
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

// New function to update the location history display
function updateLocationHistory(locations) {
    const locationHistoryDisplay = document.getElementById('locationHistoryDisplay');
    if (!locationHistoryDisplay) {
        // console.warn("locationHistoryDisplay element not found."); // DEBUG REMOVED
        return;
    }
    locationHistoryDisplay.innerHTML = ''; // Clear previous locations
    if (locations && Array.isArray(locations)) {
        if (locations.length > 0) {
            const ul = document.createElement('ul');
            ul.classList.add('list-unstyled', 'mb-0');
            locations.forEach(location => {
                const li = document.createElement('li');
                li.innerText = location;
                ul.appendChild(li);
            });
            locationHistoryDisplay.appendChild(ul);
        } else {
            locationHistoryDisplay.innerHTML = '<p class="text-muted mb-0">No locations visited yet.</p>';
        }
    } else {
        locationHistoryDisplay.innerHTML = '<p class="text-muted mb-0">Location history data not available.</p>';
    }
}

// New function to update the player locations display
function updatePlayerLocations(playerLocations) {
    const playerLocationsDisplay = document.getElementById('playerLocationsDisplay');
    if (!playerLocationsDisplay) {
        // console.warn("playerLocationsDisplay element not found."); // DEBUG REMOVED
        return;
    }
    playerLocationsDisplay.innerHTML = ''; // Clear previous locations
    if (playerLocations && typeof playerLocations === 'object') {
        const ul = document.createElement('ul');
        ul.classList.add('list-unstyled', 'mb-0');
        // Iterate over the playerLocations dictionary
        for (const userId in playerLocations) {
            if (playerLocations.hasOwnProperty(userId)) {
                const location = playerLocations[userId];
                const li = document.createElement('li');
                // TODO: Fetch username based on user ID if needed, for now just show ID and location
                li.innerText = `Player ${userId}: ${location}`;
                ul.appendChild(li);
            }
        }
        if (ul.children.length > 0) {
            playerLocationsDisplay.appendChild(ul);
        } else {
            playerLocationsDisplay.innerHTML = '<p class="text-muted mb-0">No player locations available.</p>';
        }
    } else {
        playerLocationsDisplay.innerHTML = '<p class="text-muted mb-0">Player location data not available.</p>';
    }
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

// New function to render just the current scene/narrative
function renderCurrentScene(narrative) {
    let html = '<div class="current-scene p-3">'; // Add padding
    if (narrative) {
        let content = "";
        if (typeof narrative === 'object' && narrative !== null && narrative.content) {
            content = narrative.content;
        } else {
            content = narrative;
        }
        html += `<p>${content}</p>`;
    } else {
        html += '<p class="text-muted">Waiting for the story to unfold...</p>';
    }
    html += '</div>';
    return html;
}

// Optional: Function to render other state details if needed elsewhere
// function renderOtherStateData(stateData) { ... }

// --- Initial Setup ---
const gameId = document.getElementById('gameTitle')?.dataset.gameId; // Get gameId early

if (gameId) {
    let initialStateRequested = false;

    // Define the function to request initial state
    const requestInitialState = () => {
        // Check socketClient.socket directly
        const userId = document.getElementById('gameTitle')?.dataset.userId; // Get user_id
        if (!initialStateRequested && socketClient.socket && socketClient.connected && userId) {
            // console.log(`Requesting initial state for game ${gameId} by user ${userId}`); // DEBUG REMOVED
            socketClient.socket.emit('request_state', { game_id: gameId, user_id: userId }); // Add user_id
            initialStateRequested = true;
        } else if (!initialStateRequested) {
             // console.log("Socket not ready/available when requestInitialState was called."); // DEBUG REMOVED
        }
    };

    // Setup listeners after connection
    const setupListenersAndRequestState = () => {
        // console.log("Play page: Socket connected. Setting up listeners and requesting initial state."); // DEBUG REMOVED

        if (!socketClient.socket) {
             // console.error("Play page: setupListenersAndRequestState called but socketClient.socket is not available! Aborting setup."); // DEBUG REMOVED
             return;
        }
        
        // Join the room for this game (using the object's method)
        socketClient.joinRoom(gameId); 

        // --- Setup Listeners ---
        // console.log("Play page: Setting up socket listeners."); // DEBUG REMOVED
        socketClient.socket.off('game_state_update'); // Clear potential old listeners
        socketClient.socket.off('game_state');

        socketClient.socket.on('game_state_update', (data) => {
            // console.log("Play page: Received game_state_update:", data); // DEBUG REMOVED
            updateGameState(data);
        });

        socketClient.socket.on('game_state', (state) => {
            // console.log("Play page: Received full game state:", state); // DEBUG REMOVED
            updateGameState(state);
        });

        socketClient.socket.on('game_concluded', (data) => {
            // console.log("Play page: Received game_concluded event:", data); // DEBUG REMOVED
            if (data.game_id === gameId) {
                // Update UI to show game is completed
                const gameStatusDisplay = document.getElementById('gameStatusDisplay'); // Assumes this element exists or will be added
                if (gameStatusDisplay) {
                    gameStatusDisplay.textContent = 'Status: Completed';
                } else {
                    // console.warn("gameStatusDisplay element not found. Cannot update status."); // DEBUG REMOVED
                }

                // Disable action input
                const customActionInput = document.getElementById('customActionInput');
                const submitCustomActionButton = document.getElementById('submitCustomAction');
                if (customActionInput) {
                    customActionInput.disabled = true;
                    customActionInput.placeholder = 'Campaign Complete';
                }
                if (submitCustomActionButton) {
                    submitCustomActionButton.disabled = true;
                }
                
                // Display conclusion message
                if (data.message) {
                    // Optionally, display this message in a more integrated way in the UI later
                    alert(data.message); 
                }

                // Potentially update action controls to show "Campaign Complete"
                updateActionControls(["Campaign Complete"]);
            }
        });

        // --- Request Initial State ---
        requestInitialState(); // Call the request function now that listeners are set up
    };

    // Register the setup function to run when the socket connects
    // Use the onConnectCallbacks array from the socketClient object
    socketClient.onConnectCallbacks.push(setupListenersAndRequestState);

    // Initiate the connection process for this game ID.
    // console.log("Calling socketClient.connect(gameId) for play page."); // DEBUG REMOVED
    socketClient.connect(gameId); // This will eventually trigger the callbacks in onConnectCallbacks

} else {
    // console.error("Game ID not found in DOM, cannot initialize socket connection."); // DEBUG REMOVED
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
