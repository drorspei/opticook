import React, { useState, useEffect } from 'react';
import { Plus, X, Save, ArrowLeft, Trash2 } from 'lucide-react';
import { api, ApiError } from '../api';

interface AtomicInstructionForm {
  description: string;
  attention: boolean;
  duration_seconds: number;
}

interface CookingInstructionForm {
  aiList: AtomicInstructionForm[];
  dependencies: number[];
}

interface AddRecipeProps {
  onBack: () => void;
  onRecipeAdded: () => void;
  editRecipeId?: string | null;
}

export const AddRecipe: React.FC<AddRecipeProps> = ({ onBack, onRecipeAdded, editRecipeId }) => {
  const [recipeName, setRecipeName] = useState('');
  const [instructions, setInstructions] = useState<CookingInstructionForm[]>([
    {
      aiList: [{ description: '', attention: true, duration_seconds: 30 }],
      dependencies: []
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    if (editRecipeId) {
      // Load existing recipe for editing
      const loadRecipe = async () => {
        try {
          const recipeData = await api.getRecipe(editRecipeId);
          setRecipeName(editRecipeId);
          
          const formattedInstructions: CookingInstructionForm[] = recipeData.map(inst => ({
            aiList: inst.aiList.map(ai => ({
              description: ai.description,
              attention: ai.attention,
              duration_seconds: ai.duration_seconds
            })),
            dependencies: inst.dependencies || []
          }));
          
          setInstructions(formattedInstructions);
        } catch (err) {
          console.error('Failed to load recipe for editing:', err);
          setError('Failed to load recipe data');
        }
      };
      
      loadRecipe();
    } else {
      // Generate unique recipe name for new recipe
      const generateUniqueRecipeName = async () => {
        try {
          const recipes = await api.getRecipes();
          let counter = 1;
          let name = `Recipe ${counter}`;
          while (recipes.includes(name)) {
            counter++;
            name = `Recipe ${counter}`;
          }
          setRecipeName(name);
        } catch (err) {
          console.error('Failed to generate unique recipe name:', err);
          setRecipeName('Recipe 1'); // fallback
        }
      };
      
      generateUniqueRecipeName();
    }
  }, [editRecipeId]);

  const addCookingInstruction = () => {
    setInstructions([...instructions, {
      aiList: [{ description: '', attention: true, duration_seconds: 30 }],
      dependencies: []
    }]);
  };

  const removeCookingInstruction = (index: number) => {
    if (instructions.length > 1) {
      setInstructions(instructions.filter((_, i) => i !== index));
    }
  };

  const addAtomicInstruction = (instructionIndex: number) => {
    const newInstructions = [...instructions];
    newInstructions[instructionIndex].aiList.push({
      description: '',
      attention: true,
      duration_seconds: 30
    });
    setInstructions(newInstructions);
  };

  const removeAtomicInstruction = (instructionIndex: number, atomicIndex: number) => {
    const newInstructions = [...instructions];
    if (newInstructions[instructionIndex].aiList.length > 1) {
      newInstructions[instructionIndex].aiList.splice(atomicIndex, 1);
      setInstructions(newInstructions);
    }
  };

  const updateAtomicInstruction = (
    instructionIndex: number,
    atomicIndex: number,
    field: keyof AtomicInstructionForm,
    value: string | boolean | number
  ) => {
    const newInstructions = [...instructions];
    (newInstructions[instructionIndex].aiList[atomicIndex] as any)[field] = value;
    setInstructions(newInstructions);
  };

  const updateDependencies = (instructionIndex: number, dependencies: string) => {
    const newInstructions = [...instructions];
    const depArray = dependencies
      .split(',')
      .map(s => s.trim())
      .filter(s => s !== '')
      .map(s => parseInt(s))
      .filter(n => !isNaN(n));
    newInstructions[instructionIndex].dependencies = depArray;
    setInstructions(newInstructions);
  };

  const deleteRecipe = async () => {
    if (!editRecipeId) return;
    
    setLoading(true);
    setError('');
    
    try {
      await api.deleteRecipe(editRecipeId);
      onRecipeAdded(); // This will take us back to the main page
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Failed to delete recipe: ${err.message}`);
      } else {
        setError('Failed to delete recipe');
      }
      console.error('Error deleting recipe:', err);
      setShowDeleteConfirm(false);
    } finally {
      setLoading(false);
    }
  };

  const saveRecipe = async () => {
    if (!recipeName.trim()) {
      setError('Recipe name is required');
      return;
    }

    if (instructions.some(inst => inst.aiList.some(ai => !ai.description.trim()))) {
      setError('All atomic instruction descriptions are required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      if (editRecipeId) {
        // Update existing recipe
        const result = await api.updateRecipe(editRecipeId, {
          recipe_name: recipeName,
          instructions
        });
        // If recipe was renamed, the result will contain the new recipe_id
        // We pass this info back to the parent to update the UI accordingly
      } else {
        // Add new recipe
        await api.addRecipe({
          recipe_name: recipeName,
          instructions
        });
      }
      onRecipeAdded();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError('Recipe name already exists. Please choose a different name.');
        } else {
          setError(`Failed to save recipe: ${err.message}`);
        }
      } else {
        setError('Failed to save recipe');
      }
      console.error('Error saving recipe:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">
            {editRecipeId ? 'Edit Recipe' : 'Add New Recipe'}
          </h1>
          <button
            onClick={onBack}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {showDeleteConfirm && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 font-medium mb-3">Are you sure you want to delete this recipe?</p>
            <p className="text-red-700 text-sm mb-4">This action cannot be undone.</p>
            <div className="flex gap-3">
              <button
                onClick={deleteRecipe}
                disabled={loading}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Deleting...' : 'Yes, Delete'}
              </button>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={loading}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Recipe Name {editRecipeId && <span className="text-sm font-normal text-gray-500">(can be changed)</span>}
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                value={recipeName}
                onChange={(e) => setRecipeName(e.target.value)}
                className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                placeholder="Enter recipe name"
                disabled={loading}
              />
              {editRecipeId && (
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(true)}
                  className="px-4 py-3 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={loading}
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Recipe
                </button>
              )}
            </div>
          </div>

          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Cooking Instructions</h2>
            
            {instructions.map((instruction, instructionIndex) => (
              <div key={instructionIndex} className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-md font-medium text-gray-900">
                    Cooking Instruction {instructionIndex + 1}
                  </h3>
                  {instructions.length > 1 && (
                    <button
                      onClick={() => removeCookingInstruction(instructionIndex)}
                      className="text-red-600 hover:text-red-700 p-1"
                      disabled={loading}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Dependencies (comma-separated instruction indices)
                  </label>
                  <input
                    type="text"
                    value={instruction.dependencies.join(', ')}
                    onChange={(e) => updateDependencies(instructionIndex, e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g., 0, 1, 2"
                    disabled={loading}
                  />
                </div>

                <div className="space-y-3">
                  <h4 className="text-sm font-medium text-gray-700">Atomic Instructions</h4>
                  
                  {instruction.aiList.map((atomicInstruction, atomicIndex) => (
                    <div key={atomicIndex} className="border border-gray-200 rounded-lg p-3 bg-white">
                      <div className="flex items-center justify-between mb-3">
                        <h5 className="text-sm font-medium text-gray-800">
                          Atomic Instruction {atomicIndex + 1}
                        </h5>
                        {instruction.aiList.length > 1 && (
                          <button
                            onClick={() => removeAtomicInstruction(instructionIndex, atomicIndex)}
                            className="text-red-600 hover:text-red-700 p-1"
                            disabled={loading}
                          >
                            <X className="w-3 h-3" />
                          </button>
                        )}
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Description
                          </label>
                          <input
                            type="text"
                            value={atomicInstruction.description}
                            onChange={(e) => updateAtomicInstruction(instructionIndex, atomicIndex, 'description', e.target.value)}
                            className="w-full p-2 border border-gray-300 rounded focus:ring-1 focus:ring-primary-500 focus:border-primary-500 text-sm"
                            placeholder="e.g., Chop onions"
                            disabled={loading}
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Duration (seconds)
                          </label>
                          <input
                            type="number"
                            value={atomicInstruction.duration_seconds}
                            onChange={(e) => updateAtomicInstruction(instructionIndex, atomicIndex, 'duration_seconds', parseInt(e.target.value) || 0)}
                            className="w-full p-2 border border-gray-300 rounded focus:ring-1 focus:ring-primary-500 focus:border-primary-500 text-sm"
                            min="1"
                            disabled={loading}
                          />
                        </div>

                        <div className="flex items-center">
                          <label className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={atomicInstruction.attention}
                              onChange={(e) => updateAtomicInstruction(instructionIndex, atomicIndex, 'attention', e.target.checked)}
                              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                              disabled={loading}
                            />
                            <span className="text-gray-700">Requires attention</span>
                          </label>
                        </div>
                      </div>
                    </div>
                  ))}

                  <button
                    onClick={() => addAtomicInstruction(instructionIndex)}
                    className="flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700 font-medium"
                    disabled={loading}
                  >
                    <Plus className="w-4 h-4" />
                    Add Atomic Instruction
                  </button>
                </div>
              </div>
            ))}

            <button
              onClick={addCookingInstruction}
              className="flex items-center gap-2 text-primary-600 hover:text-primary-700 font-medium"
              disabled={loading}
            >
              <Plus className="w-5 h-5" />
              Add Cooking Instruction
            </button>
          </div>

          <div className="flex justify-end pt-6 border-t">
            <button
              onClick={saveRecipe}
              disabled={loading}
              className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-4 h-4" />
              {loading ? 'Saving...' : (editRecipeId ? 'Update Recipe' : 'Save Recipe')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};