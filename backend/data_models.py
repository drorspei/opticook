#!/usr/bin/env python
# coding: utf-8

# In[2]:


from typing import List, Dict, Optional, Tuple, Set

from dataclasses import dataclass
cooking_time_unit = 30 # seconds per quantum
assert 60 % cooking_time_unit == 0

def time_in_units(time : float, time_unit : int = cooking_time_unit) -> int:
    return int(time/time_unit) + int(bool(time%time_unit))

      
@dataclass(frozen=True)
class Chef:    # information about a chef
    name: str
    addr: Optional[str] = None
    heartbeat: Optional[int] = None # last heartbeat (epoch)
        
        
@dataclass(frozen=True)
class AtomicInstruction: # aka "ai"
    attention: bool
    duration: int  #seconds
    description: str



@dataclass(frozen=True)
class CookingInstruction: 
    index : int
    aiList : List[AtomicInstruction]
    dependencies : List[int]
        

@dataclass(frozen=True)
class ActiveTask:   # Information about an atomic instruction that is currently handled by a chef
    instruction_index : int
    ai_index : int
    start_time : Optional[int] = None
    #endtime : Optional[int] = None
        
@dataclass(frozen=True)
class DoneTask:  # information about a finished instruction
    instruction_index : int
    chef_name : str
    time_data : List[Tuple[int,int]] 
        #time_data[i] = (start_time(ai),end_time(ai)) where ai = recipe[instruction_index][i]
        
@dataclass(frozen=True)
class Session:
    recipe: List[CookingInstruction] 
    chefs_data : Dict[str, Chef]  #chef_name -> chef's infomation 
    cooking_map: Dict[str, Dict[int,ActiveTask]]  #chef_name -> instruction_index --> its active task 
    done_tasks : Dict[int, DoneTask] # done_tasks.keys() = recipe indecies of done instructions



# In[ ]:




