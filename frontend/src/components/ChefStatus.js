import React from 'react';
import { User, Clock, CheckCircle, AlertCircle, WifiOff } from 'lucide-react';
import { 
  getActiveTaskForChef, 
  getCurrentAI, 
  getRemainingTime,
  isChefBusy,
  isChefAvailable,
  formatDuration,
  formatTime
} from '../utils';

export const ChefStatus = ({
  session,
  chefName,
  currentTime
}) => {
  const chef = session.chefs_data[chefName];
  const activeTask = getActiveTaskForChef(session, chefName);
  const isBusy = isChefBusy(session, chefName);
  const isAvailable = isChefAvailable(session, chefName);
  
  const getStatusIcon = () => {
    if (chef.disconnected) {
      return <WifiOff className="w-5 h-5 text-red-500" />;
    }
    if (isBusy) {
      const currentAI = activeTask ? getCurrentAI(session, activeTask.instruction_index, activeTask.ai_index) : null;
      if (currentAI?.attention) {
        return <AlertCircle className="w-5 h-5 text-warning-600 animate-pulse" />;
      }
      return <Clock className="w-5 h-5 text-primary-600 animate-pulse" />;
    }
    return <CheckCircle className="w-5 h-5 text-success-600" />;
  };
  
  const getStatusText = () => {
    if (chef.disconnected) return 'Disconnected';
    if (isBusy) {
      const currentAI = activeTask ? getCurrentAI(session, activeTask.instruction_index, activeTask.ai_index) : null;
      return currentAI?.attention ? 'Manual Task' : 'Auto Task';
    }
    return 'Available';
  };
  
  const getStatusColor = () => {
    if (chef.disconnected) return 'text-red-600 bg-red-50 border-red-200';
    if (isBusy) {
      const currentAI = activeTask ? getCurrentAI(session, activeTask.instruction_index, activeTask.ai_index) : null;
      return currentAI?.attention ? 'text-warning-600 bg-warning-50 border-warning-200' : 'text-primary-600 bg-primary-50 border-primary-200';
    }
    return 'text-success-600 bg-success-50 border-success-200';
  };
  
  const remainingTime = activeTask ? getRemainingTime(session, activeTask, currentTime) : 0;
  const currentAI = activeTask ? getCurrentAI(session, activeTask.instruction_index, activeTask.ai_index) : null;
  
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
        <span className={`text-sm font-medium px-2 py-1 rounded-full ${
          chef.disconnected ? 'bg-red-100 text-red-800' :
          isBusy ? (currentAI?.attention ? 'bg-warning-100 text-warning-800' : 'bg-primary-100 text-primary-800') :
          'bg-success-100 text-success-800'
        }`}>
          {getStatusText()}
        </span>
      </div>
      
      {isBusy && activeTask && currentAI && (
        <div className="space-y-2">
          <div className="text-sm">
            <span className="font-medium">Current Task:</span>
            <div className="mt-1 p-2 bg-white rounded border">
              <div className="flex items-center justify-between">
                <span className="font-medium">Step {activeTask.instruction_index + 1}: {currentAI.description}</span>
                <span className="text-gray-500">{formatDuration(currentAI.duration)}</span>
              </div>
              {currentAI.attention && (
                <div className="mt-1 text-warning-700 text-xs flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  Manual attention required
                </div>
              )}
            </div>
          </div>
          
          {remainingTime > 0 && (
            <div className="text-sm">
              <span className="font-medium">Time Remaining:</span>
              <div className="mt-1 font-mono text-lg font-bold">
                {formatTime(remainingTime)}
              </div>
            </div>
          )}
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