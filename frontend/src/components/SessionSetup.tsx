import React, { useState, useEffect } from 'react';
import { ChefHat, Users, Play, Loader, Plus, Edit, Link } from 'lucide-react';
import { api, ApiError } from '../api';

interface SessionSetupProps {
  onSessionStarted: () => void;
  onAddRecipe: () => void;
  onEditRecipe: (recipeId: string) => void;
}

export const SessionSetup: React.FC<SessionSetupProps> = ({ onSessionStarted, onAddRecipe, onEditRecipe }) => {
  const [recipes, setRecipes] = useState<string[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<string>('');
  const [chefNames, setChefNames] = useState<string[]>(['Alice', 'Bob']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [showUrlDialog, setShowUrlDialog] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [urlLoading, setUrlLoading] = useState(false);
  const [urlError, setUrlError] = useState('');
  const [urlRecipe, setUrlRecipe] = useState<any>(null);
  const [urlRecipeName, setUrlRecipeName] = useState('');
  const [showLlmFields, setShowLlmFields] = useState(false);
  const [llmModel, setLlmModel] = useState('gpt-4.1-nano');
  const [llmApiKey, setLlmApiKey] = useState('');

  useEffect(() => {
    loadRecipes();
  }, []);

  const loadRecipes = async () => {
    try {
      const availableRecipes = await api.getRecipes();
      setRecipes(availableRecipes);
      if (availableRecipes.length > 0) {
        setSelectedRecipe(availableRecipes[0]);
      }
    } catch (err) {
      setError('Failed to load recipes');
      console.error('Error loading recipes:', err);
    }
  };

  const addChef = () => {
    setChefNames([...chefNames, `Chef ${chefNames.length + 1}`]);
  };

  const removeChef = (index: number) => {
    if (chefNames.length > 1) {
      setChefNames(chefNames.filter((_, i) => i !== index));
    }
  };

  const updateChefName = (index: number, name: string) => {
    const newChefNames = [...chefNames];
    newChefNames[index] = name;
    setChefNames(newChefNames);
  };

  const startSession = async () => {
    if (!selectedRecipe || chefNames.length === 0) {
      setError('Please select a recipe and add at least one chef');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await api.startSession({
        recipe_id: selectedRecipe,
        chefs: chefNames
      });
      onSessionStarted();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError('A session is already running. Please reset the current session first.');
        } else {
          setError(`Failed to start session: ${err.message}`);
        }
      } else {
        setError('Failed to start session');
      }
      console.error('Error starting session:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUrlRecipe = async () => {
    setUrlLoading(true);
    setUrlError('');
    setUrlRecipe(null);
    try {
      const result = await api.getRecipeFromUrl(urlInput, llmModel, llmApiKey);
      if (result.success) {
        setUrlRecipe(result.recipe);
      } else {
        setUrlError(result.error || 'Failed to retrieve recipe from URL');
      }
    } catch (err) {
      setUrlError('Failed to retrieve recipe from URL');
      console.error('Error retrieving recipe from URL:', err);
    } finally {
      setUrlLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="card">
        <div className="text-center mb-8">
          <ChefHat className="w-16 h-16 text-primary-600 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Opticook</h1>
          <p className="text-gray-600">Smart cooking session scheduling</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        <div className="space-y-6">
          {/* Recipe Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Recipe
            </label>
            <select
              value={selectedRecipe}
              onChange={(e) => setSelectedRecipe(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              disabled={loading}
            >
              <option value="">Choose a recipe...</option>
              {recipes.map((recipe) => (
                <option key={recipe} value={recipe}>
                  {recipe.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </option>
              ))}
            </select>
            <div className="flex gap-3 mt-3">
              <button
                type="button"
                onClick={() => onEditRecipe(selectedRecipe)}
                className="flex-1 p-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={loading || !selectedRecipe || ['example_recipe', 'multi_task_recipe', 'cheesecake'].includes(selectedRecipe)}
                title={['example_recipe', 'multi_task_recipe', 'cheesecake'].includes(selectedRecipe) ? 'Cannot edit built-in recipes' : ''}
              >
                <Edit className="w-5 h-5" />
                Edit Recipe
              </button>
              <button
                type="button"
                onClick={onAddRecipe}
                className="flex-1 p-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg flex items-center justify-center gap-2 transition-colors"
                disabled={loading}
              >
                <Plus className="w-5 h-5" />
                Add New Recipe
              </button>
              <button
                type="button"
                onClick={() => setShowUrlDialog(true)}
                className="flex-1 p-3 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg flex items-center justify-center gap-2 transition-colors"
                disabled={loading}
              >
                <Link className="w-5 h-5" />
                Import Recipe from URL
              </button>
            </div>
          </div>

          {/* Chef Management */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Chefs
              </label>
              <button
                type="button"
                onClick={addChef}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                disabled={loading}
              >
                + Add Chef
              </button>
            </div>

            <div className="space-y-3">
              {chefNames.map((name, index) => (
                <div key={index} className="flex items-center gap-3">
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => updateChefName(index, e.target.value)}
                    className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Chef name"
                    disabled={loading}
                  />
                  {chefNames.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeChef(index)}
                      className="px-3 py-3 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                      disabled={loading}
                    >
                      Remove
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Start Button */}
          <button
            onClick={startSession}
            disabled={loading || !selectedRecipe || chefNames.length === 0}
            className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader className="w-5 h-5 animate-spin" />
                Starting Session...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Start Cooking Session
              </>
            )}
          </button>
        </div>
      </div>
      {/* URL Dialog */}
      {showUrlDialog && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 w-full max-w-lg relative">
            <button
              className="absolute top-2 right-2 text-gray-400 hover:text-gray-600"
              onClick={() => { setShowUrlDialog(false); setUrlInput(''); setUrlError(''); setUrlRecipe(null); setUrlRecipeName(''); }}
              aria-label="Close"
            >
              ×
            </button>
            <h2 className="text-xl font-bold mb-4">Import Recipe from URL</h2>
            <input
              type="text"
              className="w-full p-3 border border-gray-300 rounded-lg mb-3"
              placeholder="Paste recipe URL here..."
              value={urlInput}
              onChange={e => setUrlInput(e.target.value)}
              disabled={urlLoading}
            />
            <button
              className="btn-secondary w-full mb-3"
              onClick={() => setShowLlmFields(v => !v)}
              type="button"
            >
              {showLlmFields ? 'Hide LLM model and API key' : 'Add LLM model and API key'}
            </button>
            {showLlmFields && (
              <div className="mb-3">
                <input
                  type="text"
                  className="w-full p-2 border border-gray-300 rounded mb-2"
                  placeholder="LLM model (e.g., gpt-4.1-nano)"
                  value={llmModel}
                  onChange={e => setLlmModel(e.target.value)}
                  disabled={urlLoading}
                />
                <input
                  type="text"
                  className="w-full p-2 border border-gray-300 rounded"
                  placeholder="API key (optional)"
                  value={llmApiKey}
                  onChange={e => setLlmApiKey(e.target.value)}
                  disabled={urlLoading}
                />
              </div>
            )}
            <button
              className="btn-primary w-full mb-3"
              onClick={handleUrlRecipe}
              disabled={urlLoading || !urlInput}
            >
              {urlLoading ? <Loader className="w-5 h-5 animate-spin inline-block mr-2" /> : <Link className="w-5 h-5 inline-block mr-2" />}
              Fetch Recipe
            </button>
            {urlError && <div className="mb-2 text-red-600">{urlError}</div>}
            {urlRecipe && (
              <div className="mb-2 p-3 bg-green-50 border border-green-200 rounded">
                <div className="font-semibold mb-1">Recipe structure fetched!</div>
                <pre className="text-xs overflow-x-auto max-h-40">{JSON.stringify(urlRecipe, null, 2)}</pre>
                <div className="mt-2">
                  <input
                    type="text"
                    className="w-full p-2 border border-gray-300 rounded mb-2"
                    placeholder="Enter recipe name"
                    value={urlRecipeName}
                    onChange={e => setUrlRecipeName(e.target.value)}
                  />
                  <button
                    className="btn-primary w-full"
                    onClick={async () => {
                      if (!urlRecipeName.trim()) {
                        setUrlError('Please enter a recipe name.');
                        return;
                      }
                      try {
                        // Convert urlRecipe to the format expected by addRecipe
                        const instructions = (Array.isArray(urlRecipe) ? urlRecipe : urlRecipe.ci || urlRecipe.instructions || []).map((ci: any) => ({
                          aiList: (ci.ai || ci.aiList || []).map((ai: any) => ({
                            description: ai.description,
                            attention: ai.attention,
                            duration_seconds: ai.duration_seconds || ai.duration || 30
                          })),
                          dependencies: ci.dependencies || []
                        }));
                        await api.addRecipe({
                          recipe_name: urlRecipeName.trim(),
                          instructions
                        });
                        setShowUrlDialog(false);
                        setUrlInput('');
                        setUrlError('');
                        setUrlRecipe(null);
                        setUrlRecipeName('');
                        loadRecipes();
                      } catch (err) {
                        setUrlError('Failed to save recipe.');
                        console.error('Error saving imported recipe:', err);
                      }
                    }}
                  >
                    Save Recipe
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
