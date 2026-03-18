/**
 * Shared utility functions for the Password System (API Integrated)
 */

const PASSWORD_STORAGE_KEY = 'password_system_state';
const API_URL = ''; // Relative for same-origin

/**
 * Gets the current password state from localStorage (Local Cache)
 */
function getPasswordState() {
    const today = new Date().toLocaleDateString('pt-BR');
    
    const defaultState = {
        currentNumbers: { 'G': 0, 'P': 0, 'O': 0, 'E': 0 },
        queue: [],
        history: [],
        lastResetDate: today,
        counters: ['1', '2', '3'] // Default counters
    };
    
    try {
        const saved = localStorage.getItem(PASSWORD_STORAGE_KEY);
        if (!saved) return defaultState;
        
        const parsed = JSON.parse(saved);
        
        // Match today
        if (parsed.lastResetDate !== today) {
            savePasswordState(defaultState);
            return defaultState;
        }

        if (!parsed.currentNumbers) parsed.currentNumbers = defaultState.currentNumbers;
        if (!parsed.queue) parsed.queue = [];
        if (!parsed.history) parsed.history = [];
        if (!parsed.counters) parsed.counters = defaultState.counters;
        return parsed;
    } catch(e) {
        return defaultState;
    }
}

/**
 * Saves the current password state to localStorage
 */
function savePasswordState(state) {
    localStorage.setItem(PASSWORD_STORAGE_KEY, JSON.stringify(state));
}

/**
 * API: Issues a new ticket (used by Totem)
 */
async function issueTicket(type) {
    try {
        const response = await fetch(`${API_URL}/api/passwords`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: type })
        });
        const newTicket = await response.json();
        
        // Sync local queue (optional, we usually poll or broadcast)
        const state = getPasswordState();
        state.queue.push(newTicket);
        savePasswordState(state);
        
        return newTicket;
    } catch (e) {
        console.error("API Error:", e);
        // Fallback to local if API fails? For now, we want the DB to be the master.
        return null;
    }
}

/**
 * API: Calls a ticket (used by Admin)
 */
async function callTicketAPI(ticketId, guiche) {
    try {
        const response = await fetch(`${API_URL}/api/passwords/${ticketId}/call`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ guiche: guiche })
        });
        return await response.json();
    } catch (e) {
        console.error("API Error:", e);
        return null;
    }
}

/**
 * API: Get Queue
 */
async function getQueueAPI() {
    try {
        const response = await fetch(`${API_URL}/api/queue`);
        return await response.json();
    } catch (e) {
        return [];
    }
}

/**
 * API: Get History
 */
async function getHistoryAPI() {
    try {
        const response = await fetch(`${API_URL}/api/history`);
        return await response.json();
    } catch (e) {
        return [];
    }
}

/**
 * API: Get Stats
 */
async function getStatsAPI() {
    try {
        const response = await fetch(`${API_URL}/api/stats`);
        return await response.json();
    } catch (e) {
        return null;
    }
}

/**
 * Formats password number for display (e.g., G001)
 */
function formatPassword(data) {
    if (!data) return '---';
    const num = data.number || 0;
    return `${data.type}${num.toString().padStart(3, '0')}`;
}

/**
 * Helper to get type name
 */
function getTypeName(type) {
    const types = { 'G': 'Geral', 'P': 'Preferencial', 'O': 'Ouvidoria', 'E': 'Exame' };
    return types[type] || type;
}

/**
 * AUTH API
 */
async function apiLogin(username, password) {
    const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    if (!response.ok) throw new Error((await response.json()).error || 'Erro no login');
    return await response.json();
}

async function apiLogout() {
    await fetch(`${API_URL}/api/auth/logout`, { method: 'POST' });
}

async function apiGetMe() {
    const response = await fetch(`${API_URL}/api/auth/me`);
    if (!response.ok) return null;
    return await response.json();
}

/**
 * USERS API
 */
async function apiGetUsers() {
    const response = await fetch(`${API_URL}/api/users`);
    return await response.json();
}

async function apiCreateUser(userData) {
    const response = await fetch(`${API_URL}/api/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
    });
    if (!response.ok) throw new Error((await response.json()).error || 'Erro ao criar usuário');
    return await response.json();
}

async function apiDeleteUser(userId) {
    await fetch(`${API_URL}/api/users/${userId}`, { method: 'DELETE' });
}

/**
 * UPLOAD API
 */
async function apiUploadVideo(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_URL}/api/config/upload-video`, {
        method: 'POST',
        body: formData
    });
    if (!response.ok) throw new Error((await response.json()).error || 'Erro no upload');
    return await response.json();
}
