// Time conversion utilities
export const COOKING_TIME_UNIT = 30; // seconds per quantum

export function timeInUnits(seconds) {
  return Math.ceil(seconds / COOKING_TIME_UNIT);
}

export function unitsToSeconds(quanta) {
  return quanta * COOKING_TIME_UNIT;
}

export function formatDuration(quanta) {
  const seconds = unitsToSeconds(quanta);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  
  if (minutes === 0) {
    return `${remainingSeconds}s`;
  }
  return `${minutes}m ${remainingSeconds}s`;
}

export function formatTime(quanta) {
  const seconds = unitsToSeconds(quanta);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// Task status utilities
export function isTaskCompleted(session, instructionIndex) {
  const doneTask = session.done_tasks[instructionIndex];
  if (!doneTask) return false;
  
  const instruction = session.recipe[instructionIndex];
  return doneTask.time_data.length === instruction.aiList.length;
}

export function getTaskProgress(session, instructionIndex) {
  const doneTask = session.done_tasks[instructionIndex];
  if (!doneTask) return 0;
  
  const instruction = session.recipe[instructionIndex];
  return (doneTask.time_data.length / instruction.aiList.length) * 100;
}

export function getActiveTaskForChef(session, chefName) {
  const chefTasks = session.cooking_map[chefName];
  if (!chefTasks) return null;
  
  // Return the first active task (there should only be one per chef)
  const taskEntries = Object.entries(chefTasks);
  return taskEntries.length > 0 ? taskEntries[0][1] : null;
}

export function getCurrentAI(session, instructionIndex, aiIndex) {
  return session.recipe[instructionIndex].aiList[aiIndex];
}

export function getRemainingTime(session, task, now) {
  if (task.start_time === null) return 0;
  
  const ai = getCurrentAI(session, task.instruction_index, task.ai_index);
  const elapsed = now - task.start_time;
  return Math.max(0, ai.duration - elapsed);
}

export function isChefBusy(session, chefName) {
  const activeTask = getActiveTaskForChef(session, chefName);
  return activeTask !== null;
}

export function isChefAvailable(session, chefName) {
  return !isChefBusy(session, chefName) && !session.chefs_data[chefName].disconnected;
}

// Recipe utilities
export function getTotalRecipeTime(recipe) {
  return recipe.reduce((total, instruction) => {
    return total + instruction.aiList.reduce((sum, ai) => sum + ai.duration, 0);
  }, 0);
}

export function getCompletedRecipeTime(session) {
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