import { Session, ActiveTask, DoneTask, AtomicInstruction } from './types';

// Time conversion utilities
export const COOKING_TIME_UNIT = 30; // seconds per quantum

export function timeInUnits(seconds: number): number {
  return Math.ceil(seconds / COOKING_TIME_UNIT);
}

export function unitsToSeconds(quanta: number): number {
  return quanta * COOKING_TIME_UNIT;
}

export function formatDuration(quanta: number): string {
  const seconds = unitsToSeconds(quanta);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  
  if (minutes === 0) {
    return `${remainingSeconds}s`;
  }
  return `${minutes}m ${remainingSeconds}s`;
}

export function formatTime(quanta: number): string {
  const seconds = unitsToSeconds(quanta);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// Task status utilities
export function isTaskCompleted(session: Session, instructionIndex: number): boolean {
  const doneTask = session.done_tasks[instructionIndex];
  if (!doneTask) return false;
  
  const instruction = session.recipe[instructionIndex];
  return doneTask.time_data.length === instruction.aiList.length;
}

export function getTaskProgress(session: Session, instructionIndex: number): number {
  const doneTask = session.done_tasks[instructionIndex];
  if (!doneTask) return 0;
  
  const instruction = session.recipe[instructionIndex];
  return (doneTask.time_data.length / instruction.aiList.length) * 100;
}

export function getActiveTaskForChef(session: Session, chefName: string): ActiveTask | null {
  const chefTasks = session.cooking_map[chefName];
  if (!chefTasks) return null;
  
  // Return the first active task (there should only be one per chef)
  const taskEntries = Object.entries(chefTasks);
  return taskEntries.length > 0 ? taskEntries[0][1] : null;
}

export function getCurrentAI(session: Session, instructionIndex: number, aiIndex: number): AtomicInstruction {
  return session.recipe[instructionIndex].aiList[aiIndex];
}

export function getRemainingTime(session: Session, task: ActiveTask, now: number): number {
  if (task.start_time === null) return 0;
  
  const ai = getCurrentAI(session, task.instruction_index, task.ai_index);
  const elapsed = now - task.start_time;
  return Math.max(0, ai.duration - elapsed);
}

export function isChefBusy(session: Session, chefName: string): boolean {
  const activeTask = getActiveTaskForChef(session, chefName);
  return activeTask !== null;
}

export function isChefAvailable(session: Session, chefName: string): boolean {
  return !isChefBusy(session, chefName) && !session.chefs_data[chefName].disconnected;
}

// Recipe utilities
export function getTotalRecipeTime(recipe: Session['recipe']): number {
  return recipe.reduce((total, instruction) => {
    return total + instruction.aiList.reduce((sum, ai) => sum + ai.duration, 0);
  }, 0);
}

export function getCompletedRecipeTime(session: Session): number {
  let completed = 0;
  
  Object.entries(session.done_tasks).forEach(([instIndex, doneTask]) => {
    const instruction = session.recipe[parseInt(instIndex)];
    const completedAIs = Math.min(doneTask.time_data.length, instruction.aiList.length);
    
    for (let i = 0; i < completedAIs; i++) {
      completed += instruction.aiList[i].duration;
    }
  });
  
  return completed;
} 