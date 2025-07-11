import React from 'react';
import { Clock, CheckCircle, AlertCircle, Play } from 'lucide-react';
import { Session, ActiveTask } from '../types';
import { 
  isTaskCompleted, 
  getTaskProgress, 
  getActiveTaskForChef, 
  getCurrentAI, 
  getRemainingTime,
  formatDuration,
  formatTime
} from '../utils';

interface TaskCardProps {
  session: Session;
  instructionIndex: number;
  chefName?: string;
  onMarkDone?: (instructionIndex: number) => void;
  currentTime: number;
}

export const TaskCard: React.FC<TaskCardProps> = ({
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
    (tasks as Record<number, ActiveTask>)[instructionIndex] !== undefined
  )?.[0];
  
  // Get the specific task for this instruction
  const activeTask = activeChef && session.cooking_map[activeChef] ? 
    session.cooking_map[activeChef][instructionIndex] : null;
  const isActive = activeTask !== null;
  
  // Get current AI if task is active
  const currentAI = isActive && activeTask ? getCurrentAI(session, instructionIndex, activeTask.ai_index) : null;
  const remainingTime = isActive && activeTask ? getRemainingTime(session, activeTask, currentTime) : 0;
  
  // Check if current AI needs attention
  const needsAttention = currentAI?.attention || false;
  
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
          const isNonAttention = !ai.attention;
          const showTaskDone = isCurrentAI && isNonAttention && remainingTime <= 0;
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
                    {ai.attention ? 'Manual task - mark when done' : 'Auto-completing...'}
                  </span>
                  {remainingTime > 0 && (
                    <span className="text-primary-600 font-medium">
                      {formatTime(remainingTime)} remaining
                    </span>
                  )}
                  {showTaskDone && (
                    <span className="text-success-700 font-semibold ml-2">Task is Done!</span>
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