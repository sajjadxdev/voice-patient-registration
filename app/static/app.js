// Voice AI Patient Registration - Client Dashboard & Voice Simulator

let conversationHistory = [
  {
    role: "assistant",
    content: "Hi! Thank you for calling Oakwood Health Clinic. I'm Sarah, your patient intake coordinator. I can help register you as a new patient today. Could I have your first and last name to get started?"
  }
];

let speechRecognition = null;
let isListening = false;
let ttsEnabled = true;

// DOM Elements
const dialogueContainer = document.getElementById("dialogueContainer");
const micBtn = document.getElementById("micBtn");
const micBtnText = document.getElementById("micBtnText");
const ttsToggleBtn = document.getElementById("ttsToggleBtn");
const ttsIcon = document.getElementById("ttsIcon");
const textInputForm = document.getElementById("textInputForm");
const userInputText = document.getElementById("userInputText");
const resetCallBtn = document.getElementById("resetCallBtn");
const agentStatusBadge = document.getElementById("agentStatusBadge");
const agentStatusText = document.getElementById("agentStatusText");
const agentToolBadge = document.getElementById("agentToolBadge");
const simCallerPhone = document.getElementById("simCallerPhone");

// Table DOM Elements
const patientsTableBody = document.getElementById("patientsTableBody");
const totalPatientsCount = document.getElementById("totalPatientsCount");
const recordCountLabel = document.getElementById("recordCountLabel");
const refreshBtn = document.getElementById("refreshBtn");
const searchLastName = document.getElementById("searchLastName");
const searchPhone = document.getElementById("searchPhone");
const searchDOB = document.getElementById("searchDOB");

// Modal Elements
const patientDetailModal = document.getElementById("patientDetailModal");
const modalPatientName = document.getElementById("modalPatientName");
const modalPatientContent = document.getElementById("modalPatientContent");
const closeDetailModal = document.getElementById("closeDetailModal");

// Initialize Speech Recognition if supported
function initSpeechRecognition() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    console.warn("Speech recognition not supported in this browser.");
    micBtnText.textContent = "Microphone Not Supported (Use Text Input)";
    micBtn.disabled = true;
    micBtn.classList.add("opacity-60", "cursor-not-allowed");
    return;
  }

  speechRecognition = new SpeechRec();
  speechRecognition.continuous = false;
  speechRecognition.interimResults = false;
  speechRecognition.lang = "en-US";

  speechRecognition.onstart = () => {
    isListening = true;
    micBtn.classList.add("ring-4", "ring-sky-400", "bg-sky-500");
    micBtnText.textContent = "Listening to you speak...";
  };

  speechRecognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    console.log("Transcribed speech:", transcript);
    handleUserUtterance(transcript);
  };

  speechRecognition.onerror = (event) => {
    console.error("Speech recognition error:", event.error);
    stopListening();
  };

  speechRecognition.onend = () => {
    stopListening();
  };
}

function startListening() {
  if (!speechRecognition) return;
  try {
    speechRecognition.start();
  } catch (e) {
    console.warn(e);
  }
}

function stopListening() {
  isListening = false;
  micBtn.classList.remove("ring-4", "ring-sky-400", "bg-sky-500");
  micBtnText.textContent = "Click to Speak (Microphone)";
}

// Speak Assistant Response via SpeechSynthesis
function speakAssistantResponse(text) {
  if (!ttsEnabled || !window.speechSynthesis) return;

  window.speechSynthesis.cancel(); // Stop prior speech
  // Clean markdown bullets or formatting before speaking
  const cleanSpeechText = text
    .replace(/[•\*\-]/g, "")
    .replace(/\n+/g, ". ")
    .replace(/\s+/g, " ");

  const utterance = new SpeechSynthesisUtterance(cleanSpeechText);
  utterance.rate = 1.0;
  utterance.pitch = 1.05;

  // Prefer a natural English female voice if available
  const voices = window.speechSynthesis.getVoices();
  const femaleVoice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Female") || v.name.includes("Samantha") || v.name.includes("Natural") || v.name.includes("Google")));
  if (femaleVoice) {
    utterance.voice = femaleVoice;
  }

  window.speechSynthesis.speak(utterance);
}

// Render Bubble in Chat UI
function appendChatBubble(role, text) {
  const isAssistant = role === "assistant";
  const div = document.createElement("div");
  div.className = `flex items-start space-x-2.5 ${isAssistant ? "" : "flex-row-reverse space-x-reverse"}`;

  const iconHtml = isAssistant
    ? `<div class="w-7 h-7 rounded-full bg-sky-600/30 text-sky-400 border border-sky-500/40 flex items-center justify-center text-xs shrink-0 mt-0.5"><i class="fa-solid fa-user-nurse"></i></div>`
    : `<div class="w-7 h-7 rounded-full bg-indigo-600/30 text-indigo-400 border border-indigo-500/40 flex items-center justify-center text-xs shrink-0 mt-0.5"><i class="fa-solid fa-phone"></i></div>`;

  const bubbleHtml = `
    <div class="${isAssistant ? "bg-slate-900 text-slate-200 border-slate-800" : "bg-sky-950 text-sky-100 border-sky-800/80"} border rounded-2xl ${isAssistant ? "rounded-tl-none" : "rounded-tr-none"} p-3.5 text-xs leading-relaxed max-w-[85%] shadow">
      <span class="font-semibold ${isAssistant ? "text-sky-400" : "text-indigo-400"} block mb-1">
        ${isAssistant ? "Sarah (Intake Coordinator):" : "Caller:"}
      </span>
      ${text.replace(/\n/g, "<br>")}
    </div>
  `;

  div.innerHTML = isAssistant ? iconHtml + bubbleHtml : bubbleHtml + iconHtml;
  dialogueContainer.appendChild(div);
  dialogueContainer.scrollTop = dialogueContainer.scrollHeight;
}

// Send user utterance to backend agent
async function handleUserUtterance(text) {
  if (!text || !text.trim()) return;

  const userText = text.trim();
  appendChatBubble("user", userText);
  conversationHistory.push({ role: "user", content: userText });

  // Show status
  agentStatusBadge.classList.remove("hidden");
  agentStatusText.textContent = "Sarah is thinking...";
  agentToolBadge.classList.add("hidden");

  try {
    const callerPhone = simCallerPhone.value.trim();
    const res = await fetch("/voice/simulate/turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: conversationHistory,
        caller_phone: callerPhone
      })
    });

    const data = await res.json();
    if (data.data) {
      const reply = data.data.reply;
      const tools = data.data.tool_calls_executed || [];
      const completed = data.data.is_completed;

      // Show tools executed if any
      if (tools.length > 0) {
        agentToolBadge.textContent = tools.map(t => t.tool).join(", ");
        agentToolBadge.classList.remove("hidden");
      }

      appendChatBubble("assistant", reply);
      conversationHistory.push({ role: "assistant", content: reply });
      speakAssistantResponse(reply);

      if (completed) {
        // Automatically refresh patient table to show newly saved record!
        loadPatients();
      }
    }
  } catch (err) {
    console.error("Error communicating with voice agent:", err);
    appendChatBubble("assistant", "I'm sorry, I encountered a temporary connection issue. Could you please repeat that?");
  } finally {
    setTimeout(() => {
      agentStatusBadge.classList.add("hidden");
    }, 2000);
  }
}

// Fetch & render patients table
async function loadPatients() {
  const lastName = searchLastName.value.trim();
  const phone = searchPhone.value.trim();
  const dob = searchDOB.value.trim();

  const params = new URLSearchParams();
  if (lastName) params.append("last_name", lastName);
  if (phone) params.append("phone_number", phone);
  if (dob) params.append("date_of_birth", dob);

  try {
    const res = await fetch(`/patients?${params.toString()}`);
    const json = await res.json();

    if (json.data) {
      renderPatientsTable(json.data);
    }
  } catch (err) {
    console.error("Error fetching patients:", err);
  }
}

function renderPatientsTable(patients) {
  totalPatientsCount.textContent = patients.length;
  recordCountLabel.textContent = `Showing ${patients.length} record${patients.length === 1 ? "" : "s"}`;

  if (patients.length === 0) {
    patientsTableBody.innerHTML = `
      <tr>
        <td colspan="6" class="px-4 py-8 text-center text-slate-500">
          No patients found matching the criteria.
        </td>
      </tr>
    `;
    return;
  }

  patientsTableBody.innerHTML = patients.map(p => `
    <tr class="hover:bg-slate-900/60 transition group">
      <td class="px-4 py-3">
        <div class="font-medium text-white">${escapeHtml(p.first_name)} ${escapeHtml(p.last_name)}</div>
        <div class="text-[10px] text-slate-500 font-mono">ID: ${p.patient_id.slice(0, 8)}...</div>
      </td>
      <td class="px-4 py-3">
        <div>${escapeHtml(p.date_of_birth)}</div>
        <span class="inline-block mt-0.5 px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 font-medium">${escapeHtml(p.sex)}</span>
      </td>
      <td class="px-4 py-3 font-mono text-sky-300">
        ${escapeHtml(p.phone_number)}
        ${p.email ? `<div class="text-[10px] text-slate-400 font-sans">${escapeHtml(p.email)}</div>` : ""}
      </td>
      <td class="px-4 py-3">
        <div>${escapeHtml(p.address_line_1)}</div>
        <div class="text-[10px] text-slate-400">${escapeHtml(p.city)}, ${escapeHtml(p.state)} ${escapeHtml(p.zip_code)}</div>
      </td>
      <td class="px-4 py-3">
        ${p.insurance_provider ? `<span class="text-emerald-400 font-medium">${escapeHtml(p.insurance_provider)}</span>` : '<span class="text-slate-500 italic">Self-Pay / None</span>'}
        ${p.insurance_member_id ? `<div class="text-[10px] text-slate-500 font-mono">${escapeHtml(p.insurance_member_id)}</div>` : ""}
      </td>
      <td class="px-4 py-3 text-right space-x-1">
        <button onclick="viewPatientDetails('${p.patient_id}')" class="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-sky-400 transition" title="View Full Details">
          <i class="fa-solid fa-eye"></i>
        </button>
        <button onclick="softDeletePatient('${p.patient_id}')" class="p-1.5 rounded hover:bg-rose-950/40 text-slate-400 hover:text-rose-400 transition" title="Soft Delete">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </td>
    </tr>
  `).join("");
}

// View Details Modal
window.viewPatientDetails = async function(patientId) {
  try {
    const res = await fetch(`/patients/${patientId}`);
    const json = await res.json();
    if (!json.data) return;

    const p = json.data;
    modalPatientName.innerHTML = `<i class="fa-solid fa-id-card text-sky-400"></i> ${escapeHtml(p.first_name)} ${escapeHtml(p.last_name)}`;

    modalPatientContent.innerHTML = `
      <div class="grid grid-cols-2 gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800">
        <div><span class="text-slate-500">Patient ID:</span> <div class="font-mono text-slate-300">${p.patient_id}</div></div>
        <div><span class="text-slate-500">Registered Date (UTC):</span> <div class="text-slate-300">${p.created_at}</div></div>
        <div><span class="text-slate-500">Date of Birth:</span> <div class="text-slate-300">${p.date_of_birth}</div></div>
        <div><span class="text-slate-500">Sex:</span> <div class="text-slate-300">${p.sex}</div></div>
        <div><span class="text-slate-500">Phone:</span> <div class="text-sky-400 font-mono">${p.phone_number}</div></div>
        <div><span class="text-slate-500">Email:</span> <div class="text-slate-300">${p.email || 'N/A'}</div></div>
        <div class="col-span-2"><span class="text-slate-500">Full Street Address:</span> <div class="text-slate-300">${p.address_line_1} ${p.address_line_2 || ''}, ${p.city}, ${p.state} ${p.zip_code}</div></div>
        <div><span class="text-slate-500">Insurance Carrier:</span> <div class="text-slate-300">${p.insurance_provider || 'None / Not Provided'}</div></div>
        <div><span class="text-slate-500">Insurance Member ID:</span> <div class="text-slate-300">${p.insurance_member_id || 'N/A'}</div></div>
        <div><span class="text-slate-500">Preferred Language:</span> <div class="text-slate-300">${p.preferred_language || 'English'}</div></div>
        <div><span class="text-slate-500">Emergency Contact:</span> <div class="text-slate-300">${p.emergency_contact_name || 'N/A'} (${p.emergency_contact_phone || 'N/A'})</div></div>
      </div>
      <div class="border-t border-slate-800 pt-3 flex justify-between items-center">
        <span class="text-[11px] text-slate-500">REST Envelope: <code>GET /patients/${patientId}</code></span>
        <button onclick="document.getElementById('patientDetailModal').classList.add('hidden')" class="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs">Close</button>
      </div>
    `;

    patientDetailModal.classList.remove("hidden");
  } catch (e) {
    console.error(e);
  }
};

// Soft Delete Patient
window.softDeletePatient = async function(patientId) {
  if (!confirm("Are you sure you want to soft-delete this patient record? (This sets deleted_at and excludes them from queries)")) {
    return;
  }
  try {
    const res = await fetch(`/patients/${patientId}`, { method: "DELETE" });
    const json = await res.json();
    if (json.data && json.data.deleted) {
      loadPatients();
    } else {
      alert("Error: " + (json.error ? json.error.message : "Could not delete"));
    }
  } catch (err) {
    console.error(err);
  }
};

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Event Listeners
micBtn.addEventListener("click", () => {
  if (isListening) {
    if (speechRecognition) speechRecognition.stop();
  } else {
    startListening();
  }
});

ttsToggleBtn.addEventListener("click", () => {
  ttsEnabled = !ttsEnabled;
  if (ttsEnabled) {
    ttsIcon.className = "fa-solid fa-volume-high text-sky-400";
  } else {
    window.speechSynthesis.cancel();
    ttsIcon.className = "fa-solid fa-volume-xmark text-slate-500";
  }
});

textInputForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = userInputText.value.trim();
  if (text) {
    userInputText.value = "";
    handleUserUtterance(text);
  }
});

resetCallBtn.addEventListener("click", () => {
  conversationHistory = [
    {
      role: "assistant",
      content: "Hi! Thank you for calling Oakwood Health Clinic. I'm Sarah, your patient intake coordinator. I can help register you as a new patient today. Could I have your first and last name to get started?"
    }
  ];
  dialogueContainer.innerHTML = "";
  appendChatBubble("assistant", conversationHistory[0].content);
});

refreshBtn.addEventListener("click", loadPatients);
searchLastName.addEventListener("input", debounce(loadPatients, 300));
searchPhone.addEventListener("input", debounce(loadPatients, 300));
searchDOB.addEventListener("input", debounce(loadPatients, 300));
closeDetailModal.addEventListener("click", () => patientDetailModal.classList.add("hidden"));

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Initialize on page load
window.addEventListener("DOMContentLoaded", () => {
  initSpeechRecognition();
  loadPatients();
});
