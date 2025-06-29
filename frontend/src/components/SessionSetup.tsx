import React, { useState, useEffect } from 'react';
import { ChefHat, Users, Play, Loader } from 'lucide-react';
import { api, ApiError } from '../api';

interface SessionSetupProps {
  onSessionStarted: () => void;
}

export const SessionSetup: React.FC<SessionSetupProps> = ({ onSessionStarted }) => {
  const [recipes, setRecipes] = useState<string[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<string>('');
  const [chefNames, setChefNames] = useState<string[]>(['Alice', 'Bob']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  
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
    </div>
  );
}; 