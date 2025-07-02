import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, RotateCcw, ChefHat, Clock } from 'lucide-react';
import { Session, ActiveTask } from './types';
import { api, ApiError } from './api';
import { SessionSetup } from './components/SessionSetup';
import { AddRecipe } from './components/AddRecipe';
import { TaskCard } from './components/TaskCard';
import { ChefStatus } from './components/ChefStatus';
import { 
  getTotalRecipeTime, 
  getCompletedRecipeTime, 
  formatDuration,
  formatTime
} from './utils';

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [currentTime, setCurrentTime] = useState<number>(Math.floor(Date.now() / 1000));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [sessionStartTime, setSessionStartTime] = useState<number>(0);
  const [showAddRecipe, setShowAddRecipe] = useState(false);
  const [editRecipeId, setEditRecipeId] = useState<string | null>(null);
  
  // Timer for updating current time
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Math.floor(Date.now() / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, []);
  
  // Auto-refresh session state
  useEffect(() => {
    if (session) {
      const interval = setInterval(() => {
        refreshSession();
      }, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [session]);
  
  const refreshSession = useCallback(async () => {
    if (!session) return;
    
    try {
      const updatedSession = await api.refresh({
        timestamp_seconds: currentTime
      });
      setSession(updatedSession);
    } catch (err) {
      console.error('Error refreshing session:', err);
    }
  }, [session, currentTime]);
  
  const markTaskDone = async (instructionIndex: number) => {
    if (!session) return;
    
    setLoading(true);
    try {
      // Find which chef is working on this task
      const activeChef = Object.entries(session.cooking_map).find(([_, tasks]) => 
        (tasks as Record<number, ActiveTask>)[instructionIndex] !== undefined
      )?.[0];
      
      if (!activeChef) {
        throw new Error('No chef found for this task');
      }
      
      const updatedSession = await api.markDone({
        chef: activeChef,
        instruction_index: instructionIndex,
        timestamp_seconds: currentTime
      });
      setSession(updatedSession);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Failed to mark task done: ${err.message}`);
      } else {
        setError('Failed to mark task done');
      }
      console.error('Error marking task done:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const resetSession = async () => {
    setLoading(true);
    try {
      await api.reset();
      setSession(null);
      setCurrentTime(0);
      setSessionStartTime(0);
      setError('');
    } catch (err) {
      setError('Failed to reset session');
      console.error('Error resetting session:', err);
    } finally {
      setLoading(false);
    }
  };
  
  const handleSessionStarted = () => {
    setSessionStartTime(Math.floor(Date.now() / 1000));
    setShowAddRecipe(false);
    // Load initial session state
    loadSessionState();
  };

  const handleAddRecipe = () => {
    setShowAddRecipe(true);
    setEditRecipeId(null);
  };

  const handleEditRecipe = (recipeId: string) => {
    setShowAddRecipe(true);
    setEditRecipeId(recipeId);
  };

  const handleBackToSetup = () => {
    setShowAddRecipe(false);
    setEditRecipeId(null);
  };

  const handleRecipeAdded = () => {
    setShowAddRecipe(false);
    setEditRecipeId(null);
    // Optionally refresh the recipe list or show a success message
  };
  
  const loadSessionState = async () => {
    try {
      const sessionState = await api.getState();
      setSession(sessionState);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        // No active session, stay on setup screen
        return;
      }
      setError('Failed to load session state');
      console.error('Error loading session state:', err);
    }
  };
  
  // Check for existing session on mount
  useEffect(() => {
    loadSessionState();
  }, []);
  
  if (!session) {
    if (showAddRecipe) {
      return (
        <AddRecipe 
          onBack={handleBackToSetup}
          onRecipeAdded={handleRecipeAdded}
          editRecipeId={editRecipeId}
        />
      );
    }
    return (
      <SessionSetup 
        onSessionStarted={handleSessionStarted}
        onAddRecipe={handleAddRecipe}
        onEditRecipe={handleEditRecipe}
      />
    );
  }
  
  const totalTime = getTotalRecipeTime(session.recipe);
  const completedTime = getCompletedRecipeTime(session);
  const elapsedTime = sessionStartTime > 0 ? currentTime - sessionStartTime : 0;
  const progress = totalTime > 0 ? (completedTime / totalTime) * 100 : 0;
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <ChefHat className="w-8 h-8 text-primary-600" />
              <h1 className="text-xl font-bold text-gray-900">Opticook</h1>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Clock className="w-4 h-4" />
                <span>Session Time: {formatTime(elapsedTime)}</span>
              </div>
              
              <button
                onClick={refreshSession}
                disabled={loading}
                className="btn-secondary flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              
              <button
                onClick={resetSession}
                disabled={loading}
                className="btn-secondary flex items-center gap-2"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
            </div>
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}
        
        {/* Progress Overview */}
        <div className="card mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Session Progress</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary-600">{Math.round(progress)}%</div>
              <div className="text-sm text-gray-600">Complete</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{formatDuration(completedTime)}</div>
              <div className="text-sm text-gray-600">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{formatDuration(totalTime)}</div>
              <div className="text-sm text-gray-600">Total Time</div>
            </div>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div 
              className="bg-primary-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Chef Status */}
          <div className="lg:col-span-1">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Chef Status</h2>
            <div className="space-y-4">
              {Object.keys(session.chefs_data).map((chefName) => (
                <ChefStatus
                  key={chefName}
                  session={session}
                  chefName={chefName}
                  currentTime={currentTime}
                />
              ))}
            </div>
          </div>
          
          {/* Tasks */}
          <div className="lg:col-span-2">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Cooking Tasks</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {session.recipe.map((_, instructionIndex) => (
                <TaskCard
                  key={instructionIndex}
                  session={session}
                  instructionIndex={instructionIndex}
                  onMarkDone={markTaskDone}
                  currentTime={currentTime}
                />
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App; 