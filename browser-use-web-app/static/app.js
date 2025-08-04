class BrowserUseClient {
  constructor() {
    this.ws = null;
    this.results = [];
    this.imageData = null;
    this.uploadFileObj = {};
    this.init();
  }
  init() {
    this.connectWS();
    this.bindUI();
  }
  connectWS() {
    this.ws = new WebSocket(`ws://${location.host}/ws/agent-stream`);
    this.ws.onmessage = e => this.onMessage(JSON.parse(e.data));
  }
  bindUI() {
    document.getElementById('start-btn').onclick=() => this.start();
    document.getElementById('pause-btn').onclick=() => this.cmd('pause');
    document.getElementById('continue-btn').onclick=() => this.cmd('resume');
    document.getElementById('stop-btn').onclick=() => this.cmd('stop');
    document.getElementById('file-input').onchange=e => this.handleFile(e.target.files[0]);
    document.getElementById('image-input').onchange=e => this.handleImage(e.target.files[0]);
  }
  async start() {
    const task = document.getElementById('task-prompt').value.trim();
    if (!task) { alert('Enter prompt'); return; }
    const fileCtx = this.uploadFileObj;
    const imgCtx = this.imageData ? { image: this.imageData } : {};
    const resp = await fetch('/api/v1/agent/start', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ task, context:{...fileCtx,...imgCtx} })
    });
    if (resp.ok) this.updateBtns('running');
  }
  async handleFile(file) {
    if (!file) return;
    const f=new FormData(); f.append('file',file);
    const r=await fetch('/api/v1/upload',{method:'POST',body:f});
    const j=await r.json();
    this.uploadFileObj={ document:j.text_content, filename:j.filename };
  }
  handleImage(file) {
    if (!file.type.startsWith('image/')) { alert('Image only'); return; }
    const r=new FileReader();
    r.onload=e => {
      this.imageData = e.target.result;
      const img = document.getElementById('image-preview');
      img.src = this.imageData; img.style.display = 'block';
    };
    r.readAsDataURL(file);
  }
  async cmd(c) { 
    await fetch(`/api/v1/agent/${c}`, {method:'POST'}); 
    this.updateBtns(c==='pause'?'paused':'running'); 
  }
  onMessage(d) {
  if (d.type === 'step') {
    if (d.message) this.log(d.message);
    if (d.screenshot) document.getElementById('browser-screenshot').src = d.screenshot;
    if (d.results) {
      this.results = d.results;
      this.showResults();
    }
  }
  else if (d.type === 'status') {
    this.updateBtns(d.status);
    this.log(`Status: ${d.status}`);
  }
}
  log(m) {
    const l = document.getElementById('progress-log'), e = document.createElement('div');
    e.textContent = `${new Date().toLocaleTimeString()}: ${m}`;
    l.appendChild(e); l.scrollTop = l.scrollHeight;
  }
  showResults() {
    const t = document.querySelector('#results-table tbody');
    t.innerHTML = '';
    this.results.forEach(r => {
      t.insertAdjacentHTML('beforeend', `
        <tr>
          <td>${r.item || ''}</td>
          <td>${r.description || ''}</td>
          <td>${r.price || ''}</td>
          <td><a href="${r.url || '#'}" target="_blank">${r.url || ''}</a></td>
        </tr>
      `);
    });
  }
  updateBtns(state) {
  const startBtn = document.getElementById('start-btn');
  const pauseBtn = document.getElementById('pause-btn');
  const continueBtn = document.getElementById('continue-btn');
  const stopBtn = document.getElementById('stop-btn');

  switch(state) {
    case 'running':
      startBtn.disabled = true;
      pauseBtn.disabled = false;
      continueBtn.disabled = true;
      stopBtn.disabled = false;
      break;
    case 'paused':
      startBtn.disabled = true;
      pauseBtn.disabled = true;
      continueBtn.disabled = false;
      stopBtn.disabled = false;
      break;
    case 'idle': // Stopped or reset state
    default:
      startBtn.disabled = false;
      pauseBtn.disabled = true;
      continueBtn.disabled = true;
      stopBtn.disabled = true;
  }
}

window.browserUseClient = new BrowserUseClient();

function exportCSV() {
  const csv = window.browserUseClient.results.map(r => [r.item, r.description, r.price, r.url]
    .map(v => `"${v || ''}"`).join(',')).join('\n');
  const b = new Blob([csv], { type: 'text/csv' }), u = URL.createObjectURL(b), a = document.createElement('a');
  a.href = u; a.download = 'results.csv'; a.click();
}

function exportJSON() {
  const b = new Blob([JSON.stringify(window.browserUseClient.results, null, 2)], { type: 'application/json' }), u = URL.createObjectURL(b), a = document.createElement('a');
  a.href = u; a.download = 'results.json'; a.click();
}
