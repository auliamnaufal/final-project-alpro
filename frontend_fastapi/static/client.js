document.addEventListener("DOMContentLoaded", () => {

    const video = document.getElementById("cam");
    const canvas = document.getElementById("bbox");
    const ctx = canvas.getContext("2d");

    const statusText = document.getElementById("status");
    const latestImg = document.getElementById("latest");

    const ws = new WebSocket("ws://127.0.0.1:8000/yolo");

    // OPEN CAMERA
    navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
        video.srcObject = stream;

        const tmp = document.createElement("canvas");
        const tmpCtx = tmp.getContext("2d");

        setInterval(() => {

            if (video.videoWidth === 0 || video.videoHeight === 0) return;

            tmp.width = video.videoWidth;
            tmp.height = video.videoHeight;

            tmpCtx.drawImage(video, 0, 0);
            const frame = tmp.toDataURL("image/jpeg", 0.5);
            ws.send(frame);

        }, 150);

    }).catch(err => {
        console.log("Camera error:", err);
        alert("Browser blokir kamera. Izinkan dulu!");
    });

    // RECEIVE RESULT FROM BACKEND
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        statusText.innerText =
            `Person: ${msg.person}, Pelanggaran: ${msg.violation}`;

        if (msg.screenshot) {
            latestImg.src = "/" + msg.screenshot + "?t=" + Date.now();
        }

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        msg.boxes.forEach((box, idx) => {
            const cls = msg.classes[idx];
            ctx.strokeStyle = cls === "helmet" ? "green" : "red";
            ctx.lineWidth = 2;
            ctx.strokeRect(box[0], box[1], box[2]-box[0], box[3]-box[1]);
        });
    };
});
