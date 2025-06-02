document.addEventListener("DOMContentLoaded", function() {
    function tickTimers() {
        document.querySelectorAll('[id^="timer-"]').forEach(timer => {
            let time = parseInt(timer.textContent);
            if (time > 0) {
                timer.textContent = time - 1;
            } else if (time === 0) {
                notifyOrBeep();
                timer.textContent = "Time's up!";
            }
        });
    }

    function notifyOrBeep() {
        if (Notification.permission === "granted") {
            new Notification("Time's up!");
        } else if (Notification.permission !== "denied") {
            Notification.requestPermission().then(permission => {
                if (permission === "granted") {
                    new Notification("Time's up!");
                } else {
                    playBeep();
                }
            });
        } else {
            playBeep();
        }
    }

    function playBeep() {
        new Audio('/static/beep.mp3').play();
    }

    setInterval(tickTimers, 1000);
});
