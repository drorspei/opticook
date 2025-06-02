import multiprocessing
import queue
import tqdm
from subprocess import check_call
#!/usr/bin/env python
# coding: utf-8
# test2
from collections import namedtuple
from pycryptosat import Solver
from itertools import product

unit = 60
assert 60 % unit == 0
Times = range(int(2.05 * 60 * 60) // unit + 0)
Assignment = namedtuple("Assignment", ["Attention", "Pausable", "time"])

Proc = ["P1", "P2"][:1]
Vertices = [
    "measure 55gr cream cheese",
    "shred mozzarella 85gr",
    "beat egg",
    "measure 35gr almond flour",
    "mix cream cheese and mozzarella and microwave",
    "mix egg with almond flour, baking powder, garlic powder, italian seasoning",
    "measure 50gr cheddar",
    "stir in melted mozzarella until fully incorporated",
    "shred cheddar",
    "stir in cheddar",
    "shape into ball, cover",
    "chill for 30 minutes in refrigerator",
    "dust a cutting board with a handful of almond flour",
    "cut dough into 4 even pieces and roll each piece into a ball. cut each ball in half",
    "grease baking sheet",
    "place cut side down on baking sheet",
    "preheat oven to 220C",
    "bake 10-12 minutes, or until golden brown",
    "slice tomato",
    "wash basil",
    "assemble with goat cheese and pastrami",
]

Edges = [
    (Vertices[1 - 1], Vertices[5 - 1]),
    (Vertices[2 - 1], Vertices[5 - 1]),
    (Vertices[3 - 1], Vertices[6 - 1]),
    (Vertices[4 - 1], Vertices[6 - 1]),
    (Vertices[5 - 1], Vertices[8 - 1]),
    (Vertices[6 - 1], Vertices[8 - 1]),
    (Vertices[7 - 1], Vertices[9 - 1]),
    (Vertices[8 - 1], Vertices[10 - 1]),
    (Vertices[9 - 1], Vertices[10 - 1]),
    (Vertices[10 - 1], Vertices[11 - 1]),
    (Vertices[11 - 1], Vertices[12 - 1]),
    (Vertices[12 - 1], Vertices[14 - 1]),
    (Vertices[13 - 1], Vertices[14 - 1]),
    (Vertices[14 - 1], Vertices[16 - 1]),
    (Vertices[15 - 1], Vertices[16 - 1]),
    (Vertices[16 - 1], Vertices[18 - 1]),
    (Vertices[17 - 1], Vertices[18 - 1]),
    (Vertices[18 - 1], Vertices[21 - 1]),
    (Vertices[19 - 1], Vertices[21 - 1]),
    (Vertices[20 - 1], Vertices[21 - 1]),
]

a_secs = {
    Vertices[0]: [(True, False, 20)],
    Vertices[1]: [(True, False, 60)],
    Vertices[2]: [(True, False, 30)],
    Vertices[3]: [(True, False, 20)],
    Vertices[4]: [(True, False, 120)],
    Vertices[5]: [(True, False, 120)],
    Vertices[6]: [(True, False, 20)],
    Vertices[7]: [(True, False, 10)],
    Vertices[8]: [(True, False, 60)],
    Vertices[9]: [(True, False, 10)],
    Vertices[10]: [(True, False, 60)],
    Vertices[11]: [(False, False, 30 * 60)],
    Vertices[12]: [(True, False, 10)],
    Vertices[13]: [(True, False, 60)],
    Vertices[14]: [(True, False, 20)],
    Vertices[15]: [(True, False, 5)],
    Vertices[16]: [(False, False, 25 * 30)],
    Vertices[17]: [(False, False, 12 * 60)],
    Vertices[18]: [(True, False, 60)],
    Vertices[19]: [(True, False, 60)],
    Vertices[20]: [(True, False, 60)],
}


def Resources(v):
    return {"oven"} if "bake" in v else set([])


cc = open("./recipes/cheesecake2.txt").readlines()
Vertices, Edges, a = zip(
    *[
        (
            f"{i}. {v}",
            (int(i), int(e)),
            [
                (
                    not any(
                        w in v
                        for w in (
                            "bake",
                            "preheat",
                            "soften",
                            "put out",
                            "room temp",
                            "cool",
                            "simmer",
                            "refri",
                        )
                    ),
                    False,
                    int(t),
                )
            ],
        )
        for l in cc
        for i, v, t, e in [l.lower().split(";")]
    ]
)
Edges = [(Vertices[i], Vertices[j]) for i, j in Edges[:-1]]
a_secs = dict(zip(Vertices, a))
# print("\n".join(str(e) for e in Edges))


def double(Vertices, Edges, a):
    """make the recipe twice"""
    return (
        [f"{i} {v}" for i in (0, 1) for v in Vertices],
        [(f"{i} {u}", f"{i} {v}") for u, v in Edges for i in (0, 1)],
        {f"{i} {v}": x for i in (0, 1) for v, x in a.items()},
    )


# Vertices, Edges, a = double(Vertices, Edges, a)

# round time to minutes, change units to 30 seconds
a = {
    v: [Assignment(at, pa, ((t + 59) // 60) * (60 // unit)) for (at, pa, t) in tup]
    for v, tup in a_secs.items()
}
# print(a)
# exit(0)

def recipe2sat(Proc, Vertices, Times, Edges, a):
    '''transform a cooking data plus time suggestion into a SAT problem'''
    tuples = []
    for p in Proc:
        for v in Vertices:
            for i in range(len(a[v])):
                for t in Times:
                    tuples.append((p, t, v, i))

    tuple2idx = {tpl: idx for idx, tpl in enumerate(tuples, start=1)}
    #idx2tuple = {idx: tpl for tpl, idx in tuple2idx.items()}

    clauses = []

    print("1/6 process does single high attention task")
    for v, u in tqdm.tqdm(list(product(Vertices, Vertices))):
        for i, j in product(range(len(a[v])), range(len(a[u]))):
            if (u != v or i != j) and a[v][i].Attention and a[u][j].Attention:
                for t in Times:
                    for s in range(t, min(t + a[v][i].time, Times[-1] + 1)):
                        for p in Proc:
                            clauses.append(
                                [-tuple2idx[(p, t, v, i)], -tuple2idx[(p, s, u, j)]]
                            )

    print("2/6 resource can do one thing at a time")
    for (v, rv), (u, ru) in tqdm.tqdm(
        list(product([(v, rv) for v in Vertices if (rv := Resources(v))], repeat=2))
    ):
        if v != u and ru & rv:
            for p1, p2, t, i, j in product(
                Proc, Proc, Times, range(len(a[v])), range(len(a[u]))
            ):
                for s in range(t, min(t + a[v][i].time, Times[-1] + 1)):
                    clauses.append([-tuple2idx[p1, t, v, i], -tuple2idx[p2, s, u, j]])

    print("3/6 every vertex is done at least once")
    for v in tqdm.tqdm(Vertices):
        for i in range(len(a[v])):
            cls = []
            for p in Proc:
                for t in Times:
                    cls.append(tuple2idx[(p, t, v, i)])
            clauses.append(cls)


    print("4/6 every task is done at most once")
    for p, q in tqdm.tqdm(list(product(Proc, Proc))):
        for t, s in product(Times, Times):
            if p != q or t != s:
                for v in Vertices:
                    for i in range(len(a[v])):
                        clauses.append([-tuple2idx[(p, t, v, i)], -tuple2idx[(q, s, v, i)]])

    print("5/6 the task are executed serially")
    for v in tqdm.tqdm(Vertices):
        for i in range(len(a[v]) - 1):
            for p, q in product(Proc, Proc):
                for t, s in product(Times, Times):
                    if s < t + a[v][i].time:
                        clauses.append(
                            [-tuple2idx[(p, t, v, i)], -tuple2idx[(q, s, v, i + 1)]]
                        )


    print("6/6 the task execution follows the graph structure")
    for v, u in tqdm.tqdm(Edges):
        for t, s in product(Times, Times):
            if s < t + a[v][len(a[v]) - 1].time:
                for p, q in product(Proc, Proc):
                    clauses.append(
                        [-tuple2idx[(p, t, v, len(a[v]) - 1)], -tuple2idx[(q, s, u, 0)]]
                    )
    return clauses, tuples, tuple2idx


def sat2IDX(clauses, tuple2idx):
    '''Setup a SAT cryptosolver to solve the SAT cooking clauses, If a solution is found, returns the resulting cooking instructions as a list, if a solution is not found, return False'''
    s = Solver()
    for cls in tqdm.tqdm(clauses):
        s.add_clause(cls)
    sat, solution = s.solve()
    
    if sat:
        idx2tuple = {idx: tpl for tpl, idx in tuple2idx.items()}
        IDX = [idx2tuple[i] for i, s in enumerate(solution) if s]
        return IDX
        #print(            "\n".join(f"{p} {t / (60 // unit):.1f} '{v}'.{i}" for p, t, v, i in sorted(IDX)))
    else:
        return False
    
    
def binarysearch(f,lb,ub):
    """the function search for an minimal input x between lb and ub for which f returns the value True"""
    while lb < ub:
        mid = (lb + ub) // 2
        if f(mid):
            ub = mid
        else: 
            lb = mid + 1
    return lb


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


def time_per_task(assignment):
    if assignment.Attention:
        return assignment.time
    else:
        return 0
    
def time_upperbound(a):
    return sum(list(map(lambda x: time_per_task(x[0]), list(a.values()))))
    

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi import Request, Form
from fastapi.responses import RedirectResponse
from fastapi import Form
from session_manager import allocate_tasks
from session_manager import session_manager
from cooking.recipe_parser import parse_cooking_instructions

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """
    Event handler for application startup. Loads the session using SessionManager.
    """
    session = session_manager.get_session()

@app.get("/")
async def read_root(request: Request):
    """
    Render the index.html template with an empty textarea.
    """
    return templates.TemplateResponse("index.html", {"request": request, "textarea_content": ""})

@app.post("/recipe")
async def submit_recipe(recipe_text: str = Form(...)):
    """
    Receive recipe text from a form, parse it, store it in the session, and redirect to /chefs.
    """
    session = session_manager.get_session()
    session.recipe = parse_cooking_instructions(recipe_text)
    return RedirectResponse(url="/chefs", status_code=303)
@app.get("/chefs")
async def get_chefs(request: Request):
    """
    Render a form to enter chef names.
    """
    return templates.TemplateResponse("chefs.html", {"request": request})

@app.post("/chefs")
async def post_chefs(chef_names: str = Form(...)):
    """
    Receive chef names from a form, save them in the session, allocate tasks, and redirect to /cook.
    """
    session = session_manager.get_session()
    session.chefs = [name.strip() for name in chef_names.split(",")]
    allocate_tasks(session)
    return RedirectResponse(url="/cook", status_code=303)
