import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle, AlertCircle, Play } from 'lucide-react';
import { 
  isTaskCompleted, 
  getTaskProgress, 
  getActiveTaskForChef, 
  getCurrentAI, 
  formatDuration,
  unitsToSeconds
} from '../utils';

export const TaskCard = ({
  session,
  instructionIndex,
  chefName,
  onMarkDone,
  currentTime
}) => {
  const instruction = session.recipe[instructionIndex];
  const isCompleted = isTaskCompleted(session, instructionIndex);
  const progress = getTaskProgress(session, instructionIndex);
  
  // Find which chef is working on this task
  const activeChef = Object.entries(session.cooking_map).find(([_, tasks]) => 
    tasks[instructionIndex] !== undefined
  )?.[0];
  
  const activeTask = activeChef ? getActiveTaskForChef(session, activeChef) : null;
  const isActive = activeTask?.instruction_index === instructionIndex;
  
  // Get current AI if task is active
  const currentAI = isActive && activeTask ? getCurrentAI(session, instructionIndex, activeTask.ai_index) : null;
  
  // Check if current AI needs attention
  const needsAttention = currentAI?.attention || false;
  
  // Local timer state for non-attention tasks
  const [localTimer, setLocalTimer] = useState(null);
  const [localStartTime, setLocalStartTime] = useState(null);
  const [timerCompleted, setTimerCompleted] = useState(false);
  
  // Initialize local timer when a non-attention task starts
  useEffect(() => {
    if (isActive && currentAI && !needsAttention && localTimer === null && !timerCompleted) {
      const durationSeconds = unitsToSeconds(currentAI.duration);
      console.log(`[DEBUG] Timer init: task=${instructionIndex}, duration=${durationSeconds}s`);
      setLocalTimer(durationSeconds);
      setLocalStartTime(Date.now() / 1000);
      setTimerCompleted(false);
    } else if (!isActive && localTimer !== null) {
      // Reset timer when task is no longer active
      console.log(`[DEBUG] Task ${instructionIndex} no longer active, resetting timer`);
      setLocalTimer(null);
      setLocalStartTime(null);
      setTimerCompleted(false);
    }
  }, [isActive, needsAttention, localTimer, instructionIndex, timerCompleted]);
  
  // Update local timer countdown and show completion signal when done
  useEffect(() => {
    if (localTimer && localStartTime && !needsAttention && !timerCompleted) {
      const interval = setInterval(() => {
        setLocalTimer(prevTimer => {
          if (prevTimer <= 0) {
            // Timer completed - show completion signal but don't auto-send to backend
            console.log(`[DEBUG] Timer completed! Showing completion signal for task ${instructionIndex}`);
            setTimerCompleted(true);
            return 0; // Keep at 0 instead of null to prevent effect re-run
          }
          const newTimer = prevTimer - 0.1; // Update every 100ms for smooth countdown
          return Math.max(0, newTimer);
        });
      }, 100);

      return () => clearInterval(interval);
    }
  }, [localStartTime, needsAttention, timerCompleted, instructionIndex]); // Removed localTimer from dependencies
  
  // Calculate remaining time - use local timer for non-attention tasks
  let remainingTimeSeconds = 0;
  if (isActive && currentAI) {
    if (needsAttention) {
      // For attention tasks, don't show timer
      remainingTimeSeconds = 0;
    } else {
      // For non-attention tasks, use local timer
      remainingTimeSeconds = localTimer || 0;
    }
  }
  
  // Clean up timer when task is truly completed (all AIs done)
  useEffect(() => {
    if (isCompleted && localTimer) {
      console.log(`[DEBUG] Task ${instructionIndex} truly completed, cleaning up timer`);
      setLocalTimer(null);
      setLocalStartTime(null);
      setTimerCompleted(false);
    }
  }, [isCompleted, localTimer, instructionIndex]);
  
  // Handle AI changes (e.g., moving from chopping to simmering) without re-initializing running timers
  useEffect(() => {
    if (isActive && currentAI && !needsAttention && localTimer === null && !timerCompleted) {
      const durationSeconds = unitsToSeconds(currentAI.duration);
      console.log(`[DEBUG] Timer init from AI change: task=${instructionIndex}, duration=${durationSeconds}s`);
      setLocalTimer(durationSeconds);
      setLocalStartTime(Date.now() / 1000);
      setTimerCompleted(false);
    }
  }, [currentAI?.duration, currentAI?.attention, isActive, needsAttention, localTimer, timerCompleted, instructionIndex]); // Added all necessary dependencies
  
  const getStatusIcon = () => {
    if (isCompleted) {
      return <CheckCircle className="w-5 h-5 text-success-600" />;
    }
    if (isActive) {
      if (needsAttention) {
        return <AlertCircle className="w-5 h-5 text-warning-600 animate-pulse" />;
      }
      return <Play className="w-5 h-5 text-primary-600 animate-pulse" />;
    }
    return <Clock className="w-5 h-5 text-gray-400" />;
  };
  
  const getStatusText = () => {
    if (isCompleted) return 'Completed';
    if (isActive) {
      return needsAttention ? 'Needs Attention' : 'In Progress';
    }
    return 'Pending';
  };
  
  const getCardClasses = () => {
    let baseClasses = 'task-card';
    if (isCompleted) return `${baseClasses} task-completed`;
    if (isActive) return `${baseClasses} task-active`;
    if (needsAttention) return `${baseClasses} task-attention`;
    return baseClasses;
  };
  
  return (
    <div className={getCardClasses()}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <h3 className="font-semibold text-gray-900">
            Step {instructionIndex + 1}
          </h3>
        </div>
        <span className={`text-sm font-medium px-2 py-1 rounded-full ${
          isCompleted ? 'bg-success-100 text-success-800' :
          isActive ? (needsAttention ? 'bg-warning-100 text-warning-800' : 'bg-primary-100 text-primary-800') :
          'bg-gray-100 text-gray-600'
        }`}>
          {getStatusText()}
        </span>
      </div>
      
      <div className="space-y-2">
        {instruction.aiList.map((ai, aiIndex) => {
          const isCurrentAI = isActive && activeTask?.ai_index === aiIndex;
          const isCompletedAI = session.done_tasks[instructionIndex]?.time_data.length > aiIndex;
          
          return (
            <div 
              key={aiIndex}
              className={`p-3 rounded-lg border ${
                isCurrentAI ? 'bg-primary-50 border-primary-200' :
                isCompletedAI ? 'bg-success-50 border-success-200' :
                'bg-gray-50 border-gray-200'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {ai.attention && (
                    <AlertCircle className="w-4 h-4 text-warning-600" />
                  )}
                  <span className={`font-medium ${
                    isCurrentAI ? 'text-primary-900' :
                    isCompletedAI ? 'text-success-900' :
                    'text-gray-700'
                  }`}>
                    {ai.description}
                  </span>
                </div>
                <span className="text-sm text-gray-500">
                  {formatDuration(ai.duration)}
                </span>
              </div>
              
              {isCurrentAI && (
                <div className="mt-2 flex items-center justify-between text-sm">
                  <span className="text-primary-700">
                    {needsAttention ? 'Manual task - mark when done' : 'Auto-completing...'}
                  </span>
                  {/* Only show timer for non-attention tasks */}
                  {!needsAttention && (localTimer !== null || timerCompleted) && (
                    <span className={timerCompleted ? "text-red-600 font-medium" : "text-primary-600 font-medium"}>
                      {Math.floor(remainingTimeSeconds / 60)}:{Math.floor(remainingTimeSeconds % 60).toString().padStart(2, '0')} 
                      {timerCompleted ? " - Timer finished!" : " remaining"}
                    </span>
                  )}
                  {/* Show blinking message when local timer hits 0 for non-attention task */}
                  {!needsAttention && timerCompleted && (
                    <span className="text-red-600 font-bold animate-blink ml-2">
                      Click "Mark Step Complete"
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      {activeChef && (
        <div className="mt-3 text-sm text-gray-600">
          Assigned to: <span className="font-medium">{activeChef}</span>
        </div>
      )}
      
      {progress > 0 && progress < 100 && (
        <div className="mt-3">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Progress</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
      
      {/* Show button for all active tasks, regardless of attention or timer status */}
      {isActive && onMarkDone && (
        <button
          onClick={() => onMarkDone(instructionIndex)}
          className="btn-success w-full mt-3"
        >
          Mark Step Complete
        </button>
      )}
    </div>
  );
}; 