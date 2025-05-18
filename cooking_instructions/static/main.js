let socket;
const cards = new Map();

// show client ID
document.getElementById('who').textContent = window.clientId;

// fetch & render only tasks assigned to me
fetch("/tasks")
  .then(r => r.json())
  .then(all => {
    const mine = all.filter(t => t.assignedTo.includes(window.clientId));
    const container = document.getElementById("tasks");
    mine.forEach(t => {
      const card = document.createElement("div");
      card.className = "task-card";
      card.id = `task-${t.id}`;

      const name = document.createElement("div");
      name.className = "task-name";
      name.textContent = t.name;
      card.appendChild(name);

      const bar = document.createElement("progress");
      bar.className = "task-progress";
      bar.max = t.duration;
      bar.value = 0;
      bar.id = `progress-${t.id}`;
      card.appendChild(bar);

      container.appendChild(card);
      cards.set(t.id, { card, bar });
    });

    setupWebSocket();
    setupControls();
  });

// handle broadcasts, filtering by my clientId
function setupWebSocket() {
  socket = new WebSocket(`ws://${location.host}/ws`);
  socket.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    if (!msg.assignedTo?.includes(window.clientId)) return;

    const entry = cards.get(msg.taskId);
    if (!entry) return;

    const { card, bar } = entry;
    switch (msg.type) {
      case "start_task":
        card.classList.add("active");
        bar.max   = msg.duration;
        bar.value = 0;
        break;
      case "progress":
        bar.value = msg.elapsed;
        break;
      case "complete_task":
        card.classList.remove("active");
        bar.value = bar.max;
        break;
      case "all_tasks_complete":
        alert("All cooking steps are done!");
        break;
    }
  };
}

// wire the global controls
function setupControls() {
  document.getElementById("startBtn").onclick = () =>
    socket.send(JSON.stringify({ action: "start" }));
  document.getElementById("pauseBtn").onclick = () =>
    socket.send(JSON.stringify({ action: "pause" }));
  document.getElementById("skipBtn").onclick = () =>
    socket.send(JSON.stringify({ action: "skip" }));
}