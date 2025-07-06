import React, { useState } from 'react';
import { UserPlus, X, Check } from 'lucide-react';
import { Session } from '../types';
import { ChefStatus } from './ChefStatus';

interface ChefStatusPanelProps {
  session: Session;
  currentTime: number;
  onAddChef: (chefName: string) => Promise<void>;
  onRemoveChef?: (chefName: string) => Promise<void>;
}

export const ChefStatusPanel: React.FC<ChefStatusPanelProps> = ({
  session,
  currentTime,
  onAddChef,
  onRemoveChef
}) => {
  const [isAddingChef, setIsAddingChef] = useState(false);
  const [newChefName, setNewChefName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAddChef = async () => {
    if (!newChefName.trim()) {
      setError('Chef name cannot be empty');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    
    try {
      await onAddChef(newChefName.trim());
      setNewChefName('');
      setIsAddingChef(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add chef');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setIsAddingChef(false);
    setNewChefName('');
    setError(null);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Chef Status</h2>
        {!isAddingChef && (
          <button
            onClick={() => setIsAddingChef(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            Add Chef
          </button>
        )}
      </div>
      
      <div className="space-y-4">
        {isAddingChef && (
          <div className="p-4 rounded-lg border border-primary-200 bg-primary-50">
            <div className="space-y-3">
              <div>
                <label htmlFor="chef-name" className="block text-sm font-medium text-gray-700 mb-1">
                  Chef Name
                </label>
                <input
                  id="chef-name"
                  type="text"
                  value={newChefName}
                  onChange={(e) => setNewChefName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !isSubmitting) {
                      handleAddChef();
                    } else if (e.key === 'Escape') {
                      handleCancel();
                    }
                  }}
                  placeholder="Enter chef name"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={isSubmitting}
                  autoFocus
                />
                {error && (
                  <p className="mt-1 text-sm text-red-600">{error}</p>
                )}
              </div>
              
              <div className="flex gap-2">
                <button
                  onClick={handleAddChef}
                  disabled={isSubmitting || !newChefName.trim()}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Check className="w-4 h-4" />
                  {isSubmitting ? 'Adding...' : 'Add'}
                </button>
                <button
                  onClick={handleCancel}
                  disabled={isSubmitting}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <X className="w-4 h-4" />
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
        
        {Object.keys(session.chefs_data).map((chefName) => (
          <ChefStatus
            key={chefName}
            session={session}
            chefName={chefName}
            currentTime={currentTime}
            onRemoveChef={onRemoveChef}
          />
        ))}
      </div>
    </div>
  );
};