class BrowserUseClient {
  constructor() {
    this.ws = null;
    this.results = [];
    this.imageData = null;
    this.uploadFileObj = {};
    this.wsReconnectInterval = null;
    this.init();
  }

  init() {
    this.connectWS();
    this.bindUI();
    // Clear any existing logs
    document.getElementById('progress-log').innerHTML = '';
    this.log('System ready');
  }

  connectWS() {
    try {
      // Use ws:// or wss:// based on current protocol
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/agent-stream`;
      
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.log('Connected to server');
        if (this.wsReconnectInterval) {
          clearInterval(this.wsReconnectInterval);
          this.wsReconnectInterval = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onMessage(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.log('Connection error - retrying...');
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.log('Disconnected from server - reconnecting...');
        // Attempt to reconnect every 3 seconds
        if (!this.wsReconnectInterval) {
          this.wsReconnectInterval = setInterval(() => this.connectWS(), 3000);
        }
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      this.log('Failed to connect - retrying...');
    }
  }

  bindUI() {
    document.getElementById('start-btn').onclick = () => this.start();
    document.getElementById('pause-btn').onclick = () => this.pause();
    document.getElementById('continue-btn').onclick = () => this.resume();
    document.getElementById('stop-btn').onclick = () => this.stop();
    document.getElementById('file-input').onchange = (e) => this.handleFile(e.target.files[0]);
    document.getElementById('image-input').onchange = (e) => this.handleImage(e.target.files[0]);
  }

  async start() {
    const task = document.getElementById('task-prompt').value.trim();
    if (!task) {
      alert('Please enter a task');
      return;
    }

    const model = document.getElementById('model-select').value;
    this.log(`Starting task with ${model}: ${task}`);
    this.results = []; // Clear previous results
    this.showResults(); // Clear table
    
    // Prepare context
    const context = { ...this.uploadFileObj };
    
    // Prepare request body
    const body = {
      task: task,
      model: model,
      context: context
    };
    
    // Add image if uploaded
    if (this.imageData) {
      body.image = this.imageData;
    }

    try {
      const response = await fetch('/api/v1/agent/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      if (response.ok) {
        const data = await response.json();
        this.log(`Task started with ID: ${data.task_id}`);
        this.updateButtons('running');
      } else {
        const error = await response.text();
        this.log(`Failed to start: ${error}`);
      }
    } catch (e) {
      this.log(`Error starting task: ${e.message}`);
    }
  }

  async pause() {
    this.log('Pausing agent...');
    try {
      const response = await fetch('/api/v1/agent/pause', { method: 'POST' });
      if (!response.ok) {
        const error = await response.text();
        this.log(`Failed to pause: ${error}`);
      }
    } catch (e) {
      this.log(`Error pausing: ${e.message}`);
    }
  }

  async resume() {
    this.log('Resuming agent...');
    try {
      const response = await fetch('/api/v1/agent/resume', { method: 'POST' });
      if (!response.ok) {
        const error = await response.text();
        this.log(`Failed to resume: ${error}`);
      }
    } catch (e) {
      this.log(`Error resuming: ${e.message}`);
    }
  }

  async stop() {
    this.log('Stopping agent...');
    try {
      const response = await fetch('/api/v1/agent/stop', { method: 'POST' });
      if (response.ok) {
        this.log('Agent stopped');
        this.updateButtons('idle');
      } else {
        const error = await response.text();
        this.log(`Failed to stop: ${error}`);
      }
    } catch (e) {
      this.log(`Error stopping: ${e.message}`);
    }
  }

  async handleFile(file) {
    if (!file) return;
    
    this.log(`Uploading file: ${file.name}`);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/v1/upload', {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        this.uploadFileObj = {
          document: data.text_content,
          filename: data.filename
        };
        this.log(`File uploaded: ${data.filename}`);
      } else {
        this.log('Failed to upload file');
      }
    } catch (e) {
      this.log(`Error uploading file: ${e.message}`);
    }
  }

  handleImage(file) {
    if (!file || !file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      this.imageData = e.target.result;
      const preview = document.getElementById('image-preview');
      preview.src = this.imageData;
      preview.style.display = 'block';
      this.log(`Image loaded: ${file.name}`);
    };
    reader.readAsDataURL(file);
  }

  onMessage(data) {
    console.log('WebSocket message:', data);

    switch (data.type) {
      case 'connected':
        this.updateButtons(data.status);
        break;

      case 'status':
        this.updateButtons(data.status);
        this.log(`Status: ${data.status}`);
        if (data.message) {
          this.log(data.message);
        }
        break;

      case 'step':
        if (data.message) {
          this.log(data.message);
        }
        if (data.url) {
          this.log(`URL: ${data.url}`);
        }
        if (data.screenshot) {
          const screenshot = document.getElementById('browser-screenshot');
          screenshot.src = data.screenshot;
          screenshot.style.display = 'block';
        }
        if (data.results && data.results.length > 0) {
          this.results = data.results;
          this.showResults();
        }
        break;

      case 'error':
        this.log(`ERROR: ${data.message}`);
        this.updateButtons('idle');
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  }

  log(message) {
    const logContainer = document.getElementById('progress-log');
    const entry = document.createElement('div');
    entry.style.marginBottom = '5px';
    
    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `<span style="color: #8AB4F8">[${timestamp}]</span> ${message}`;
    
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
  }

  showResults() {
    const tbody = document.querySelector('#results-table tbody');
    tbody.innerHTML = '';

    this.results.forEach((result) => {
      const row = tbody.insertRow();
      row.insertCell(0).textContent = result.item || result.title || result.name || '-';
      row.insertCell(1).textContent = result.description || result.content || '-';
      row.insertCell(2).textContent = result.price || result.value || '-';
      
      const urlCell = row.insertCell(3);
      if (result.url || result.link) {
        const link = document.createElement('a');
        link.href = result.url || result.link;
        link.target = '_blank';
        link.textContent = 'Link';
        link.style.color = '#8AB4F8';
        urlCell.appendChild(link);
      } else {
        urlCell.textContent = '-';
      }
    });
  }

  updateButtons(status) {
    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const continueBtn = document.getElementById('continue-btn');
    const stopBtn = document.getElementById('stop-btn');

    // Reset all buttons first
    startBtn.disabled = true;
    pauseBtn.disabled = true;
    continueBtn.disabled = true;
    stopBtn.disabled = true;

    switch (status) {
      case 'idle':
      case 'completed':
        startBtn.disabled = false;
        break;
      case 'running':
        pauseBtn.disabled = false;
        stopBtn.disabled = false;
        break;
      case 'paused':
        continueBtn.disabled = false;
        stopBtn.disabled = false;
        break;
    }
  }
}

// Initialize client when page loads
let browserUseClient;
window.addEventListener('DOMContentLoaded', () => {
  browserUseClient = new BrowserUseClient();
});

// Export functions
function exportCSV() {
  if (!browserUseClient || browserUseClient.results.length === 0) {
    alert('No results to export');
    return;
  }

  const headers = ['Item', 'Description', 'Price', 'URL'];
  const rows = browserUseClient.results.map(r => [
    r.item || r.title || r.name || '',
    r.description || r.content || '',
    r.price || r.value || '',
    r.url || r.link || ''
  ]);

  let csv = headers.join(',') + '\n';
  rows.forEach(row => {
    csv += row.map(cell => `"${cell}"`).join(',') + '\n';
  });

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `results_${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportJSON() {
  if (!browserUseClient || browserUseClient.results.length === 0) {
    alert('No results to export');
    return;
  }

  const json = JSON.stringify(browserUseClient.results, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `results_${new Date().toISOString().split('T')[0]}.json`;
  a.click();
  URL.revokeObjectURL(url);
}