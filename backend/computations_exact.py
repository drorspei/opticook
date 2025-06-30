#!/usr/bin/env python3
"""Exact SAT encoding without time granularity - guarantees monotonicity."""

import copy
import tqdm
from dataclasses import dataclass, replace
from itertools import product, combinations
from typing import Dict, List, Optional, Set, Tuple
from pycryptosat import Solver
from functools import lru_cache
import multiprocessing, queue
import os

from data_models import *
from computations_optimized import (
    _instruction_cooking_time_cached, instruction_cooking_time,
    is_in_attention, time_left_in_attention, _attention_span_cached, attention_span,
    cooking_graph, forbidden_int_shifts, forbidden_intervals_shifts, interval_union,
    recipe_active_part, active_ai_done, _chef_needs_attention,
    _at_most_one_sequential_fixed, satSolve, run_with_timeout, _binarysearch,
    refresh_session
)


def session2sat_exact_monotonic(session: Session, time_ub: int, now: int):
    """
    Exact SAT encoding without time granularity optimization.
    
    This guarantees monotonicity: if time T is satisfiable, then T+k is also satisfiable.
    We sacrifice some performance for correctness.
    """
    
    vertex_set, edges, _ = cooking_graph(session)
    chefs = list(session.chefs_data)
    
    # ========== NO TIME GRANULARITY - USE EXACT TIME ==========
    # This is the key fix: use actual time units, not coarse granularity
    time_slots = range(time_ub + 1)  # 0 to time_ub inclusive
    
    # Helper function for getting instruction (potentially shortened for active tasks)
    active_recipe = recipe_active_part(session, now)
    def _inst(idx: int):
        return active_recipe.get(idx, session.recipe[idx])
    
    print(f"Exact SAT encoding: time_ub={time_ub}, time_slots={len(time_slots)}")
    
    # ---------------- triple enumeration with filtering ----------------
    # Create (chef, start_time, instruction) triples
    triples = []
    for p in chefs:
        for v in vertex_set:
            duration = instruction_cooking_time(_inst(v))
            for t in time_slots:
                # Task can start at time t if it can complete by time_ub
                if t + duration <= time_ub:
                    triples.append((p, t, v))
    
    triple2idx = {tpl: idx for idx, tpl in enumerate(triples, 1)}
    
    print(f"Generated {len(triples)} triples for exact time encoding")
    
    # Track auxiliary variables to avoid conflicts
    aux_var_counter = len(triple2idx) + 1
    
    # ---------------- part 0 · assert current running tasks ----------------
    clauses0 = []
    for chef, tasks in session.cooking_map.items():
        for task in tasks.values():
            triple = (chef, 0, task.instruction_index)
            if triple in triple2idx:
                clauses0.append([triple2idx[triple]])
    
    # ---------------- part 0.5 · exclude instructions already being worked on ----------------
    clauses0_5 = []
    active_instructions = set()
    for chef_tasks in session.cooking_map.values():
        active_instructions.update(chef_tasks.keys())
    
    for inst_idx in active_instructions:
        for chef in chefs:
            triple = (chef, 0, inst_idx)
            if triple in triple2idx:
                actual_chef = None
                for c, tasks in session.cooking_map.items():
                    if inst_idx in tasks:
                        actual_chef = c
                        break
                
                if actual_chef and chef != actual_chef:
                    clauses0_5.append([-triple2idx[triple]])
    
    # ---------------- part 1 · no overlapping attention tasks ------------
    clauses1: List[List[int]] = []
    
    # For each chef and each exact time point, at most one attention task can be active
    attention_tasks = [v for v in vertex_set if attention_span(_inst(v))]
    
    for chef in chefs:
        for exact_time in time_slots:
            # Find all attention tasks that could be active at this exact time
            active_at_time = []
            
            for v in attention_tasks:
                spans = attention_span(_inst(v))
                duration = instruction_cooking_time(_inst(v))
                
                # Check all possible start times for task v
                for start_time in time_slots:
                    if start_time + duration <= time_ub:
                        # Check if any attention span would be active at exact_time
                        for span_start, span_end in spans:
                            absolute_span_start = start_time + span_start
                            absolute_span_end = start_time + span_end
                            
                            if absolute_span_start <= exact_time <= absolute_span_end:
                                triple = (chef, start_time, v)
                                if triple in triple2idx:
                                    active_at_time.append(triple2idx[triple])
                                    break  # Don't double-count the same task
            
            # At most one attention task can be active at this time
            if len(active_at_time) > 3:
                seq_clauses, aux_var_counter = _at_most_one_sequential_fixed(tuple(active_at_time), aux_var_counter)
                clauses1.extend([list(clause) for clause in seq_clauses])
            elif len(active_at_time) > 1:
                for i in range(len(active_at_time)):
                    for j in range(i + 1, len(active_at_time)):
                        clauses1.append([-active_at_time[i], -active_at_time[j]])
    
    # ---------------- part 2 · every task is done at least once ------------
    clauses2: List[List[int]] = []
    for v in vertex_set:
        clause: List[int] = []
        duration = instruction_cooking_time(_inst(v))
        for chef in chefs:
            for t in time_slots:
                if t + duration <= time_ub:
                    triple = (chef, t, v)
                    if triple in triple2idx:
                        clause.append(triple2idx[triple])
        if clause:
            clauses2.append(clause)
    
    # ---------------- part 3 · every task at most once ----------------
    clauses3: List[List[int]] = []
    for v in vertex_set:
        vars_v = [triple2idx[(c, t, v)] for c in chefs for t in time_slots
                  if (c, t, v) in triple2idx]
        if len(vars_v) > 3:
            seq_clauses, aux_var_counter = _at_most_one_sequential_fixed(tuple(vars_v), aux_var_counter)
            clauses3.extend([list(clause) for clause in seq_clauses])
        elif len(vars_v) > 1:
            for i in range(len(vars_v)):
                for j in range(i + 1, len(vars_v)):
                    clauses3.append([-vars_v[i], -vars_v[j]])
    
    # ---------------- part 4 · dependency order (exact time) ----------------
    clauses4: List[List[int]] = []
    
    deps_by_dst = {}
    for dep, dst in edges:
        if dst not in deps_by_dst:
            deps_by_dst[dst] = []
        deps_by_dst[dst].append(dep)
    
    for dst, dep_list in deps_by_dst.items():
        for chef_dst in chefs:
            for t_dst in time_slots:
                if (chef_dst, t_dst, dst) not in triple2idx:
                    continue
                
                # dst wants to start at time t_dst
                for dep in dep_list:
                    dur_dep = instruction_cooking_time(_inst(dep))
                    
                    # Find all dependency assignments that would conflict
                    for chef_dep in chefs:
                        for t_dep in time_slots:
                            if (chef_dep, t_dep, dep) not in triple2idx:
                                continue
                            
                            # If dep starts at t_dep, it finishes at t_dep + dur_dep
                            # This conflicts if dep finishes after dst wants to start
                            if t_dep + dur_dep > t_dst:
                                clauses4.append([-triple2idx[(chef_dst, t_dst, dst)], 
                                               -triple2idx[(chef_dep, t_dep, dep)]])
    
    # ---------------- part 5 · symmetry breaking ---------------------------
    clauses5: List[List[int]] = []
    if len(chefs) > 1:
        for chef_idx in range(len(chefs) - 1):
            chef1, chef2 = chefs[chef_idx], chefs[chef_idx + 1]
            
            min_vertex_at_t0 = None
            for v in sorted(vertex_set):
                if (chef1, 0, v) in triple2idx and (chef2, 0, v) in triple2idx:
                    min_vertex_at_t0 = v
                    break
            
            if min_vertex_at_t0 is not None:
                chef1_t0_options = [triple2idx[(chef1, 0, v)] for v in vertex_set if (chef1, 0, v) in triple2idx]
                if chef1_t0_options:
                    clause = [-triple2idx[(chef2, 0, min_vertex_at_t0)]] + chef1_t0_options
                    clauses5.append(clause)
    
    all_clauses = clauses0 + clauses0_5 + clauses1 + clauses2 + clauses3 + clauses4 + clauses5
    
    print(f"Clause counts - part0: {len(clauses0)}, part0.5: {len(clauses0_5)}, "
          f"part1: {len(clauses1)}, part2: {len(clauses2)}, part3: {len(clauses3)}, part4: {len(clauses4)}, part5: {len(clauses5)}")
    
    return triple2idx, all_clauses


def graph2solve_with_timeout_exact(session: Session, time_ub: int, now: int, timeout: int = 60):
    """Exact version using monotonic SAT encoding without time granularity."""
    t2i, clauses = session2sat_exact_monotonic(session, time_ub, now)
    return run_with_timeout(satSolve, [clauses, t2i], timeout)


def sat_search_exact(session: Session, now: int = 0, lb: int = 0, timeout: int = 60):
    """Exact SAT search that guarantees monotonicity."""
    ub = cooking_graph(session)[2]
    if lb >= ub:
        return False
    return _binarysearch(lambda t: graph2solve_with_timeout_exact(session, t, now, timeout), lb, ub)