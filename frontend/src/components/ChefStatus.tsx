import React from 'react';
import { User, Clock, CheckCircle, AlertCircle, Wifi, WifiOff, UserMinus } from 'lucide-react';
import { Session } from '../types';
import { 
  getActiveTaskForChef,
  getActiveTasksForChef, 
  getCurrentAI, 
  getRemainingTime,
  isChefBusy,
  isChefAvailable,
  formatDuration,
  formatTime
} from '../utils';

interface ChefStatusProps {
  session: Session;
  chefName: string;
  currentTime: number;
  onRemoveChef?: (chefName: string) => void;
}

export const ChefStatus: React.FC<ChefStatusProps> = ({
  session,
  chefName,
  currentTime,
  onRemoveChef
}) => {
  const chef = session.chefs_data[chefName];
  const activeTasks = getActiveTasksForChef(session, chefName);
  const isBusy = isChefBusy(session, chefName);
  const isAvailable = isChefAvailable(session, chefName);
  
  const getStatusIcon = () => {
    if (chef.disconnected) {
      return <WifiOff className="w-5 h-5 text-red-500" />;
    }
    if (isBusy) {
      // Check if any task needs attention
      const hasAttentionTask = activeTasks.some(task => {
        const ai = getCurrentAI(session, task.instruction_index, task.ai_index);
        return ai?.attention;
      });
      if (hasAttentionTask) {
        return <AlertCircle className="w-5 h-5 text-warning-600 animate-pulse" />;
      }
      return <Clock className="w-5 h-5 text-primary-600 animate-pulse" />;
    }
    return <CheckCircle className="w-5 h-5 text-success-600" />;
  };
  
  const getStatusText = () => {
    if (chef.disconnected) return 'Disconnected';
    if (isBusy) {
      const taskCount = activeTasks.length;
      if (taskCount > 1) {
        return `${taskCount} Active Tasks`;
      }
      const currentAI = activeTasks[0] ? getCurrentAI(session, activeTasks[0].instruction_index, activeTasks[0].ai_index) : null;
      return currentAI?.attention ? 'Manual Task' : 'Auto Task';
    }
    return 'Available';
  };
  
  const getStatusColor = () => {
    if (chef.disconnected) return 'text-red-600 bg-red-50 border-red-200';
    if (isBusy) {
      const hasAttentionTask = activeTasks.some(task => {
        const ai = getCurrentAI(session, task.instruction_index, task.ai_index);
        return ai?.attention;
      });
      return hasAttentionTask ? 'text-warning-600 bg-warning-50 border-warning-200' : 'text-primary-600 bg-primary-50 border-primary-200';
    }
    return 'text-success-600 bg-success-50 border-success-200';
  };
  
  const handleRemoveChef = () => {
    if (onRemoveChef) {
      const confirmed = window.confirm(`Are you sure you want to remove ${chefName} from the cooking session?`);
      if (confirmed) {
        onRemoveChef(chefName);
      }
    }
  };
  
  return (
    <div className={`p-4 rounded-lg border ${getStatusColor()}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <User className="w-5 h-5" />
            <span className="font-semibold text-gray-900">{chefName}</span>
          </div>
          {getStatusIcon()}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium px-2 py-1 rounded-full ${
            chef.disconnected ? 'bg-red-100 text-red-800' :
            isBusy ? (activeTasks.some(task => getCurrentAI(session, task.instruction_index, task.ai_index)?.attention) ? 'bg-warning-100 text-warning-800' : 'bg-primary-100 text-primary-800') :
            'bg-success-100 text-success-800'
          }`}>
            {getStatusText()}
          </span>
          {onRemoveChef && (
            <button
              onClick={handleRemoveChef}
              className="p-1 rounded-full hover:bg-red-100 text-red-600 hover:text-red-700 transition-colors"
              title={`Remove ${chefName} from session`}
            >
              <UserMinus className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
      
      {isBusy && activeTasks.length > 0 && (
        <div className="space-y-3">
          <div className="text-sm">
            <span className="font-medium">{activeTasks.length > 1 ? 'Active Tasks:' : 'Current Task:'}</span>
            <div className="space-y-2 mt-1">
              {activeTasks.map((task) => {
                const currentAI = getCurrentAI(session, task.instruction_index, task.ai_index);
                const remainingTime = getRemainingTime(session, task, currentTime);
                
                return (
                  <div key={task.instruction_index} className="p-2 bg-white rounded border">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Step {task.instruction_index + 1}: {currentAI.description}</span>
                      <span className="text-gray-500">{formatDuration(currentAI.duration)}</span>
                    </div>
                    {currentAI.attention && (
                      <div className="mt-1 text-warning-700 text-xs flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        Manual attention required
                      </div>
                    )}
                    {remainingTime > 0 && (
                      <div className="mt-1 text-sm text-gray-600">
                        Time remaining: <span className="font-mono font-bold">{formatTime(remainingTime)}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
      
      {!isBusy && isAvailable && (
        <div className="text-sm text-gray-600">
          Ready for next task
        </div>
      )}
      
      {chef.disconnected && (
        <div className="text-sm text-red-600">
          Last seen: {chef.heartbeat ? new Date(chef.heartbeat * 1000).toLocaleTimeString() : 'Unknown'}
        </div>
      )}
    </div>
  );
}; 