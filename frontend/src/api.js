const API_BASE = '/api/v1/session/current';

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new ApiError(response.status, `API request failed: ${response.statusText}`);
  }

  return response.json();
}

export const api = {
  // Get available recipes
  async getRecipes() {
    return apiRequest('/recipes');
  },

  // Get recipe details
  async getRecipe(recipeId) {
    return apiRequest(`/recipes/${recipeId}`);
  },

  // Start a new session
  async startSession(request) {
    return apiRequest('/start', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Mark a task as done
  async markDone(request) {
    return apiRequest('/done', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Refresh session state
  async refresh(request) {
    return apiRequest('/refresh', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Get current session state
  async getState() {
    return apiRequest('/state');
  },

  // Reset session (dev only)
  async reset() {
    return apiRequest('/reset', {
      method: 'POST',
    });
  },

  // Send heartbeat for a chef
  async heartbeat(chefName) {
    return apiRequest(`/heartbeat?chef=${encodeURIComponent(chefName)}`);
  },
};

export { ApiError }; 