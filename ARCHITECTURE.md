# Architecture

Frontend --> Backend

We talk to sites in HTTP 1/2/3 (or later?)
Calling a page means sending over a tcp/ip socket something like this:

Abstract data:
  - Task is (description, duration, attention, dependencies)
  - Instructions is (task, chef)
  - A session is a list of done tasks, a list of unstarted tasks and their compilation to Instructions, which is a list of lists of items, and a list of pairs (cook,current task or null)
  - A chef is a name (later we might put in other stuff)

  A session is a "recipe" - list of ([number,] description, duration, attention, dependencies), list of done indices, current assignments Dict[chef, int], list of unstarted items Dict[chef, List[int]]

Computations:
  - Next instruction ( (session, chef) -> session ) - move current task to done tasks, and move an unstarted task to the current task of the chef
    * The chosen unstarted task can be interesting.
    * For the first version, we don't do anything interesting: take the next instruction for the chef.
  - Chef done washing hands/joins ( (session, new chef) -> session ) - compile unstarted tasks for one more chef, assign instruction to new chef, change session.
  - Chef leaves ( (session, chef) -> session ) - move chef current task to unstarted, recompile, and change session.
  - Total loss task ( (session, chef) -> session ) - if no diamonds, then recompile with ancesstors of task.

Actions:
  - Recipe to Session
  - Read from session store
  - Write to session store


Story:
  - Omer enters recipe
      UI calls Recipe to Session
      UI calls write session to store



***** first implementation ******
solely in python, in "backend" with jupyter notebook examples of usage, data+computations

Omer's assignment(s):
1. Write a python file that defines the data types (class) for Chef, Session, Instructions
2. In the file write the computations as free python functions
3. In a jupyter notebook write examples of initializing a Session object - either at the beginning of a Session _or not_ - then calls the computation, and shows the output




---------------------------------------------------------------------------------

      


Let's fill in backend endpoint details
-- Home --
  "/index.html"
  * History?
  * Enter url in Frontend
  - "/translate-to-tasks?url=https://gluten-free-cheesecakes/1.html"
backend calls LLM (say openai or local) to translate url to tasks
  "[{"text": "chop chop", "time": 7, "attention": true, "dependencies": [1, 2]}, ...]"
frontend shows tasks for inspection
maybe edit a bit:
  - each task is in a line with a select box on the left
  - user can select a few lines and then a "join" button
    backend gets "/edit/join?lines=1,3"
    and calls LLM to try to join, returns updated task lines
  - user can select a line and then "split further" button
    backend gets "/edit/split?line=3", then calls LLM to try to split and returns tasks
  - lets allow manual editing
click continue, which POSTs tasks to "/compile"
backend compiles tasks to instructions using SAT solver
backend "starts a session", with no cooks
redirected to "/join?session=ABEVC727BEY"
in join you enter session id

On frontend we see list of instructions
Current is in color (black, blue, red?), others greyed/phased out a bit
Current instruction is a button, when you click you proceed to next instruction
Instructions show text and a progress bar showing time passing (either going forward or running out)
"[ Chop carrots ###.........]"
"[ Chop carrots ####........]"
"[ Chop carrots #####.......]"
On each click we send to backend
  "/next-instruction"
this saves time and player name in db
Every 200ms we check
  "/cooking-state?session=ABEVC727BEY&cook=Dror"

There's also a "copy share link" button that user can click and then send over whatsapp or something
Other user goes there
  "/join?session=ABEVC727BEY"
Asks you for name, load default from cookie?
Then you are redirected to
  "/cooking-state?session=ABEVC727BEY&cook=Omer"

  backend reads from state the other cook positions
  take instructions that are left, and compile with new number of cooks
  save new state of all cooks and return to this cook

For single player, we don't need backend anymore
