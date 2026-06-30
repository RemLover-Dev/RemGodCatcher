// ==========================================
// === INITIALIZATION ===
// ==========================================
let globalNetConfig = { "proxy_url": "", "use_proxy": false, "verify_tls": false };
window.nekoData = { image: [], gif: [] };

const socket = io();

socket.on("python_log", function(data) {
    logToConsole(data.worker, data.msg);
});

window.onload = async function() {
    // Load startup config (including proxy)
    try {
        let resp = await fetch("/api/config");
        let config = await resp.json();
        if (config) {
            globalNetConfig = config;
            document.getElementById("proxyEnabled").checked = config.use_proxy || false;
            document.getElementById("proxyUrl").value = config.proxy_url || "http://127.0.0.1:10808";
            document.getElementById("tlsVerify").checked = config.verify_tls || false;
            document.getElementById("apiTimeout").value = config.api_timeout || 10;
            document.getElementById("retryWait").value = config.retry_wait || 5;
            document.getElementById("antiBanPause").value = config.anti_ban_pause || 3;
        }
    } catch(e) { console.error("Config load error:", e); }

    // Load current folder
    try {
        let resp = await fetch("/api/folder");
        let data = await resp.json();
        if (data.folder) document.getElementById("folderDisplay").innerText = data.folder;
    } catch(e) { console.error("Folder load error:", e); }

    // Load neko categories
    await loadNekoCategories();
    document.getElementById("nekoCat").onclick = function() {
        if(this.value.includes("Network Error")) {
            this.value = "Retrying...";
            loadNekoCategories();
        }
    };

    // Load waifu tags
    try {
        let resp = await fetch("/api/tags/waifu", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(globalNetConfig)
        });
        let waifuTags = await resp.json();
        let wl = document.getElementById("waifuList");
        wl.innerHTML = "";
        waifuTags.forEach(t => wl.innerHTML += `<option value="${t}">`);
        if (waifuTags.length > 0) document.getElementById("waifuTag").value = waifuTags[0];
    } catch(e) { console.error("Waifu tags error:", e); }

    // Load API settings
    await loadApiSettings();

    logToConsole("main", "Welcome to Rem God Catcher! Web Interface Online.");
    logToConsole("main", "Configure API keys and download settings in the 'Options' tab.");
};

// ==========================================
// === CATEGORY LOADERS ===
// ==========================================
async function loadNekoCategories() {
    try {
        let resp = await fetch("/api/tags/neko", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(globalNetConfig)
        });
        let data = await resp.json();
        if (data.image.length === 0 && data.gif.length === 0) {
            document.getElementById("nekoCat").value = "Network Error (Click to Retry)";
        } else {
            window.nekoData = data;
            updateNekoDropdown();
        }
    } catch(e) {
        document.getElementById("nekoCat").value = "Network Error (Click to Retry)";
    }
}

function updateNekoDropdown() {
    let fmt = document.getElementById("nekoFormat").value;
    let nl = document.getElementById("nekoList");
    nl.innerHTML = "";
    
    let targetList = [];
    if (fmt === "Images (PNG)") targetList = window.nekoData.image;
    else if (fmt === "GIFs (Animations)") targetList = window.nekoData.gif;
    else targetList = window.nekoData.image.concat(window.nekoData.gif).sort();

    targetList.forEach(t => nl.innerHTML += `<option value="${t}">`);
    if (targetList.length > 0) document.getElementById("nekoCat").value = targetList[0];
}

// ==========================================
// === FOLDER BROWSER ===
// ==========================================
async function saveProxySettings() {
    globalNetConfig.use_proxy = document.getElementById("proxyEnabled").checked;
    globalNetConfig.proxy_url = document.getElementById("proxyUrl").value;
    globalNetConfig.verify_tls = document.getElementById("tlsVerify").checked;

    try {
        let resp = await fetch("/api/config", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(globalNetConfig)
        });
        let result = await resp.json();
        if (result.success) {
            logToConsole("main", `Proxy settings updated: ${globalNetConfig.use_proxy ? 'ENABLED' : 'DISABLED'} (${globalNetConfig.proxy_url})`);
        }
    } catch(e) {
        logToConsole("main", `Error saving proxy: ${e}`);
    }
}

async function browseFolder() {
    let input = document.createElement("input");
    input.type = "file";
    input.webkitdirectory = true;
    input.directory = true;
    
    // Use a hidden input trick for folder selection
    let folderInput = document.createElement("input");
    folderInput.type = "text";
    folderInput.placeholder = "Paste folder path here...";
    
    let folder = prompt("Enter the master download folder path:");
    if (!folder) return;
    
    try {
        let resp = await fetch("/api/folder", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ folder: folder })
        });
        let data = await resp.json();
        if (data.folder) {
            document.getElementById("folderDisplay").innerText = data.folder;
            logToConsole("main", `Master folder updated to: ${data.folder}`);
        }
    } catch(e) {
        logToConsole("main", `Error: ${e}`);
    }
}

// ==========================================
// === TAG SUGGESTION FETCHERS ===
// ==========================================
async function fetchZero(val) {
    if(val.length < 3) return;
    try {
        let resp = await fetch("/api/tags/zerochan", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ query: val, net_config: globalNetConfig })
        });
        let tags = await resp.json();
        let dl = document.getElementById("zeroList");
        dl.innerHTML = "";
        tags.forEach(t => dl.innerHTML += `<option value="${t}">`);
    } catch(e) { console.error(e); }
}

async function fetchSafe(val) {
    if(val.length < 2) return;
    let words = val.split(" ");
    let lastWord = words[words.length - 1];
    if(lastWord.length < 2) return;

    try {
        let resp = await fetch("/api/tags/safe", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ query: lastWord })
        });
        let tags = await resp.json();
        let dl = document.getElementById("safeList");
        dl.innerHTML = "";
        tags.forEach(t => {
            let suggestion = words.slice(0, -1).join(" ") + (words.length > 1 ? " " : "") + t;
            dl.innerHTML += `<option value="${suggestion}">`;
        });
    } catch(e) { console.error(e); }
}

async function fetchGelbooru(val) {
    if(val.length < 2) return;
    try {
        let resp = await fetch("/api/tags/gelbooru", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ query: val, net_config: globalNetConfig })
        });
        let tags = await resp.json();
        let dl = document.getElementById("gelbooruList");
        dl.innerHTML = "";
        tags.forEach(t => dl.innerHTML += `<option value="${t}">`);
    } catch(e) { console.error(e); }
}

async function fetchGelbooru(val) {
    if(val.length < 2) return;
    try {
        let resp = await fetch("/api/tags/gelbooru", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ query: val, net_config: globalNetConfig })
        });
        let tags = await resp.json();
        let dl = document.getElementById("gelbooruList");
        dl.innerHTML = "";
        tags.forEach(t => dl.innerHTML += `<option value="${t}">`);
    } catch(e) { console.error(e); }
}

async function fetchRule34(val) {
    if(val.length < 2) return;
    try {
        let resp = await fetch("/api/tags/rule34", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ query: val, net_config: globalNetConfig })
        });
        let tags = await resp.json();
        let dl = document.getElementById("rule34List");
        dl.innerHTML = "";
        tags.forEach(t => dl.innerHTML += `<option value="${t}">`);
    } catch(e) { console.error(e); }
}

// ==========================================
// === TAB SWITCHING ===
// ==========================================
function openTab(tabName, wallpaperFile, btn) {
    let contents = document.getElementsByClassName("tab-content");
    for (let i = 0; i < contents.length; i++) {
        contents[i].style.display = "none";
    }

    let buttons = document.getElementsByClassName("tab-btn");
    for (let i = 0; i < buttons.length; i++) buttons[i].classList.remove("active");

    let tab = document.getElementById(tabName);
    tab.style.display = "flex";
    btn.classList.add("active");
    document.body.style.backgroundImage = `url('wallpaper/${wallpaperFile}')`;
}

// ==========================================
// === CONSOLE LOG ===
// ==========================================
function logToConsole(tabID, msg) {
    let boxMap = {
        "main": "consoleLog_main",
        "neko": "consoleLog_neko",
        "nekos_life": "consoleLog_nekos_life",
        "zero": "consoleLog_zero",
        "waifu": "consoleLog_waifu",
        "safe": "consoleLog_safe",
        "gelbooru": "consoleLog_gelbooru",
        "rule34": "consoleLog_rule34"
    };
    
    let targetBoxId = boxMap[tabID.toLowerCase()] || "consoleLog_main";
    let consoleBox = document.getElementById(targetBoxId);
    
    if (consoleBox) {
        let time = new Date().toLocaleTimeString();
        let line = document.createElement("div");
        line.textContent = `[${time}] ${msg}`;
        consoleBox.appendChild(line);
        consoleBox.scrollTop = consoleBox.scrollHeight;
    }
}

// ==========================================
// === WORKER CONTROLS ===
// ==========================================
function startWorker(workerName) {
    try {
        if (workerName === 'zero') {
            let tag = document.getElementById('zeroTag').value;
            let limit = document.getElementById('zeroLimit').value;
            if(!tag) return logToConsole('zero', 'Error: Tag Name cannot be empty!');
            socket.emit("start_worker", { worker: 'zero', tag: tag, limit: limit, net_config: globalNetConfig });
        } 
        else if (workerName === 'waifu') {
            let tag = document.getElementById('waifuTag').value;
            let limit = document.getElementById('waifuLimit').value;
            let nsfw = document.getElementById('waifuNsfw').checked;
            if(!tag) return logToConsole('waifu', 'Error: Tag Name cannot be empty!');
            socket.emit("start_worker", { worker: 'waifu', tag: tag, limit: limit, nsfw: nsfw, net_config: globalNetConfig });
        }
        else if (workerName === 'neko') {
            let tag = document.getElementById('nekoCat').value;
            let limit = document.getElementById('nekoAmount').value;
            if(!tag) return logToConsole('neko', 'Error: Category cannot be empty!');
            socket.emit("start_worker", { worker: 'neko', category: tag, limit: limit, net_config: globalNetConfig });
        }
        else if (workerName === 'nekos_life') {
            let tag = document.getElementById('nekosLifeCat').value;
            let limit = document.getElementById('nekosLifeAmount').value;
            if(!tag) return logToConsole('nekos_life', 'Error: Category cannot be empty!');
            let net = Object.assign({}, globalNetConfig);
            net.nekos_life_exclude_gif = document.getElementById('nekosLifeExGif').checked;
            net.nekos_life_exclude_img = document.getElementById('nekosLifeExImg').checked;
            socket.emit("start_worker", { worker: 'nekos_life', category: tag, limit: limit, net_config: net });
        }
        else if (workerName === 'safe') {
            let tag = document.getElementById('safeTag').value;
            let limit = document.getElementById('safeLimit').value;
            if(!tag) return logToConsole('safe', 'Error: Search Tags cannot be empty!');
            socket.emit("start_worker", { worker: 'safe', tag: tag, limit: limit, net_config: globalNetConfig });
        }
        else if (workerName === 'gelbooru') {
            let tag = document.getElementById('gelbooruTag').value;
            let limit = document.getElementById('gelbooruLimit').value;
            if(!tag) return logToConsole('gelbooru', 'Error: Search Tags cannot be empty!');
            let exclusions = [];
            if (document.getElementById('gelbooruExVideo').checked) exclusions.push('-video');
            if (document.getElementById('gelbooruExGif').checked) exclusions.push('-gif');
            socket.emit("start_worker", { worker: 'gelbooru', tag: tag, limit: limit, exclusions: exclusions, net_config: globalNetConfig });
        }
        else if (workerName === 'rule34') {
            let tag = document.getElementById('rule34Tag').value;
            let limit = document.getElementById('rule34Limit').value;
            let method = document.getElementById('rule34Method').value;
            let sortType = document.getElementById('rule34SortType').value;
            let sortOrder = document.getElementById('rule34SortOrder').value;

            if(!tag) return logToConsole('rule34', 'Error: Search Tags cannot be empty!');
            
            let exclusions = [];
            if (document.getElementById('exVideo').checked) exclusions.push('-video');
            if (document.getElementById('exGif').checked) exclusions.push('-gif');
            if (document.getElementById('exComic').checked) exclusions.push('-comic');
            if (document.getElementById('ex3D').checked) exclusions.push('-3d');

            socket.emit("start_worker", {
                worker: 'rule34',
                tag: tag,
                limit: limit,
                method: method,
                sort_type: sortType,
                sort_order: sortOrder,
                exclusions: exclusions,
                net_config: globalNetConfig
            });
        }
    } catch (e) {
        logToConsole('main', `UI Error: ${e}`);
    }
}

function stopWorker(workerName) { 
    socket.emit("stop_worker", { worker: workerName });
}

// ==========================================
// === API SETTINGS ===
// ==========================================
async function loadApiSettings() {
    try {
        let resp = await fetch("/api/api-settings");
        let settings = await resp.json();
        document.getElementById("apiKeyInput").value = settings.rule34_api_key || "";
        document.getElementById("apiUserIdInput").value = settings.rule34_user_id || "";
        document.getElementById("gelbooruApiKeyInput").value = settings.gelbooru_api_key || "";
        document.getElementById("gelbooruUserIdInput").value = settings.gelbooru_user_id || "";
    } catch(e) {
        console.error("Failed to load API settings:", e);
    }
}

async function saveApiSettings() {
    let rule34Key = document.getElementById("apiKeyInput").value.trim();
    let rule34Uid = document.getElementById("apiUserIdInput").value.trim();
    let gelKey = document.getElementById("gelbooruApiKeyInput").value.trim();
    let gelUid = document.getElementById("gelbooruUserIdInput").value.trim();
    let statusEl = document.getElementById("apiSaveStatus");

    try {
        let resp = await fetch("/api/api-settings", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                rule34_api_key: rule34Key,
                rule34_user_id: rule34Uid,
                gelbooru_api_key: gelKey,
                gelbooru_user_id: gelUid,
            })
        });
        let result = await resp.json();
        if (result.success) {
            statusEl.style.color = "#00d2d3";
            statusEl.textContent = result.message;
        } else {
            statusEl.style.color = "#ff9ff3";
            statusEl.textContent = "Error saving settings.";
        }
    } catch(e) {
        statusEl.style.color = "#ff9ff3";
        statusEl.textContent = "Error: " + e;
    }
}

function toggleApiKeyVisibility() {
    let input = document.getElementById("apiKeyInput");
    let btn = event.target;
    if (input.type === "password") {
        input.type = "text";
        btn.textContent = "Hide";
    } else {
        input.type = "password";
        btn.textContent = "Show";
    }
}

function saveGelbooruApiSettings() {
    let gelKey = document.getElementById("gelbooruApiKeyInput").value.trim();
    let gelUid = document.getElementById("gelbooruUserIdInput").value.trim();
    let statusEl = document.getElementById("gelbooruApiSaveStatus");

    fetch("/api/api-settings", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            rule34_api_key: document.getElementById("apiKeyInput").value.trim(),
            rule34_user_id: document.getElementById("apiUserIdInput").value.trim(),
            gelbooru_api_key: gelKey,
            gelbooru_user_id: gelUid,
        })
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            statusEl.style.color = "#00d2d3";
            statusEl.textContent = "Saved!";
        } else {
            statusEl.style.color = "#ff9ff3";
            statusEl.textContent = "Error saving.";
        }
        setTimeout(() => { statusEl.textContent = ""; }, 2500);
    })
    .catch(() => {
        statusEl.style.color = "#ff9ff3";
        statusEl.textContent = "Error saving.";
    });
}

function toggleGelbooruApiKeyVisibility() {
    let input = document.getElementById("gelbooruApiKeyInput");
    let btn = event.target;
    if (input.type === "password") {
        input.type = "text";
        btn.textContent = "Hide";
    } else {
        input.type = "password";
        btn.textContent = "Show";
    }
}

// ==========================================
// === DOWNLOAD SETTINGS ===
// ==========================================
async function saveDownloadSettings() {
    globalNetConfig.api_timeout = document.getElementById("apiTimeout").value;
    globalNetConfig.retry_wait = document.getElementById("retryWait").value;
    globalNetConfig.anti_ban_pause = document.getElementById("antiBanPause").value;

    try {
        let resp = await fetch("/api/config", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(globalNetConfig)
        });
        let result = await resp.json();
        if (result.success) {
            let status = document.getElementById("dlSettingsStatus");
            status.style.color = "#00d2d3";
            status.textContent = "Saved!";
            setTimeout(() => status.textContent = "", 2000);
        }
    } catch(e) {
        let status = document.getElementById("dlSettingsStatus");
        status.style.color = "#ff9ff3";
        status.textContent = "Error: " + e;
    }
}
