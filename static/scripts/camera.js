const videoElement = document.getElementById("videoFeed");
const cameraSelect = document.getElementById("cameraSelect");
let stream;

async function getCameras() {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === 'videoinput');

    cameraSelect.innerHTML = '';
    videoDevices.forEach((device, index) => {
        const option = document.createElement('option');
        option.value = device.deviceId;
        option.text = device.label || `Camera ${index + 1}`;
        cameraSelect.appendChild(option);
    });

    if (videoDevices.length > 0) {
        startStream(videoDevices[0].deviceId);
    }
}

async function startStream(deviceId) {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }

    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { deviceId: { exact: deviceId } }
        });
        videoElement.srcObject = stream;
    } catch (err) {
        console.error('Error accessing camera:', err);
    }
}

cameraSelect.addEventListener('change', () => {
    startStream(cameraSelect.value);
});

getCameras();
