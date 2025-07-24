import { Session, StartSessionRequest, MarkDoneRequest, RefreshRequest, RecipeInfo, AddRecipeRequest } from './types';

const API_BASE = '/api/v1/session/current';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
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
  async getRecipes(): Promise<string[]> {
    return apiRequest<string[]>('/recipes');
  },

  // Get recipe details
  async getRecipe(recipeId: string): Promise<RecipeInfo[]> {
    return apiRequest<RecipeInfo[]>(`/recipes/${recipeId}`);
  },

  // Start a new session
  async startSession(request: StartSessionRequest): Promise<Session> {
    return apiRequest<Session>('/start', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Mark a task as done
  async markDone(request: MarkDoneRequest): Promise<Session> {
    return apiRequest<Session>('/done', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Refresh session state
  async refresh(request: RefreshRequest): Promise<Session> {
    return apiRequest<Session>('/refresh', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Get current session state
  async getState(): Promise<Session> {
    return apiRequest<Session>('/state');
  },

  // Reset session (dev only)
  async reset(): Promise<{}> {
    return apiRequest<{}>('/reset', {
      method: 'POST',
    });
  },

  // Send heartbeat for a chef
  async heartbeat(chefName: string): Promise<Session> {
    return apiRequest<Session>(`/heartbeat?chef=${encodeURIComponent(chefName)}`);
  },

  // Add a new recipe
  async addRecipe(request: AddRecipeRequest): Promise<{ message: string; recipe_id: string }> {
    const response = await fetch('/api/v1/recipes/add', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new ApiError(response.status, `API request failed: ${response.statusText}`);
    }

    return response.json();
  },

  // Update an existing recipe
  async updateRecipe(recipeId: string, request: AddRecipeRequest): Promise<{ message: string; recipe_id: string }> {
    const response = await fetch(`/api/v1/recipes/${recipeId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new ApiError(response.status, `API request failed: ${response.statusText}`);
    }

    return response.json();
  },

  // Delete a recipe
  async deleteRecipe(recipeId: string): Promise<void> {
    const response = await fetch(`/api/v1/recipes/${recipeId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new ApiError(response.status, `API request failed: ${response.statusText}`);
    }
  },

  // Add a chef to the current session
  async addChef(chefName: string, timestampSeconds: number): Promise<Session> {
    return apiRequest<Session>('/add-chef', {
      method: 'POST',
      body: JSON.stringify({
        chef_name: chefName,
        timestamp_seconds: timestampSeconds,
      }),
    });
  },

  // Remove a chef from the current session
  async removeChef(chefName: string, timestampSeconds: number): Promise<Session> {
    return apiRequest<Session>('/remove-chef', {
      method: 'POST',
      body: JSON.stringify({
        chef_name: chefName,
        timestamp_seconds: timestampSeconds,
      }),
    });
  },

  // Retrieve a recipe from a URL using the backend LLM pipeline
  async getRecipeFromUrl(url: string, llmModel: string = 'gpt-4.1-nano', apiKey?: string): Promise<{ success: boolean; recipe?: any; error?: string }> {
    const body: any = { url, llm_model: llmModel };
    if (apiKey) body.api_key = apiKey;
    const response = await fetch('/api/v1/recipes/from-url', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new ApiError(response.status, `API request failed: ${response.statusText}`);
    }
    return response.json();
  },
};

export { ApiError };
