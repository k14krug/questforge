/**
 * SocketIO Client Manager for QuestForge (Simplified - No Classes)
 * Handles real-time communication with game server
 */

console.log("Initializing socketClient (no class)...");

const socketClient = {
  socket: null,
  connected: false,
  gameId: null,
  hasJoinedRoom: false,
  onConnectCallbacks: [], // Keep callbacks array for potential use
  onDisconnectCallbacks: [],

  connect: function(gameId) {
    console.log(`socketClient.connect(${gameId}) called.`);
    if (this.socket && this.connected && this.gameId === gameId) {
        console.log(`Socket already connected for game ${gameId}.`);
        // Trigger connect callbacks immediately if someone registers later
        setTimeout(() => this.onConnectCallbacks.forEach(cb => cb()), 0);
        return;
    }
    if (this.socket && this.gameId !== gameId) {
        console.log(`Switching game context. Disconnecting from ${this.gameId}.`);
        this.disconnect(); 
    }
    if (this.isConnecting) {
         console.log("Connection attempt already in progress.");
         return;
    }

    this.gameId = gameId;
    this.isConnecting = true;

    try {
      this.socket = io({ path: '/socket.io/' });
      const self = this; // Use self for clarity inside listeners

      this.socket.on('connect', function() {
        console.log("Socket connected event");
        self.connected = true;
        self.isConnecting = false;
        self.hasJoinedRoom = false;
        console.log(`SocketIO connected successfully for game ${self.gameId}. Triggering connect callbacks.`);
        // Trigger connect callbacks
        self.onConnectCallbacks.forEach(function(cb) { cb(); });
      });

      this.socket.on('disconnect', function(reason) {
        console.log(`Socket disconnected: ${reason}`);
        const wasConnected = self.connected;
        self.connected = false;
        self.isConnecting = false;
        self.hasJoinedRoom = false;
        if (wasConnected) {
            self.onDisconnectCallbacks.forEach(function(cb) { cb(); });
        }
      });

      // Add other necessary listeners back
      this.socket.on('player_list', function(data) {
         console.log(`Received player_list event for game ${self.gameId}:`, data);
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
          console.log(`Received player_joined event for game ${self.gameId}:`, data);
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
          console.log(`Received player_left event for game ${self.gameId}:`, data);
          const playerList = document.getElementById('player-list'); 
          if (playerList && data && data.user_id) {
             const playerItem = playerList.querySelector(`li[data-user-id="${data.user_id}"]`);
             if (playerItem) playerItem.remove();
             if (typeof checkAllPlayersReady === 'function') checkAllPlayersReady();
         }
      });

      this.socket.on('player_status_update', function(data) {
        console.log(`Received player_status_update event:`, data);
        if (data && data.user_id && typeof data.is_ready !== 'undefined') {
          const event = new CustomEvent('playerStatusUpdate', { detail: { userId: data.user_id, isReady: data.is_ready } });
          console.log(`Dispatching playerStatusUpdate event for userId=${data.user_id}, isReady=${data.is_ready}`);
          window.dispatchEvent(event);
          // Also call checkAllPlayersReady directly if needed in lobby context
          if (typeof checkAllPlayersReady === 'function') checkAllPlayersReady();
        }
      });

      this.socket.on('game_started', function(data) {
          console.log(`Received game_started event for game ${self.gameId}:`, data);
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
      });

    } catch (err) {
      console.error('Failed to initialize SocketIO:', err);
      this.isConnecting = false;
    }
  },

  joinRoom: function(gameId) {
    console.log(`joinRoom(${gameId}) called. State: connected=${this.connected}, hasJoinedRoom=${this.hasJoinedRoom}`);
    if (gameId !== this.gameId) {
      console.warn(`joinRoom: ID mismatch.`);
      return;
    }
    if (this.connected && this.socket && !this.hasJoinedRoom) {
       console.log(`joinRoom: Emitting join_game for ${this.gameId}.`);
       this.socket.emit('join_game', {
         game_id: this.gameId,
         user_id: window.currentUserId
       });
       this.hasJoinedRoom = true; // Set flag AFTER emitting
     } else if (this.hasJoinedRoom) {
       console.warn(`joinRoom: Already attempted join for this connection cycle. Skipping emit.`);
     } else {
       console.warn(`joinRoom: Not connected or socket not available. Cannot emit join_game.`);
     }
  },

  emitPlayerReady: function() {
    console.log(`emitPlayerReady called. State: connected=${this.connected}, gameId=${this.gameId}`);
    if (this.gameId && this.connected && this.socket) {
      console.log(`Emitting player_ready for game ${this.gameId}, user ${window.currentUserId}`);
      this.socket.emit('player_ready', {
        game_id: this.gameId,
        user_id: window.currentUserId
      });
    } else {
      console.warn(`Conditions not met to emit player_ready.`);
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
     console.log(`socketClient.disconnect() called. Current gameId: ${this.gameId}`);
     if (this.socket) {
       console.log(`Disconnecting socket instance for game ${this.gameId}`);
       this.socket.disconnect();
       this.socket = null; 
     }
     this.connected = false;
     this.isConnecting = false;
     console.log(`State after disconnect: connected=${this.connected}, isConnecting=${this.isConnecting}`);
     this.gameId = null;
     this.hasJoinedRoom = false; 
     this.onConnectCallbacks = []; 
     this.onDisconnectCallbacks = [];
   }
};

console.log("socketClient object created.");
export default socketClient;
console.log("socketClient exported.");
