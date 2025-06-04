#!/usr/bin/env python
# coding: utf-8

# In[2]:


## SAT stuff ##
import tqdm
from subprocess import check_call
#!/usr/bin/env python
# coding: utf-8
# test2
from collections import namedtuple
from pycryptosat import Solver
from itertools import product
import multiprocessing
import queue
cooking_time_unit = 30    # in seconds
assert 60 % cooking_time_unit == 0


#cooking_time_unit = 30    # in seconds
#assert 60 % cooking_time_unit == 0

Assignment = namedtuple("Assignment", ["attention", "time"])


# Trivial Resorce considerations (for now)
def Resources(v):
    return set([]) #return {"oven"} if "bake" in v else set([])


def recipe2sat(chefs, vertices, edges,a, time_ub, time_unit=cooking_time_unit):
    time_slots = range(int(time_ub)*60 // time_unit + 0)
    print('timeslot[0] ==', time_slots[0])
    
    tuples = []
    for p in chefs:
        for v in vertices:
            #for i in range(len(a[v])):
                for t in time_slots:
                    tuples.append((p, t, v))

    tuple2idx = {tpl: idx for idx, tpl in enumerate(tuples, start=1)}
    #idx2tuple = {idx: tpl for tpl, idx in tuple2idx.items()}

    clauses = []

    print("1/6 process does single high attention task")
    for v, u in tqdm.tqdm(list(product(vertices, vertices))):
        #for i, j in product(range(len(a[v])), range(len(a[u]))):
            #if (u != v or i != j) and a[v][i].Attention and a[u][j].Attention:
            #print(u,v,a[v].attention,a[u].attention)
            if (u != v) and a[v].attention and a[u].attention:
                for t in time_slots:
                    for s in range(t, min(t + a[v].time, time_slots[-1] + 1)):
                        for p in chefs:
                            clauses.append(
                                [-tuple2idx[(p, t, v)], -tuple2idx[(p, s, u)]]
                            )


    print("2/6 resource can do one thing at a time")
    for (v, rv), (u, ru) in tqdm.tqdm(
        list(product([(v, rv) for v in vertices if (rv := Resources(v))], repeat=2))
    ):
        if v != u and ru & rv:
            for p1, p2, t in product(
                chefs, chefs, time_slots
            ):
                for s in range(t, min(t + a[v].time, time_slots[-1] + 1)):
                    clauses.append([-tuple2idx[p1, t, v], -tuple2idx[p2, s, u]])
                                              

    print("3/6 every vertex is done at least once")
    for v in tqdm.tqdm(vertices):
        #for i in range(len(a[v])):
            cls = []
            for p in chefs:
                for t in time_slots:
                    cls.append(tuple2idx[(p, t, v)])
            clauses.append(cls)


    print("4/6 every task is done at most once")
    for p, q in tqdm.tqdm(list(product(chefs, chefs))):
        for t, s in product(time_slots, time_slots):
            if p != q or t != s:
                for v in vertices:
                    #for i in range(len(a[v])):
                        clauses.append([-tuple2idx[(p, t, v)], -tuple2idx[(q, s, v)]])

    #print("5/6 the task are executed serially")
    #for v in tqdm.tqdm(Vertices):
    #    for i in range(len(a[v]) - 1):
    #        for p, q in product(Proc, Proc):
    #            for t, s in product(Times, Times):
    #                if s < t + a[v][i].time:
    #                    clauses.append(
    #                        [-tuple2idx[(p, t, v, i)], -tuple2idx[(q, s, v, i + 1)]]
    #                    )


    print("6/6 the task execution follows the graph structure")
    for v, u in tqdm.tqdm(edges):
        for t, s in product(time_slots, time_slots):
           # if s < t + a[v][len(a[v]) - 1].time:
             if s < t + a[v].time:
                for p, q in product(chefs, chefs):
                    clauses.append(
                        [-tuple2idx[(p, t, v)], -tuple2idx[(q, s, u)]]
                    )
    return clauses, tuples, tuple2idx



def satSolve(clauses, tuple2idx):
    '''Setup a SAT cryptosolver to solve the SAT cooking clauses, If a solution is found, returns the resulting cooking instructions as a list, if a solution is not found, return False'''
    s = Solver()
    for cls in tqdm.tqdm(clauses):
        s.add_clause(cls)
    sat, solution = s.solve()
    
    if sat:
        idx2tuple = {idx: tpl for tpl, idx in tuple2idx.items()}
        chosen_triples = [idx2tuple[i] for i, s in enumerate(solution) if s]
        return chosen_triples
        #print(            "\n".join(f"{p} {t / (60 // unit):.1f} '{v}'.{i}" for p, t, v, i in sorted(IDX)))
    else:
        return False


def run_with_timeout(f, args, timeout, default=None):
    ctx = multiprocessing.get_context('fork')
    q = ctx.Queue()
    def ff(f, args, q):
        ret = f(*args)
        q.put(ret)
        
    p = ctx.Process(target=ff, args=(f, args, q))
    p.start()
    try:
        ret = q.get(timeout=timeout)
    except queue.Empty:
        p.kill()
        return default
    p.join()
    return ret

    
def recipe2solve_with_timeout(chefs, vertices, edges,a, time_ub, timeout, time_unit=cooking_time_unit):
    clauses, tuples, tuple2idx = recipe2sat(chefs, vertices, edges,a, time_ub, time_unit)
    return run_with_timeout(satSolve, [clauses,tuple2idx], timeout)


def F(chefs, vertices, edges, a, timeout):
    return lambda time_ub: recipe2solve_with_timeout(chefs, vertices, edges,a, time_ub, timeout)



def recipe2solve_with_timeout(chefs, vertices, edges,a, time_ub, timeout, time_unit=cooking_time_unit):
    clauses, tuples, tuple2idx = recipe2sat(chefs, vertices, edges,a, time_ub, time_unit)
    return run_with_timeout(satSolve, [clauses,tuple2idx], timeout)


def F(chefs, vertices, edges, a, timeout):
    return lambda time_ub: recipe2solve_with_timeout(chefs, vertices, edges,a, time_ub, timeout)



def binarysearch(f,lb,ub):
    """the function search for an minimal input x between lb and ub for which f returns the value True"""
    while lb < ub:
        mid = (lb + ub) // 2
        new_ret = f(mid)
        if new_ret:
            ub = mid
            last_ret = new_ret
        else: 
            lb = mid + 1
    print("Final lb,ub = ",lb,ub)
    return last_ret



def solver(chefs, vertices, edges, a, timeout, ub, lb = 0):
    if lb < ub:
        return binarysearch(F(chefs, vertices, edges, a, timeout),lb,ub)
    else:
        print("Error: `lb` = ", lb, " is not smallar than `ub` = ", ub)
        return False
