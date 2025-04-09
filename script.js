const recordButton = document.getElementById('record');
const stopButton = document.getElementById('stop');
const uploadForm = document.getElementById('uploadForm');
const audioDataInput = document.getElementById('audioData');
const timerDisplay = document.getElementById('timer');
const pdfInput = document.getElementById('pdfInput');

let mediaRecorder;
let audioChunks = [];
let startTime;
let timerInterval;

function formatTime(time) {
  const minutes = Math.floor(time / 60);
  const seconds = Math.floor(time % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function showStatus(message) {
  let existing = document.getElementById('statusMsg');
  if (!existing) {
    const statusMsg = document.createElement('p');
    statusMsg.id = 'statusMsg';
    statusMsg.textContent = message;
    statusMsg.style.fontWeight = 'bold';
    statusMsg.style.color = 'green';
    uploadForm.appendChild(statusMsg);
  } else {
    existing.textContent = message;
  }
}

function removeStatus() {
  const msg = document.getElementById('statusMsg');
  if (msg) msg.remove();
}

recordButton.addEventListener('click', () => {
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.start();
      startTime = Date.now();
      timerDisplay.textContent = "00:00";
      recordButton.textContent = "Recording...";
      stopButton.textContent = "Stop";
      recordButton.disabled = true;
      stopButton.disabled = false;

      timerInterval = setInterval(() => {
        const elapsedTime = Math.floor((Date.now() - startTime) / 1000);
        timerDisplay.textContent = formatTime(elapsedTime);
      }, 1000);

      mediaRecorder.ondataavailable = e => {
        audioChunks.push(e.data);
      };

      mediaRecorder.onstop = () => {
        clearInterval(timerInterval);
        recordButton.textContent = "Record";

        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });

       
        if (audioBlob.size < 1000) {
          alert("Recording too short. Please record a longer question.");
          recordButton.disabled = false;
          stopButton.disabled = true;
          return;
        }

        const formData = new FormData();
        formData.append('audio_data', audioBlob, 'question.wav');

        const selectedPDF = pdfInput.files[0];
        if (!selectedPDF) {
          alert("Please select a PDF file first!");
          recordButton.disabled = false;
          stopButton.disabled = true;
          return;
        }
        formData.append('pdf_file', selectedPDF);

        showStatus("Processing your question...");

        fetch('/ask_about_book', {
          method: 'POST',
          body: formData
        })
        .then(response => {
          if (!response.ok) {
            throw new Error('Upload failed');
          }
          return response.text();
        })
        .then(data => {
          console.log('Uploaded successfully:', data);

          setTimeout(() => {
            removeStatus();
            window.location.reload();
          }, 1500);
        })
        .catch(error => {
          console.error('Upload error:', error);
          alert("There was an error uploading your audio.");
          removeStatus();
        });

        recordButton.disabled = false;
        stopButton.disabled = true;
      };
    })
    .catch(error => {
      console.error('Microphone access error:', error);
      alert("Microphone access denied or not available.");
    });
});

stopButton.addEventListener('click', () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    stopButton.disabled = true;
  }
});

// Disable Stop initially
stopButton.disabled = true;
