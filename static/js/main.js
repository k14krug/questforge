// QuestForge Main JavaScript File

const API_BASE_URL = '/api'; // Assuming your Flask app serves API under /api

// --- Token Management ---
function saveToken(token) {
    localStorage.setItem('questforge_token', token);
}

function getToken() {
    return localStorage.getItem('questforge_token');
}

function removeToken() {
    localStorage.removeItem('questforge_token');
}

function isLoggedIn() {
    return !!getToken();
}

// --- API Helper ---
async function fetchWithAuth(url, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await fetch(url, { ...options, headers });
    return response;
}


// --- Authentication UI ---
function updateNavAuthLinks() {
    const loginLink = document.getElementById('nav-login-link');
    const registerLink = document.getElementById('nav-register-link');
    const logoutLink = document.getElementById('nav-logout-link');

    if (isLoggedIn()) {
        if (loginLink) loginLink.style.display = 'none';
        if (registerLink) registerLink.style.display = 'none';
        if (logoutLink) logoutLink.style.display = 'inline';
    } else {
        if (loginLink) loginLink.style.display = 'inline';
        if (registerLink) registerLink.style.display = 'inline';
        if (logoutLink) logoutLink.style.display = 'none';
    }
}

// --- Login Handler ---
async function handleLoginFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const emailInput = form.querySelector('#email'); // Assuming login uses email
    const passwordInput = form.querySelector('#password');
    const errorElement = document.getElementById('login-error');

    if (!emailInput || !passwordInput) {
        console.error('Login form elements not found');
        if(errorElement) errorElement.textContent = 'Form fields missing. Please contact support.';
        if(errorElement) errorElement.style.display = 'block';
        return;
    }
    
    const email = emailInput.value;
    const password = passwordInput.value;

    if(errorElement) errorElement.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username_or_email: email, password: password }) // API expects username_or_email
        });

        const data = await response.json();

        if (response.ok) {
            saveToken(data.access_token);
            updateNavAuthLinks();
            window.location.href = '/dashboard'; // Redirect to dashboard or desired page
        } else {
            if(errorElement) errorElement.textContent = data.error || 'Login failed. Please check your credentials.';
            if(data.details && typeof data.details === 'string') {
                 if(errorElement) errorElement.textContent += ` ${data.details}`;
            } else if (data.details && typeof data.details === 'object') {
                const detailMessages = Object.values(data.details).join(' ');
                if(errorElement) errorElement.textContent += ` ${detailMessages}`;
            }
            if(errorElement) errorElement.style.display = 'block';
        }
    } catch (error) {
        console.error('Login error:', error);
        if(errorElement) errorElement.textContent = 'An unexpected error occurred. Please try again.';
        if(errorElement) errorElement.style.display = 'block';
    }
}

// --- Registration Handler ---
async function handleRegisterFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const usernameInput = form.querySelector('#username');
    const emailInput = form.querySelector('#email');
    const passwordInput = form.querySelector('#password');
    const confirmPasswordInput = form.querySelector('#confirm-password');
    const errorElement = document.getElementById('register-error');
    const successElement = document.getElementById('register-success');

    if (!usernameInput || !emailInput || !passwordInput || !confirmPasswordInput) {
        console.error('Register form elements not found');
        if(errorElement) errorElement.textContent = 'Form fields missing. Please contact support.';
        if(errorElement) errorElement.style.display = 'block';
        return;
    }

    const username = usernameInput.value;
    const email = emailInput.value;
    const password = password.value;
    const confirmPassword = confirmPasswordInput.value;

    if(errorElement) errorElement.style.display = 'none';
    if(successElement) successElement.style.display = 'none';

    if (password !== confirmPassword) {
        if(errorElement) errorElement.textContent = 'Passwords do not match.';
        if(errorElement) errorElement.style.display = 'block';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (response.ok) {
            if(successElement) successElement.textContent = 'Registration successful! Please login.';
            if(successElement) successElement.style.display = 'block';
            form.reset(); // Clear the form
            // Optionally redirect to login page after a delay or let user click
            // window.location.href = '/api/auth/login-page'; 
        } else {
            if(errorElement) errorElement.textContent = data.error || 'Registration failed.';
            if(data.details && typeof data.details === 'string') {
                if(errorElement) errorElement.textContent += ` ${data.details}`;
            } else if (data.details && typeof data.details === 'object') {
                const detailMessages = Object.values(data.details).join(' ');
                if(errorElement) errorElement.textContent += ` ${detailMessages}`;
            }
            if(errorElement) errorElement.style.display = 'block';
        }
    } catch (error) {
        console.error('Registration error:', error);
        if(errorElement) errorElement.textContent = 'An unexpected error occurred. Please try again.';
        if(errorElement) errorElement.style.display = 'block';
    }
}


// --- Logout Handler ---
async function handleLogout() {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/auth/logout`, { method: 'POST' });
        if (response.ok || response.status === 401 || response.status === 422) { // 401/422 if token already expired/invalid
            removeToken();
            updateNavAuthLinks();
            window.location.href = '/api/auth/login-page'; // Redirect to login page
        } else {
            const data = await response.json();
            console.error('Logout failed:', data.error || 'Unknown error');
            // Still remove token and redirect as a fallback
            removeToken();
            updateNavAuthLinks();
            window.location.href = '/api/auth/login-page';
        }
    } catch (error) {
        console.error('Logout error:', error);
        // Still remove token and redirect as a fallback
        removeToken();
        updateNavAuthLinks();
            window.location.href = '/api/auth/login-page';
    }
}

// --- Page Protection & Auth State Update ---
function checkAuthStatusAndProtect() {
    updateNavAuthLinks();
    const protectedPaths = ['/dashboard', '/', '/templates-page', '/games-page', '/play', '/games/create', '/games']; 
    const currentPath = window.location.pathname;

    const isProtected = protectedPaths.some(path => currentPath.startsWith(path));

    if (isProtected && !isLoggedIn()) {
        window.location.href = '/api/auth/login-page';
    }
}

// --- Template Management Page Functions ---
async function fetchTemplatesForCRUDPage() {
    const response = await fetchWithAuth(`${API_BASE_URL}/templates`);
    if (!response.ok) {
        console.error('Failed to fetch templates for management page:', response.status);
        const container = document.getElementById('templates-list-container');
        if (container) container.innerHTML = '<p>Error loading templates. Please try again.</p>';
        return [];
    }
    return response.json();
}

function renderTemplatesForCRUDPage(templates) {
    const container = document.getElementById('templates-list-container');
    if (!container) return;
    container.innerHTML = '';

    if (!templates || templates.length === 0) {
        container.innerHTML = '<p>You have not created any templates yet.</p>';
        return;
    }

    templates.forEach(template => {
        const templateCard = document.createElement('div');
        templateCard.className = 'card template-item';
        templateCard.dataset.templateId = template.id;
        const formatDate = (dateString) => dateString ? new Date(dateString).toLocaleDateString() : 'N/A';

        templateCard.innerHTML = `
            <h3>${template.name}</h3>
            <p><strong>Genre:</strong> ${template.genre || 'N/A'}</p>
            <p><small>Created: ${formatDate(template.created_at)}</small></p>
            <div class="template-item-actions action-buttons">
                <button class="btn btn-small btn-edit-template">Edit</button>
                <button class="btn btn-small btn-danger btn-delete-template">Delete</button>
            </div>
        `;
        container.appendChild(templateCard);

        templateCard.querySelector('.btn-edit-template').addEventListener('click', () => populateTemplateFormForEdit(template));
        templateCard.querySelector('.btn-delete-template').addEventListener('click', () => handleDeleteTemplate(template.id, template.name));
    });
}

function populateTemplateFormForEdit(template) {
    document.getElementById('template-id').value = template.id;
    document.getElementById('template-name').value = template.name;
    document.getElementById('template-genre').value = template.genre;
    document.getElementById('template-core-conflict').value = template.core_conflict;
    document.getElementById('template-world-description').value = template.world_description;
    document.getElementById('template-ai-gm-persona').value = template.ai_gm_persona;
    document.getElementById('template-core-skills').value = Array.isArray(template.core_skills) ? template.core_skills.join(', ') : '';

    document.getElementById('template-form-title').textContent = 'Edit Template';
    document.getElementById('template-form-section').style.display = 'block';
    document.getElementById('cancel-edit-btn').style.display = 'inline-block';
    document.getElementById('create-template-btn').style.display = 'none';
    document.getElementById('template-form').scrollIntoView({ behavior: 'smooth' });
}

async function handleTemplateFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const templateId = document.getElementById('template-id').value;
    const payload = {
        name: document.getElementById('template-name').value,
        genre: document.getElementById('template-genre').value,
        core_conflict: document.getElementById('template-core-conflict').value,
        world_description: document.getElementById('template-world-description').value,
        ai_gm_persona: document.getElementById('template-ai-gm-persona').value,
        core_skills: document.getElementById('template-core-skills').value.split(',').map(s => s.trim()).filter(Boolean),
    };

    const url = templateId ? `${API_BASE_URL}/templates/${templateId}` : `${API_BASE_URL}/templates`;
    const method = templateId ? 'PUT' : 'POST';

    try {
        const response = await fetchWithAuth(url, { method, body: JSON.stringify(payload) });
        const data = await response.json();
        const errorElement = document.getElementById('template-form-error');

        if (response.ok) {
            form.reset();
            document.getElementById('template-id').value = '';
            document.getElementById('template-form-section').style.display = 'none';
            document.getElementById('create-template-btn').style.display = 'inline-block';
            await loadAndDisplayTemplatesPageData();
        } else {
            errorElement.textContent = data.msg || data.error || 'An error occurred.';
            errorElement.style.display = 'block';
        }
    } catch (err) {
        console.error('Template form submission error:', err);
    }
}

async function handleDeleteTemplate(templateId, templateName) {
    if (confirm(`Are you sure you want to delete "${templateName}"?`)) {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/templates/${templateId}`, { method: 'DELETE' });
            if (response.ok) {
                await loadAndDisplayTemplatesPageData();
            } else {
                const data = await response.json();
                alert(`Failed to delete: ${data.msg || 'Unknown error'}`);
            }
        } catch (err) {
            console.error('Error deleting template:', err);
        }
    }
}

async function loadAndDisplayTemplatesPageData() {
    if (document.getElementById('templates-list-container')) {
        const templates = await fetchTemplatesForCRUDPage();
        renderTemplatesForCRUDPage(templates);
    }
}

// --- Game Management Page Functions ---
async function fetchGamesForCRUDPage() {
    const response = await fetchWithAuth(`${API_BASE_URL}/games`);
    if (!response.ok) {
        console.error('Failed to fetch games:', response.status);
        return [];
    }
    return response.json();
}

function renderGamesForCRUDPage(games) {
    const container = document.getElementById('games-list-container');
    if (!container) return;
    container.innerHTML = '';

    if (!games || games.length === 0) {
        container.innerHTML = '<p>You have no games. <a href="/games/create">Create one now!</a></p>';
        return;
    }

    games.forEach(game => {
        const gameCard = document.createElement('div');
        gameCard.className = 'card game-item';
        gameCard.dataset.gameId = game.id;

        const status = game.completed_at ? "Completed" : (game.started_at ? "In Progress" : "New");
        const campaignName = game.campaign_charter ? game.campaign_charter.campaign_name : 'Unnamed';
        const formatDate = (dateString) => dateString ? new Date(dateString).toLocaleDateString() : 'N/A';

        let actionButtonHtml = `<a href="/games/${game.id}/lobby" class="btn btn-small btn-primary">Open Lobby</a>`;
        if (status === "In Progress") {
            actionButtonHtml = `<a href="/play/${game.id}" class="btn btn-small btn-info">View Game</a>`;
        }

        gameCard.innerHTML = `
            <h3><a href="/play/${game.id}">${game.game_name} <small>(${campaignName})</small></a></h3>
            <p><strong>Status:</strong> ${status}</p>
            <p><small>Created: ${formatDate(game.created_at)}</small></p>
            <div class="game-item-actions action-buttons">
                ${actionButtonHtml}
                <button class="btn btn-small btn-danger btn-delete-game" data-game-id="${game.id}">Delete</button>
            </div>
        `;
        container.appendChild(gameCard);
        gameCard.querySelector('.btn-delete-game').addEventListener('click', () => handleDeleteGame(game.id, game.game_name));
    });
}

async function loadAndDisplayGamesPageData() {
    if (document.getElementById('games-list-container')) {
        const games = await fetchGamesForCRUDPage();
        renderGamesForCRUDPage(games);
    }
}

async function handleDeleteGame(gameId, gameName) {
    if (confirm(`Are you sure you want to delete "${gameName}"?`)) {
        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/games/${gameId}`, { method: 'DELETE' });
            if (response.ok) {
                await loadAndDisplayGamesPageData();
            } else {
                const data = await response.json();
                alert(`Failed to delete: ${data.msg || 'Unknown error'}`);
            }
        } catch (err) {
            console.error('Error deleting game:', err);
        }
    }
}

// --- Dashboard Data Loading ---
async function fetchActiveGames() {
    const response = await fetchWithAuth(`${API_BASE_URL}/games`);
    if (!response.ok) {
        console.error('Failed to fetch active games:', response.status);
        return [];
    }
    return response.json();
}

async function fetchMyTemplates() {
    const response = await fetchWithAuth(`${API_BASE_URL}/templates`);
    if (!response.ok) {
        console.error('Failed to fetch templates:', response.status);
        return [];
    }
    return response.json();
}

function renderGames(games) {
    const container = document.querySelector('#active-games .item-list');
    if (!container) return;
    container.innerHTML = '';

    if (!games || games.length === 0) {
        container.innerHTML = '<p>You have no active games. <a href="/games/create">Create one now!</a></p>';
        return;
    }

    games.forEach(game => {
        const gameCard = document.createElement('div');
        gameCard.className = 'card game-item';
        const campaignName = game.campaign_charter ? game.campaign_charter.campaign_name : 'Unnamed';
        const formatDate = (dateString) => dateString ? new Date(dateString).toLocaleDateString() : 'N/A';
        const status = game.completed_at ? "Completed" : (game.started_at ? "In Progress" : "New");

        gameCard.innerHTML = `
            <h3><a href="/play/${game.id}">${game.game_name} <small>(${campaignName})</small></a></h3>
            <p><strong>Status:</strong> ${status}</p>
            <p><small>Created: ${formatDate(game.created_at)}</small></p>
            <a href="/play/${game.id}" class="btn btn-small">View/Continue</a>
        `;
        container.appendChild(gameCard);
    });
}

function renderTemplates(templates) {
    const container = document.querySelector('#my-templates .item-list');
    if (!container) return;
    container.innerHTML = '';

    if (!templates || templates.length === 0) {
        container.innerHTML = '<p>You have not created any templates. <a href="/templates-page">Create one now!</a></p>';
        return;
    }

    templates.slice(0, 5).forEach(template => {
        const templateCard = document.createElement('div');
        templateCard.className = 'card template-item';
        const formatDate = (dateString) => dateString ? new Date(dateString).toLocaleDateString() : 'N/A';

        templateCard.innerHTML = `
            <h3><a href="/templates-page">${template.name}</a></h3>
            <p><strong>Genre:</strong> ${template.genre || 'N/A'}</p>
            <p><small>Created: ${formatDate(template.created_at)}</small></p>
        `;
        container.appendChild(templateCard);
    });
}

async function displayDashboardData() {
    const [games, templates] = await Promise.all([fetchActiveGames(), fetchMyTemplates()]);
    renderGames(games);
    renderTemplates(templates);
}

// --- Create Game Page Functions ---
async function populateTemplateSelector() {
    const templateSelect = document.getElementById('template-id');
    if (!templateSelect) return;

    try {
        const templates = await fetchMyTemplates();
        templateSelect.innerHTML = '<option value="" disabled selected>Select a campaign template</option>';
        templates.forEach(template => {
            const option = document.createElement('option');
            option.value = template.id;
            option.textContent = template.name;
            templateSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error populating template selector:', error);
    }
}

async function handleCreateGameFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const payload = {
        game_name: form.querySelector('#game-name').value,
        template_id: parseInt(form.querySelector('#template-id').value, 10),
        settings: {
            enable_visual_dice_roller: form.querySelector('#enable-visual-dice-roller').checked,
            expected_session_length_minutes: parseInt(form.querySelector('#expected-session-length').value, 10),
        }
    };

    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/games`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (response.ok) {
            window.location.href = `/games/${data.game_id}/lobby`;
        } else {
            document.getElementById('create-game-error').textContent = data.message || 'Failed to create game.';
        }
    } catch (err) {
        console.error('Error creating game:', err);
    }
}

// --- Play Page Functions ---
function renderInteractiveMap(mapData) {
    const mapContainer = document.getElementById('map-container');
    const actionInput = document.getElementById('action-input');

    if (!mapContainer || !actionInput) {
        console.error('Map container or action input not found');
        return;
    }

    mapContainer.innerHTML = ''; // Clear existing content

    if (mapData && mapData.nodes && Array.isArray(mapData.nodes)) {
        mapData.nodes.forEach(node => {
            const locationButton = document.createElement('button');
            locationButton.className = 'btn btn-link map-location';
            locationButton.textContent = node.name;
            locationButton.addEventListener('click', () => {
                actionInput.value = `Travel to ${node.name}`;
            });
            mapContainer.appendChild(locationButton);
        });
    } else {
        mapContainer.innerHTML = '<p>No map data available.</p>';
    }
}

async function initializePlayPage() { // Made async to support dynamic import
    const { gameId, currentUserId, gameCreatorId } = window.questForgeData;
    let isCurrentUserTurn = false;
    let currentPlayerId = null;

    const gameLog = document.getElementById('game-log');
    const actionInput = document.getElementById('action-input');
    const submitActionBtn = document.getElementById('submit-action-btn');
    const notYourTurnNotice = document.getElementById('not-your-turn-notice');
    const actionControls = document.getElementById('action-controls');
    const partyGrid = document.getElementById('party-grid');
    const npcGrid = document.getElementById('npc-grid');
    const addNpcBtn = document.getElementById('add-npc');
    const characterDetailsModal = document.getElementById('character-details-modal');
    const modalDetailsContent = document.getElementById('modal-details-content');
    const closeButton = characterDetailsModal.querySelector('.close-button');
    const turnNumberEl = document.getElementById('turn-number');
    const currentPlayerNameEl = document.getElementById('current-player-name');

    

    const socket = io();
    socket.on('connect', () => {
        console.log('Connected to server for game play');
        socket.emit('join_game_room', { game_id: gameId });
    });

    socket.on('game_state_update', updateGameState);
    socket.on('narrative_update', (data) => {
        const gameLog = document.getElementById('game-log');
        if (data.new_log_entries && Array.isArray(data.new_log_entries)) {
            data.new_log_entries.forEach(entry => {
                const logEntry = document.createElement('div');
                const entryType = entry.type ? entry.type.toLowerCase() : 'system';
                logEntry.className = `log-entry log-${entryType}`;
                if (entry.type === 'PLAYER_ACTION') {
                    logEntry.classList.add('log-player-action');
                }
                logEntry.innerHTML = `<span class="log-timestamp">${new Date(entry.timestamp).toLocaleTimeString()}</span>: ${entry.content}`;
                gameLog.appendChild(logEntry);
            });
            gameLog.scrollTop = gameLog.scrollHeight;
        }
    });

    socket.on('player_turn_changed', (data) => {
        const turnNumberEl = document.getElementById('turn-number');
        const currentPlayerNameEl = document.getElementById('current-player-name');
        turnNumberEl.textContent = data.new_turn_number;
        currentPlayerNameEl.textContent = data.current_player_name;

        const { currentUserId } = window.questForgeData;
        isCurrentUserTurn = (String(data.current_player_id) === String(currentUserId));
        const actionControls = document.getElementById('action-controls');
        const notYourTurnNotice = document.getElementById('not-your-turn-notice');
        actionControls.style.display = isCurrentUserTurn ? 'block' : 'none';
        notYourTurnNotice.style.display = isCurrentUserTurn ? 'none' : 'block';
    });

    socket.on('error', (data) => alert(`An error occurred: ${data.error}`));

    fetch(`/api/games/${gameId}/state`).then(res => res.json()).then(updateGameState).catch(console.error);

    function updateGameState(state) {
        turnNumberEl.textContent = state.turn_number;
        currentPlayerId = state.current_player_id;
        const currentPlayer = state.players.find(p => p.user_id === currentPlayerId);
        currentPlayerNameEl.textContent = currentPlayer ? currentPlayer.character_name : 'Unknown';

        gameLog.innerHTML = '';
        state.game_log.forEach(entry => {
            const logEntry = document.createElement('div');
            const entryType = entry.type ? entry.type.toLowerCase() : 'system';
            logEntry.className = `log-entry log-${entryType}`;
            logEntry.innerHTML = `<span class="log-timestamp">${new Date(entry.timestamp).toLocaleTimeString()}</span>: ${entry.content}`;
            gameLog.appendChild(logEntry);
        });
        gameLog.scrollTop = gameLog.scrollHeight;

        updateCharacterGrids(state.players, state.active_npcs);

        isCurrentUserTurn = (String(currentPlayerId) === String(currentUserId));
        actionControls.style.display = isCurrentUserTurn ? 'block' : 'none';
        notYourTurnNotice.style.display = isCurrentUserTurn ? 'none' : 'block';
        updateObjectivesAndLore(state.completed_objectives, state.discovered_lore_items);
        if (state.campaign_charter && state.campaign_charter.interactive_map_layout) {
            renderInteractiveMap(state.campaign_charter.interactive_map_layout);
        }
    }

    function updateObjectivesAndLore(completedObjectives, discoveredLore) {
        const objectivesList = document.getElementById('objectives-list');
        const loreDocuments = document.getElementById('lore-documents');
        const { objectives } = window.questForgeData; // The full list of objectives from the charter

        if (!objectivesList || !loreDocuments) return;

        objectivesList.innerHTML = '';
        if (objectives && objectives.length > 0) {
            objectives.forEach(obj => {
                const li = document.createElement('li');
                const isCompleted = completedObjectives && completedObjectives.includes(obj);
                li.textContent = obj;
                li.className = isCompleted ? 'completed' : 'active';
                if (isCompleted) {
                    li.textContent += ' (Completed)';
                }
                objectivesList.appendChild(li);
            });
        } else {
            objectivesList.innerHTML = '<li>No objectives defined yet.</li>';
        }

        loreDocuments.innerHTML = '';
        if (discoveredLore && discoveredLore.length > 0) {
            discoveredLore.forEach(lore => {
                const details = document.createElement('details');
                details.className = 'lore-item';
                const summary = document.createElement('summary');
                summary.textContent = lore.title || 'Unnamed Document';
                const content = document.createElement('div');
                content.className = 'lore-content';
                content.textContent = lore.content || 'No content.';
                details.appendChild(summary);
                details.appendChild(content);
                loreDocuments.appendChild(details);
            });
        } else {
            loreDocuments.innerHTML = '<p>No lore discovered yet.</p>';
        }
    }

    function updateCharacterGrids(players, npcs) {
        partyGrid.innerHTML = '';
        players.forEach(p => partyGrid.appendChild(createCharacterCard(p, 'player')));
        npcGrid.innerHTML = '';
        if (npcs) npcs.forEach(n => npcGrid.appendChild(createCharacterCard(n, 'npc')));
    }

    function createCharacterCard(character, type) {
        const card = document.createElement('div');
        card.className = 'character-card';
        card.dataset.id = character.id;
        const name = type === 'player' ? character.character_name : character.name;
        const imageUrl = character.character_portrait_url || '/static/images/default_npc.png';

        let detailsHtml = '';
        if (type === 'npc') {
            detailsHtml = `
                <p class="character-detail"><strong>Status:</strong> ${character.status || 'Unknown'}</p>
                <p class="character-detail"><strong>Location:</strong> ${character.location || 'Unknown'}</p>
            `;
        } else {
            const characterClass = character.character_sheet && character.character_sheet.class ? character.character_sheet.class : 'N/A';
            detailsHtml = `<p class="character-detail"><strong>Class:</strong> ${characterClass}</p>`;
        }

        card.innerHTML = `
            <div class="character-card-header">
                <img src="${imageUrl}" alt="Portrait of ${name}" class="character-portrait-thumb">
                <h3 class="character-name">${name}</h3>
            </div>
            <div class="character-details">
                ${detailsHtml}
            </div>
        `;
        card.addEventListener('click', () => showCharacterDetails(character, type));
        return card;
    }

    function showCharacterDetails(character, type) {
        let detailsHtml = '';
        if (type === 'npc') {
            detailsHtml = `
                <h3>${character.name}</h3>
                <p><strong>Description:</strong> ${character.description || 'N/A'}</p>
                <p><strong>Status:</strong> ${character.status || 'N/A'}</p>
                <p><strong>Location:</strong> ${character.location || 'N/A'}</p>
            `;
        } else {
            detailsHtml = `
                <h3>${character.character_name}</h3>
                <p><strong>Description:</strong> ${character.character_description || 'N/A'}</p>
                <p><strong>Class:</strong> ${character.character_sheet && character.character_sheet.class ? character.character_sheet.class : 'N/A'}</p>
                <h4>Character Sheet:</h4>
                <div class="character-sheet-details">
                    ${formatCharacterSheet(character.character_sheet)}
                </div>
            `;
        }
        modalDetailsContent.innerHTML = detailsHtml;
        characterDetailsModal.style.display = 'block';
    }

    function formatCharacterSheet(sheet) {
        if (!sheet) {
            return '<p>No character sheet available.</p>';
        }
        let html = '<ul>';
        for (const [key, value] of Object.entries(sheet)) {
            if (typeof value === 'object' && value !== null) {
                html += `<li><strong>${key}:</strong> ${formatCharacterSheet(value)}</li>`;
            } else {
                html += `<li><strong>${key}:</strong> ${value}</li>`;
            }
        }
        html += '</ul>';
        return html;
    }

    closeButton.onclick = () => characterDetailsModal.style.display = 'none';
    window.onclick = (event) => {
        if (event.target == characterDetailsModal) characterDetailsModal.style.display = 'none';
    };

    submitActionBtn.addEventListener('click', () => {
        const actionText = actionInput.value.trim();
        if (actionText && isCurrentUserTurn) {
            // Directly find the player from the already available state if possible
            // This depends on whether 'players' is available in the scope. 
            // Assuming it is not directly, we still need a way to get game_player_id.
            // The original implementation had a fetch, which is slow but gets the needed ID.
            // A better way would be to store the game_player_id when the page loads.

            // Let's check if we can get the player id from the global scope or data attribute.
            const { gameId, currentUserId, gameCreatorId, players } = window.questForgeData;
            const currentPlayer = players.find(p => String(p.user_id) === String(currentUserId));

            if (currentPlayer) {
                socket.emit('submit_player_action', { 
                    game_id: gameId, 
                    game_player_id: currentPlayer.id, 
                    action_text: actionText 
                });
                actionInput.value = '';
            } else {
                // Fallback to fetch if not available, though this indicates a design issue
                console.warn("Player data not available in window.questForgeData, falling back to fetch. This may cause delays.");
                fetch(`/api/games/${gameId}/state`).then(res => res.json()).then(state => {
                    const player = state.players.find(p => String(p.user_id) === String(currentUserId));
                    if (player) {
                        socket.emit('player_action', { game_id: gameId, game_player_id: player.id, action_text: actionText });
                        actionInput.value = '';
                    }
                });
            }
        }
    });

    addNpcBtn.addEventListener('click', () => {
        if (String(currentUserId) !== String(gameCreatorId)) return alert('Only the GM can add NPCs.');
        const npcName = prompt("Enter NPC name:");
        if (npcName) socket.emit('add_npc', { game_id: gameId, npc_data: { name: npcName } });
    });

    const diceContainer = document.getElementById('dice-container');
    if (diceContainer) {
        // Dynamically import DiceRoller
        const { default: DiceRoller } = await import('./dice.js');
        const diceRoller = new DiceRoller(diceContainer);
        const diceModal = document.getElementById('dice-modal');
        const diceResult = document.getElementById('dice-result');
        const closeBtn = diceModal.querySelector('.close');

        socket.on('dice_roll', (data) => {
            diceModal.style.display = 'block';
            diceRoller.rollToValue(data.value, data.dice_type || 'd20');
            setTimeout(() => {
                diceResult.textContent = `Result: ${data.value}`;
            }, 2000);
        });

        closeBtn.onclick = () => diceModal.style.display = "none";
    }
}

async function initializeLobbyPage() {
    const gameId = window.location.pathname.split('/')[2];
    if (!gameId) {
        console.error('Game ID not found in URL');
        return;
    }

    const socket = io();
    socket.on('connect', () => {
        console.log('Connected to server for lobby');
        socket.emit('join_game_room', { game_id: gameId });
    });

    socket.on('game_state_update', (state) => {
        console.log('game_state_update received in lobby', state);
        // The state object from the socket event has a 'players' property
        updateLobbyPlayers(state.players);
    });

    socket.on('game_starting', (data) => {
        console.log('Game starting, redirecting...', data);
        window.location.href = `/play/${data.game_id}`;
    });

    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/games/${gameId}`);
        if (!response.ok) {
            console.error('Failed to fetch game details for lobby');
            return;
        }
        const game = await response.json();
        console.log(game);

        document.getElementById('game-title').textContent = `Game Lobby: ${game.game_name}`;
        if (game.campaign_charter) {
            const charter = typeof game.campaign_charter === 'string' ? JSON.parse(game.campaign_charter) : game.campaign_charter;
            document.getElementById('gm-persona').textContent = charter.ai_gm_persona_for_campaign || '[GM Persona Placeholder]';
            document.getElementById('game-description').textContent = charter.core_conflict || '[Game Description Placeholder]';
        }

        if (game.game_players) {
            updateLobbyPlayers(game.game_players);
        }

        const readyUpButton = document.getElementById('ready-up-button');
        readyUpButton.addEventListener('click', async () => {
            try {
                const response = await fetchWithAuth(`${API_BASE_URL}/games/${gameId}/ready`, {
                    method: 'POST',
                });
                if (!response.ok) {
                    console.error('Failed to ready up');
                }
            } catch (error) {
                console.error('Error readying up:', error);
            }
        });

    } catch (error) {
        console.error('Error initializing lobby page:', error);
    }
}

function updateLobbyPlayers(players) {
    console.log('Updating lobby players with:', players); // Debugging line
    const playerList = document.getElementById('player-list');
    playerList.innerHTML = '';
    if (players && Array.isArray(players)) {
        players.forEach(player => {
            const playerItem = document.createElement('li');
            playerItem.className = 'list-group-item d-flex justify-content-between align-items-center';
            // Check if player.user exists before accessing username
            const username = player.user ? player.user.username : 'Unknown User';
            playerItem.innerHTML = `
                <span>${username} (${player.character_name}) - <span class="player-status">${player.ready_status ? 'Ready' : 'Not Ready'}</span></span>
            `;
            playerList.appendChild(playerItem);
        });
    }
}

// --- DOMContentLoaded Event Listener ---
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatusAndProtect();

    const currentPath = window.location.pathname;

    if (currentPath === '/dashboard' || currentPath === '/') {
        displayDashboardData();
    } else if (currentPath.startsWith('/templates-page')) {
        loadAndDisplayTemplatesPageData();
        const templateForm = document.getElementById('template-form');
        if (templateForm) templateForm.addEventListener('submit', handleTemplateFormSubmit);
    } else if (currentPath.startsWith('/games-page')) {
        loadAndDisplayGamesPageData();
    } else if (currentPath === '/games/create') {
        populateTemplateSelector();
        const createGameForm = document.getElementById('create-game-form');
        if (createGameForm) createGameForm.addEventListener('submit', handleCreateGameFormSubmit);
    } else if (currentPath.startsWith('/play/')) {
        initializePlayPage();
    } else if (currentPath.includes('/lobby')) {
        initializeLobbyPage();
    }

    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLoginFormSubmit);
    }

    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegisterFormSubmit);
    }

    const logoutLink = document.getElementById('nav-logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', (e) => {
            e.preventDefault();
            handleLogout();
        });
    }
});
