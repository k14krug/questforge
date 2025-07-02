# Implementation Plan: The Information Panel

This document outlines the phased implementation for a **fully functional** tabbed "Information Panel" on the "Play" screen.

**Session Learnings & Key Context:**
- The primary route rendering the page is `play_page_route` in `app.py`.
- The `GameState` model uses `completed_objectives` and `discovered_lore_items`.
- Bootstrap CSS/JS is now correctly loaded from `layout.html`.
- The page layout in `play_page.html` and CSS in `style.css` are now corrected for a tabbed interface.

---

### **Phase 1-3: Initial Implementation (Completed)**

- **Summary:** The initial phases successfully set up the backend data pipeline, corrected the UI layout, fixed styling issues, and implemented the "Party & NPCs" and "Objectives & Lore" tabs. These two tabs are considered **feature-complete** based on the spec.

---

### **Phase 4: Interactive World Map**

**Goal:** Make the "World & Map" tab fully functional by displaying an interactive, node-based map based on the `campaign_charter`. Clicking a location will populate the main action input.

**1. Frontend - `play_page.html`:**
   - **File:** `/home/kkrug/projects/questforge/templates/play_page.html`
   - **Action:** Replace the placeholder content in the "World & Map" tab pane with a dedicated container for the map nodes.
   - **Details:**
     - **Locate:** The `<div class="tab-pane fade" id="world-map-content" ...>` element.
     - **Replace** its content with:
       ```html
       <div id="map-container" class="p-3">
           <!-- Interactive map nodes will be dynamically inserted here by main.js -->
       </div>
       ```

**2. Frontend - `static/js/main.js`:**
   - **File:** `/home/kkrug/projects/questforge/static/js/main.js`
   - **Action:** Add a new function to render the map and handle interactions.
   - **Details:**
     - Inside `initializePlayPage`, create a new function: `function renderInteractiveMap(mapData)`.
     - This function will:
       - Get the `#map-container` element.
       - Clear any existing content.
       - Check if `mapData` and `mapData.nodes` exist.
       - Loop through each `node` in `mapData.nodes`. For each node, create a clickable element (e.g., `<button class="btn btn-link map-location">${node.name}</button>`).
       - Add a `click` event listener to each button. When clicked, it will set the value of the `#action-input` textarea to `Travel to ${node.name}`.
       - Append the button to the `#map-container`.
     - Call this new function from within `initializePlayPage`, passing it the map data from the game object: `renderInteractiveMap(window.questForgeData.game.campaign_charter.interactive_map_layout);`.

---

### **Phase 5: Fully Functional Player Chat**

**Goal:** Implement a fully functional, real-time player-to-player chat system using Socket.IO.

**1. Backend - `app.py`:**
   - **File:** `/home/kkrug/projects/questforge/app.py`
   - **Action:** Create a new Socket.IO event handler to receive and broadcast chat messages.
   - **Details:**
     - Add the following handler to your `app.py`:
       ```python
       @socketio.on('send_chat_message')
       @jwt_required(optional=True) # Or your preferred auth method
       def handle_send_chat_message(data):
           current_user_id_str = get_jwt_identity()
           if not current_user_id_str:
               emit('error', {'message': 'Authentication required for chat.'})
               return

           game_id = data.get('game_id')
           message = data.get('message')
           if not game_id or not message:
               return # Ignore empty messages or requests

           player = GamePlayer.query.filter_by(game_id=game_id, user_id=int(current_user_id_str)).first()
           if not player:
               return # User is not a player in this game

           room_name = f"game_{game_id}"
           emit('new_chat_message', {
               'sender_name': player.character_name,
               'message': message,
               'timestamp': datetime.utcnow().isoformat()
           }, to=room_name)
       ```

**2. Frontend - `play_page.html`:**
   - **File:** `/home/kkrug/projects/questforge/templates/play_page.html`
   - **Action:** Replace the disabled placeholder chat UI with a functional one.
   - **Details:**
     - **Locate:** The `<div class="tab-pane fade" id="comms-chat-content" ...>` element.
     - **Replace** its content with the following, ensuring the `disabled` attributes are removed:
       ```html
       <div class="d-flex flex-column h-100 p-2">
           <div id="chat-log" class="flex-grow-1 border rounded p-2 mb-2" style="overflow-y: auto; height: 200px;">
               <!-- Chat messages will be appended here -->
           </div>
           <div class="d-flex">
               <input type="text" id="chat-input" class="form-control" placeholder="Type a message...">
               <button id="chat-send-btn" class="btn btn-primary ms-2">Send</button>
           </div>
       </div>
       ```

**3. Frontend - `static/js/main.js`:**
   - **File:** `/home/kkrug/projects/questforge/static/js/main.js`
   - **Action:** Add the client-side logic to send and receive chat messages.
   - **Details:**
     - **Sending:**
       - In `initializePlayPage`, get references to `#chat-input` and `#chat-send-btn`.
       - Add a `click` event listener to the send button. On click, it should get the text from the input, and if it's not empty, `socket.emit('send_chat_message', ...)` with the `gameId` and message. Then, clear the input.
     - **Receiving:**
       - Add a new socket listener: `socket.on('new_chat_message', (data) => { ... });`.
       - This listener will take the received `data`, create a new paragraph element (e.g., `<p><strong>[${data.sender_name}]:</strong> ${data.message}</p>`), append it to the `#chat-log`, and scroll the log to the bottom.