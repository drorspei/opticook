# opticook

A near optimal scheduling solver with a focus on parallelizing multiprocess resource-limited cooking.

## roadmap

- [x] generate SAT clauses
- [x] solve SAT problem with an external solver - minicryptosat
- [ ] add binary search to find (near) optimal time
- [ ] add attention per row to the current file format, add it in `recipes/cheesecake2.txt`
- [ ] pass arguments: `python main.py recipegraph.txt [--procs=1]`, use `argparse`
- [ ] visualize output in a nice graph (networkx+dot ?)
- [ ] extract attention maps out of recipes
- [ ] process for converting free text to task graph
- [ ] get the recipe free text from a given url automatically
- [ ] process for getting times per task-processor
- [ ] add cleaning
- [ ] make as (web)app that let's you colabo-cook™
- [ ] optimize some algorithm, meaning compile assembly code
