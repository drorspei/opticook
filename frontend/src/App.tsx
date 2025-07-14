import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, RotateCcw, ChefHat, Clock } from 'lucide-react';
import useEmblaCarousel from 'embla-carousel-react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Session, ActiveTask } from './types';
import { api, ApiError } from './api';
import { SessionSetup } from './components/SessionSetup';
import { AddRecipe } from './components/AddRecipe';
import { TaskCard } from './components/TaskCard';
import { ChefStatusPanel } from './components/ChefStatusPanel';
import { ChefTaskCarousel } from './components/ChefTaskCarousel';
import { 
  getTotalRecipeTime, 
  getCompletedRecipeTime, 
  formatDuration,
  formatTime,
  getCurrentAI,
  getRemainingTime
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
  
  const markTaskDone = async (chefName: string, instructionIndex: number) => {
    if (!session) return;
    
    setLoading(true);
    try {
      const updatedSession = await api.markDone({
        chef: chefName,
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
  
  const addChef = async (chefName: string) => {
    if (!session) return;
    
    setLoading(true);
    setError('');
    
    try {
      const updatedSession = await api.addChef(chefName, currentTime);
      setSession(updatedSession);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add chef');
      throw err; // Re-throw to be handled by the component
    } finally {
      setLoading(false);
    }
  };

  const removeChef = async (chefName: string) => {
    if (!session) return;
    
    setLoading(true);
    setError('');
    
    try {
      const updatedSession = await api.removeChef(chefName, currentTime);
      setSession(updatedSession);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove chef');
      throw err; // Re-throw to be handled by the component
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
  
  // Embla Carousel setup
  const [emblaRef, emblaApi] = useEmblaCarousel({
    loop: false,
    skipSnaps: false
  });
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Add state to track which instruction index should flash
  const [flashIndex, setFlashIndex] = useState<number | null>(null);
  const [urgentMessage, setUrgentMessage] = useState<string | null>(null);

  // Build a list of active instruction indices (for any chef)
  const activeInstructionIndices = React.useMemo(() => {
    const indices = new Set<number>();
    if (session) {
      Object.values(session.cooking_map).forEach(tasks => {
        Object.keys(tasks).forEach(idx => indices.add(Number(idx)));
      });
    }
    return Array.from(indices).sort((a, b) => a - b);
  }, [session]);

  // Embla: update selected index on slide change
  useEffect(() => {
    if (!emblaApi) return;
    const onSelect = () => setSelectedIndex(emblaApi.selectedScrollSnap());
    emblaApi.on('select', onSelect);
    onSelect();
    return () => {
      emblaApi.off('select', onSelect);
    };
  }, [emblaApi]);

  // Embla: keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!emblaApi) return;
      if (e.key === 'ArrowLeft') emblaApi.scrollPrev();
      if (e.key === 'ArrowRight') emblaApi.scrollNext();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [emblaApi]);
  
  // Auto-advance and flash logic
  useEffect(() => {
    if (!session || !emblaApi) return;
    // Find the first non-attention active task whose timer just ran out
    const now = currentTime;
    let found = false;
    for (const chefTasks of Object.values(session.cooking_map)) {
      for (const [idxStr, activeTask] of Object.entries(chefTasks)) {
        const idx = Number(idxStr);
        const currentAI = getCurrentAI(session, activeTask.instruction_index, activeTask.ai_index);
        const isNonAttention = currentAI && !currentAI.attention;
        const remaining = getRemainingTime(session, activeTask, now);
        if (isNonAttention && remaining === 0) {
          // Auto-advance carousel if not already on this card
          if (activeInstructionIndices[selectedIndex] !== idx) {
            const targetIdx = activeInstructionIndices.indexOf(idx);
            if (targetIdx !== -1) {
              emblaApi.scrollTo(targetIdx);
              setFlashIndex(idx);
              setUrgentMessage('Time to attend the task!');
              found = true;
              break;
            }
          } else {
            setFlashIndex(idx);
            setUrgentMessage('Time to attend the task!');
            found = true;
            break;
          }
        }
      }
      if (found) break;
    }
    if (!found) {
      setFlashIndex(null);
      setUrgentMessage(null);
    }
    // eslint-disable-next-line
  }, [session, currentTime, emblaApi, activeInstructionIndices, selectedIndex]);
  
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
              {/* <h1 className="text-xl font-bold text-gray-900">Opticook</h1> */}
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
        
        {/* Progress Overview 
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
        */}
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Chef Status */}
          <div className="lg:col-span-1">
            <ChefStatusPanel
              session={session}
              currentTime={currentTime}
              onAddChef={addChef}
              onRemoveChef={removeChef}
            />
          </div>
          {/* Tasks */}
          <div className="lg:col-span-2">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Cooking Tasks</h2>
            <div className="space-y-8">
              {Object.keys(session.chefs_data).map((chefName) => (
                <ChefTaskCarousel
                  key={chefName}
                  session={session}
                  chefName={chefName}
                  currentTime={currentTime}
                  onMarkDone={markTaskDone}
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
