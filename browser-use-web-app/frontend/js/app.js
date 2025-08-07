class BrowserAgentApp {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.initializeElements();
        this.setupEventListeners();
        this.connectWebSocket();
        this.updateModelOptions();
    }

    initializeElements() {
        // Control elements
        this.startBtn = document.getElementById('start-btn');
        this.pauseBtn = document.getElementById('pause-btn');
        this.resumeBtn = document.getElementById('resume-btn');
        this.stopBtn = document.getElementById('stop-btn');
        this.clearLogBtn = document.getElementById('clear-log');
        
        // Form elements
        this.llmProvider = document.getElementById('llm-provider');
        this.model = document.getElementById('model');
        this.apiKey = document.getElementById('api-key');
        this.url = document.getElementById('url');
        this.task = document.getElementById('task');
        
        // Display elements
        this.statusText = document.getElementById('status-text');
        this.statusDot = document.getElementById('status-dot');
        this.browserScreenshot = document.getElementById('browser-screenshot');
        this.screenshotOverlay = document.getElementById('screenshot-overlay');
        this.screenshotTimestamp = document.getElementById('screenshot-timestamp');
        this.logContainer = document.getElementById('log-container');
        this.connectionStatus = document.getElementById('connection-status');
        
        // Modal elements
        this.errorModal = document.getElementById('error-modal');
        this.errorMessage = document.getElementById('error-message');
        this.closeModal = document.querySelector('.close');
    }

    setupEventListeners() {
        // Control buttons
        this.startBtn.addEventListener('click', () => this.startAgent());
        this.pauseBtn.addEventListener('click', () => this.pauseAgent());
        this.resumeBtn.addEventListener('click', () => this.resumeAgent());
        this.stopBtn.addEventListener('click', () => this.stopAgent());
        this.clearLogBtn.addEventListener('click', () => this.clearLog());
        
        // LLM provider change
        this.llmProvider.addEventListener('change', () => this.updateModelOptions());
        
        // Modal close
        this.closeModal.addEventListener('click', () => this.hideModal());
        window.addEventListener('click', (event) => {
            if (event.target === this.errorModal) {
                this.hideModal();
            }
        });
        
        // Auto-save form data
        [this.llmProvider, this.model, this.apiKey, this.url, this.task].forEach(element => {
            element.addEventListener('change', () => this.saveFormData());
            element.addEventListener('input', () => this.saveFormData());
        });
        
        // Load saved form data
        this.loadFormData();
    }

    updateModelOptions() {
        const provider = this.llmProvider.value;
        const models = {
            'openai': ['gpt-4', 'gpt-4o', 'gpt-3.5-turbo'],
            'gemini': ['gemini-pro', 'gemini-pro-vision'],
            'anthropic': ['claude-3-sonnet', 'claude-3-haiku']
        };
        
        this.model.innerHTML = '';
        models[provider].forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            this.model.appendChild(option);
        });
    }

    saveFormData() {
        const formData = {
            llmProvider: this.llmProvider.value,
            model: this.model.value,
            apiKey: this.apiKey.value,
            url: this.url.value,
            task: this.task.value
        };
        localStorage.setItem('browserAgentForm', JSON.stringify(formData));
    }

    loadFormData() {
        try {
            const saved = localStorage.getItem('browserAgentForm');
            if (saved) {
                const formData = JSON.parse(saved);
                this.llmProvider.value = formData.llmProvider || 'openai';
                this.updateModelOptions();
                this.model.value = formData.model || 'gpt-4';
                this.apiKey.value = formData.apiKey || '';
                this.url.value = formData.url || 'https://example.com';
                this.task.value = formData.task || '';
            }
        } catch (e) {
            console.warn('Failed to load saved form data:', e);
        }
    }

    connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/agent-stream`;
            
            this.ws = new WebSocket(wsUrl);
            this.updateConnectionStatus('connecting');
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected');
                this.addLogEntry('info', 'Connected to server');
                this.startHeartbeat();
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket disconnected', event.code, event.reason);
                this.isConnected = false;
                this.stopHeartbeat();
                this.updateConnectionStatus('disconnected');
                this.addLogEntry('warning', 'Disconnected from server');
                this.attemptReconnect();
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.addLogEntry('error', 'Connection error');
            };
            
        } catch (e) {
            console.error('Failed to connect WebSocket:', e);
            this.updateConnectionStatus('disconnected');
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 10000);
            
            setTimeout(() => {
                if (!this.isConnected) {
                    console.log(`Reconnection attempt ${this.reconnectAttempts}`);
                    this.connectWebSocket();
                }
            }, delay);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'connected':
                this.updateStatus(data.status);
                break;
                
            case 'status':
                this.updateStatus(data.status);
                if (data.message) {
                    this.addLogEntry('info', data.message);
                }
                break;
                
            case 'step':
                this.addLogEntry('info', data.message);
                if (data.action) {
                    this.updateCurrentAction(data.action);
                }
                break;
                
            case 'screenshot':
                this.updateScreenshot(data.data, data.description);
                break;
                
            case 'error':
                this.addLogEntry('error', data.message);
                this.showError(data.message);
                break;
                
            case 'warning':
                this.addLogEntry('warning', data.message);
                break;
                
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    updateConnectionStatus(status) {
        const dot = this.connectionStatus.querySelector('.connection-dot');
        const text = this.connectionStatus.querySelector('span:last-child');
        
        dot.className = `connection-dot ${status}`;
        
        switch (status) {
            case 'connected':
                text.textContent = 'Connected';
                break;
            case 'connecting':
                text.textContent = 'Connecting...';
                break;
            case 'disconnected':
                text.textContent = 'Disconnected';
                break;
        }
    }

    updateStatus(status) {
        this.statusDot.className = `status-dot ${status}`;
        this.statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        
        // Update button states
        const isRunning = status === 'running';
        const isPaused = status === 'paused';
        const isIdle = status === 'idle' || status === 'completed' || status === 'error';
        
        this.startBtn.disabled = !isIdle;
        this.pauseBtn.disabled = !isRunning;
        this.resumeBtn.disabled = !isPaused;
        this.stopBtn.disabled = isIdle;
        
        // Show/hide overlay
        if (status === 'running' || status === 'paused') {
            this.screenshotOverlay.style.display = 'none';
        } else if (status === 'idle') {
            this.screenshotOverlay.style.display = 'flex';
            this.screenshotOverlay.innerHTML = '<div class="loading-spinner"></div><p>Waiting for browser...</p>';
        }
    }

    updateCurrentAction(action) {
        // Update the header or add visual indicator of current action
        const actionIndicator = document.querySelector('.current-action') || 
            this.createActionIndicator();
        actionIndicator.textContent = action;
    }

    createActionIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'current-action';
        indicator.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #2563eb;
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 0.9rem;
            z-index: 100;
        `;
        document.body.appendChild(indicator);
        return indicator;
    }

    updateScreenshot(imageData, description = '') {
        this.browserScreenshot.src = imageData;
        this.screenshotOverlay.style.display = 'none';
        
        if (description) {
            this.screenshotTimestamp.textContent = `- ${description}`;
        } else {
            this.screenshotTimestamp.textContent = `- ${new Date().toLocaleTimeString()}`;
        }
    }

    addLogEntry(type, message) {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        
        const timestamp = document.createElement('span');
        timestamp.className = 'timestamp';
        timestamp.textContent = new Date().toLocaleTimeString();
        
        const messageSpan = document.createElement('span');
        messageSpan.className = 'message';
        messageSpan.textContent = message;
        
        entry.appendChild(timestamp);
        entry.appendChild(messageSpan);
        
        this.logContainer.appendChild(entry);
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
    }

    clearLog() {
        this.logContainer.innerHTML = '<div class="log-entry info"><span class="timestamp">Ready</span><span class="message">Log cleared</span></div>';
    }

    async startAgent() {
        if (!this.validateForm()) {
            return;
        }
        
        const taskData = {
            task: this.task.value.trim(),
            api_key: this.apiKey.value.trim(),
            llm_provider: this.llmProvider.value,
            model: this.model.value,
            context: {
                url: this.url.value.trim()
            },
            headless: false,
            max_steps: 50,
            timeout: 120
        };
        
        try {
            const response = await fetch('/api/v1/agent/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(taskData)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to start agent');
            }
            
            const result = await response.json();
            this.addLogEntry('success', `Agent started with task ID: ${result.task_id}`);
            
        } catch (error) {
            console.error('Error starting agent:', error);
            this.showError(`Failed to start agent: ${error.message}`);
            this.addLogEntry('error', error.message);
        }
    }

    async pauseAgent() {
        try {
            const response = await fetch('/api/v1/agent/pause', { method: 'POST' });
            if (!response.ok) throw new Error('Failed to pause agent');
            
            this.addLogEntry('info', 'Agent paused');
        } catch (error) {
            this.showError(`Failed to pause agent: ${error.message}`);
        }
    }

    async resumeAgent() {
        try {
            const response = await fetch('/api/v1/agent/resume', { method: 'POST' });
            if (!response.ok) throw new Error('Failed to resume agent');
            
            this.addLogEntry('info', 'Agent resumed');
        } catch (error) {
            this.showError(`Failed to resume agent: ${error.message}`);
        }
    }

    async stopAgent() {
        try {
            const response = await fetch('/api/v1/agent/stop', { method: 'POST' });
            if (!response.ok) throw new Error('Failed to stop agent');
            
            this.addLogEntry('info', 'Agent stopped');
        } catch (error) {
            this.showError(`Failed to stop agent: ${error.message}`);
        }
    }

    validateForm() {
        const apiKey = this.apiKey.value.trim();
        const task = this.task.value.trim();
        const url = this.url.value.trim();
        
        if (!apiKey) {
            this.showError('Please enter your API key');
            this.apiKey.focus();
            return false;
        }
        
        if (!task) {
            this.showError('Please enter a task description');
            this.task.focus();
            return false;
        }
        
        if (!url || !this.isValidUrl(url)) {
            this.showError('Please enter a valid URL');
            this.url.focus();
            return false;
        }
        
        return true;
    }

    isValidUrl(string) {
        try {
            new URL(string.startsWith('http') ? string : 'https://' + string);
            return true;
        } catch (e) {
            return false;
        }
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorModal.style.display = 'block';
    }

    hideModal() {
        this.errorModal.style.display = 'none';
    }

    sendWebSocketMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }

    // Keep connection alive
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            this.sendWebSocketMessage({ type: 'ping' });
        }, 30000); // Ping every 30 seconds
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
}

// Global functions for example prompts
function fillExampleTask(element) {
    const taskTextarea = document.getElementById('task');
    taskTextarea.value = element.textContent.trim();
    taskTextarea.focus();
    
    // Save the updated value
    app.saveFormData();
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new BrowserAgentApp();
});