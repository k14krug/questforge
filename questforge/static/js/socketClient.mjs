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
              // Use a custom modal or message box instead of alert()
              // For now, a simple console log as a placeholder for a custom UI
              console.warn("ALERT (Implement custom UI):", data.newly_completed_plot_point_message);
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
          // Use a custom modal or message box instead of alert()
          // For now, a simple console log as a placeholder for a custom UI
          console.warn(`Error: ${err.message}`); 
        } else if (typeof err === 'string') {
          // Use a custom modal or message box instead of alert()
          console.warn(`Error: ${err}`); 
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

  onDisconnect: function(callback) {
     console.log("SocketClient: socketClient.onDisconnect method CALLED.");
     if (typeof callback === 'function') this.onDisconnectCallbacks.push(callback);
  },

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
     this.onDisconnectCallbacks = [];
     hasSetupListenersForCurrentConnection = false;
     this.initialStateRequestedThisConnection = false;
     console.log(`SocketClient: State after disconnect: connected=${this.connected}, isConnecting=${this.isConnecting}`);
   }
};

// --- Game State Update Handlers ---

function updateGameState(packet) {
    console.log("--- updateGameState received state:", JSON.stringify(packet, null, 2));

    updateActionControls(packet?.actions || []);
    updateGameLog(packet); // This function will now handle all log display
    updatePlayerLocationsDisplay(packet?.state?.player_locations || null);
    updateVisitedLocationsDisplay(packet?.state?.visited_locations || []);
    updateInventoryDisplay(packet?.state?.inventory || null);

    if (typeof packet?.total_cost !== 'undefined') {
        updateTotalCostDisplay(packet.total_cost);
    }
}

function updateGameLog(packet) {
    const gameStateVisualization = document.getElementById('gameStateVisualization');
    if (!gameStateVisualization) return;

    gameStateVisualization.innerHTML = ''; // Clear existing content

    // Ensure necessary data exists
    if (!packet || (!packet.latest_ai_response && (!Array.isArray(packet.player_commands) || packet.player_commands.length === 0) && (!Array.isArray(packet.historical_summary) || packet.historical_summary.length === 0))) {
        const noLogMessage = document.createElement('p');
        noLogMessage.className = 'text-muted mb-0';
        noLogMessage.textContent = 'No game log available yet.';
        gameStateVisualization.appendChild(noLogMessage);
        return;
    }

    const latestAiResponse = packet.latest_ai_response || '';
    const historicalSummary = Array.isArray(packet.historical_summary) ? packet.historical_summary : [];
    const playerCommands = Array.isArray(packet.player_commands) ? packet.player_commands : [];
    const playerDisplayMap = packet.player_display_map || {};

    // 1. Add Latest AI Response (verbose)
    if (latestAiResponse) {
        const latestAiHeader = document.createElement('h6');
        latestAiHeader.textContent = 'Latest AI Response';
        latestAiHeader.className = 'mt-2 mb-1'; // Bootstrap margin classes
        gameStateVisualization.appendChild(latestAiHeader);

        const latestAiDiv = document.createElement('div');
        latestAiDiv.className = 'log-entry log-entry-ai-latest'; // Use a specific class for latest
        latestAiDiv.style.whiteSpace = 'pre-wrap'; // Preserve formatting
        // Use CSS for background/padding/border-radius
        latestAiDiv.textContent = latestAiResponse;
        gameStateVisualization.appendChild(latestAiDiv);
    }

    // 2. Add Separator if there's both latest AI and historical log
    if (latestAiResponse && (historicalSummary.length > 0 || playerCommands.length > 0)) {
        const hr = document.createElement('hr');
        gameStateVisualization.appendChild(hr);
    }

    // 3. Add Interaction Log Header
    if (historicalSummary.length > 0 || playerCommands.length > 0) {
        const historyHeader = document.createElement('h6');
        historyHeader.textContent = 'Interaction Log';
        historyHeader.className = 'mt-2 mb-1'; // Bootstrap margin classes
        gameStateVisualization.appendChild(historyHeader);

        // 4. Add Historical Summaries and Player Commands (interleaved, reverse chronological)
        // Assuming playerCommands and historicalSummary have the same length and correspond to turns
        const logLength = Math.min(playerCommands.length, historicalSummary.length); // Use min length just in case
        for (let i = logLength - 1; i >= 0; i--) {
            const cmd = playerCommands[i];
            const summaryText = historicalSummary[i];

            // Add Player Command
            if (cmd && cmd.content) {
                const playerId = cmd.user_id;
                const playerName = playerDisplayMap[playerId] || 'Unknown Player';
                const playerDiv = document.createElement('div');
                playerDiv.className = 'log-entry log-entry-player';

                const identifierSpan = document.createElement('span');
                identifierSpan.className = 'log-player-identifier';
                identifierSpan.textContent = playerName + ': ';
                playerDiv.appendChild(identifierSpan);

                const actionSpan = document.createElement('span');
                actionSpan.textContent = cmd.content;
                playerDiv.appendChild(actionSpan);

                gameStateVisualization.appendChild(playerDiv);
            }

            // Add AI Summary
            if (summaryText) {
                const summaryDiv = document.createElement('div');
                summaryDiv.className = 'log-entry log-entry-summary'; // Specific class for summary
                summaryDiv.textContent = summaryText;
                gameStateVisualization.appendChild(summaryDiv);
            }
        }
    } else if (!latestAiResponse) { // If no latest AI response and no historical log
        const noLogMessage = document.createElement('p');
        noLogMessage.className = 'text-muted mb-0';
        noLogMessage.textContent = 'No game log available yet.';
        gameStateVisualization.appendChild(noLogMessage);
    }

    // Scroll to the bottom
    gameStateVisualization.scrollTop = gameStateVisualization.scrollHeight;
}

function appendSlashCommandResponseToLog(data) {
    const gameStateVisualization = document.getElementById('gameStateVisualization');
    if (!gameStateVisualization) return;

    if (data && data.lines && data.lines.length > 0) {
        const headerEntry = document.createElement('div');
        headerEntry.classList.add('log-entry', 'log-entry-system', 'fw-bold');
        headerEntry.innerText = data.header || `${data.command} response:`;
        gameStateVisualization.appendChild(headerEntry);

        data.lines.forEach(line => {
            const lineEntry = document.createElement('div');
            lineEntry.classList.add('log-entry', 'log-entry-system', 'ms-2');
            lineEntry.innerText = line;
            gameStateVisualization.appendChild(lineEntry);
        });
        gameStateVisualization.appendChild(document.createElement('hr'));
    } else if (data && data.message) {
        const messageEntry = document.createElement('div');
        messageEntry.classList.add('log-entry', 'log-entry-system');
        messageEntry.innerText = data.message;
        gameStateVisualization.appendChild(messageEntry);
        gameStateVisualization.appendChild(document.createElement('hr'));
    }
    gameStateVisualization.scrollTop = gameStateVisualization.scrollHeight;
}

function updateTotalCostDisplay(cost) {
    const costElement = document.getElementById('totalCostDisplay');
    if (costElement) {
        costElement.textContent = `Cost: $${cost.toFixed(4)}`;
    }
}

function updateActionControls(actions) {
    const actionControls = document.getElementById('actionControls');
    if (!actionControls) return;

    actionControls.innerHTML = '';
    if (actions && Array.isArray(actions)) {
        actions.forEach(action => {
            const button = document.createElement('button');
            button.className = 'btn btn-primary mb-2 w-100';
            button.innerText = typeof action === 'object' ? action.name || JSON.stringify(action) : action;
            button.onclick = () => socketClient.performAction(action);
            actionControls.appendChild(button);
        });
    } else {
        actionControls.innerHTML = '<p class="text-muted">No actions available.</p>';
    }
}

function updatePlayerLocationsDisplay(playerLocations) {
    const displayElement = document.getElementById('playerLocationsDisplay');
    if (!displayElement) return;

    let html = '<ul class="list-unstyled mb-0">';
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

function updateVisitedLocationsDisplay(visitedLocations) {
    const displayElement = document.getElementById('locationHistoryDisplay');
    if (!displayElement) return;

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
}

function updateInventoryDisplay(inventory) {
    const displayElement = document.getElementById('inventoryDisplay');
    if (!displayElement) return;

    let html = '<ul class="list-unstyled mb-0">';
    if (inventory === null || inventory === undefined) {
        html += '<li class="text-muted">Inventory data not available from server.</li>';
    } else if (Array.isArray(inventory) && inventory.length > 0) {
        inventory.forEach(item => {
            if (typeof item === 'object' && item !== null && item.name) {
                html += `<li>${item.name}</li>`;
            } else {
                html += `<li>${item}</li>`;
            }
        });
    } else if (typeof inventory === 'object' && inventory !== null && Object.keys(inventory).length > 0) {
        for (const [key, value] of Object.entries(inventory)) {
            if (typeof value === 'object' && value !== null) {
                const itemName = value.name || value.description || key;
                html += `<li>${itemName}</li>`;
            } else {
                html += `<li>${key}</li>`;
            }
        }
    } else {
        html += '<li class="text-muted">Inventory is empty.</li>';
    }
    html += '</ul>';
    displayElement.innerHTML = html;
}

socketClient.performAction = function(actionInputText) {
    const rawInput = actionInputText;
    const trimmedActionText = actionInputText ? actionInputText.trim() : "";

    if (!trimmedActionText) {
        return;
    }

    const isSlashCommand = trimmedActionText.startsWith('/');

    if (isSlashCommand) {
        const parts = trimmedActionText.substring(1).split(' ');
        const command = parts[0].toLowerCase();
        const args = parts.slice(1);

        const gameIdForEmit = socketClient.gameId || document.getElementById('gameTitle')?.dataset.gameId;
        const userIdForEmit = window.currentUserId || document.getElementById('gameTitle')?.dataset.userId;

        if (!gameIdForEmit || !userIdForEmit) {
            return;
        }

        if (socketClient.socket && socketClient.connected) {
            socketClient.socket.emit('slash_command', {
                game_id: gameIdForEmit,
                user_id: userIdForEmit,
                command: command,
                args: args
            });
        }
    } else {
        const gameTitleElement = document.getElementById('gameTitle');
        if (!gameTitleElement) {
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
        }
    }
};

const gameId = document.getElementById('gameTitle')?.dataset.gameId; 

if (gameId) {
    console.log("SocketClient: Initializing for gameId:", gameId);
    socketClient.connect(gameId); 
} else {
    console.error("SocketClient: Game ID not found in DOM, cannot initialize socket connection.");
}

const customActionInput = document.getElementById('customActionInput');
const submitCustomActionButton = document.getElementById('submitCustomAction');

if (customActionInput && submitCustomActionButton) {
    submitCustomActionButton.addEventListener('click', () => {
        const actionText = customActionInput.value.trim();
        if (actionText) {
            socketClient.performAction(actionText);
            customActionInput.value = '';
        }
    });

    customActionInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            submitCustomActionButton.click();
        }
    });
}

export default socketClient;
