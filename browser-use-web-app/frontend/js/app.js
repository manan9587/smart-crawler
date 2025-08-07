const ws=new WebSocket(`ws://${location.host}/ws/agent-stream`);
ws.onmessage=e=>onMsg(JSON.parse(e.data));
function onMsg(d){
  if(d.type=="step"){log(d.message);updRes(d.results);}
  if(d.type=="status"){log("Status:"+d.status);updBtns(d.status);}
}
function log(m){
  const l=document.getElementById("log"),e=document.createElement("div");
  e.textContent=new Date().toLocaleTimeString()+": "+m; l.append(e);l.scrollTop=l.scrollHeight;
}
function updRes(r){
  const tb=document.querySelector("#results tbody");tb.innerHTML="";
  r.forEach(x=>tb.insertAdjacentHTML("beforeend",`<tr><td>${x.item}</td><td>${x.price}</td></tr>`));
}
function updBtns(s){
  start.disabled=s==="running";
  pause.disabled=s!=="running";
  resume.disabled=s!=="paused";
  stop.disabled=s==="idle";
}
["pause","resume","stop"].forEach(c=>document.getElementById(c).onclick=_=>fetch(`/api/v1/agent/${c}`,{method:"POST"}));
start.onclick=async()=>{
  const p={task:task.value,api_key:apiKey.value,llm_provider:provider.value,model:model.value};
  await fetch("/api/v1/agent/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)});
};
