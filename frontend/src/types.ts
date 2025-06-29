export interface Chef {
  name: string;
  addr: string | null;
  heartbeat: number | null;
  disconnected: boolean;
}

export interface AtomicInstruction {
  attention: boolean;
  duration: number; // in quanta (30-second units)
  description: string;
}

export interface CookingInstruction {
  index: number;
  aiList: AtomicInstruction[];
  dependencies: number[];
}

export interface ActiveTask {
  instruction_index: number;
  ai_index: number;
  start_time: number | null;
}

export interface DoneTask {
  instruction_index: number;
  chef_name: string;
  time_data: [number, number][]; // (start, end) pairs for each AI
}

export interface Session {
  recipe: CookingInstruction[];
  chefs_data: Record<string, Chef>;
  cooking_map: Record<string, Record<number, ActiveTask>>;
  done_tasks: Record<number, DoneTask>;
}

export interface StartSessionRequest {
  recipe_id: string;
  chefs: string[];
}

export interface MarkDoneRequest {
  chef: string;
  instruction_index: number;
  timestamp_seconds: number;
}

export interface RefreshRequest {
  timestamp_seconds: number;
}

export interface RecipeInfo {
  index: number;
  aiList: {
    attention: boolean;
    duration_seconds: number;
    description: string;
  }[];
  dependencies: number[];
} 