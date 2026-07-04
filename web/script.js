let globalNetConfig = { "proxy_url": "", "use_proxy": false, "verify_tls": false };
let uiConfig = {};
let currentActiveTheme = 'dark';

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if (uiConfig.theme_mode === 'system') {
        applyRenderTheme(e.matches ? 'dark' : 'light');
    }
});

async function loadUIConfig() {
    try {
        let resp = await fetch("/api/ui_config");
        uiConfig = await resp.json();

        let radio = document.querySelector(`input[name="themeMode"][value="${uiConfig.theme_mode}"]`);
        if (radio) radio.checked = true;

        let resolvedTheme = uiConfig.theme_mode;
        if (resolvedTheme === 'system') {
            resolvedTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        applyRenderTheme(resolvedTheme);
        renderWallpaperGrid();
    } catch(e) { console.error("Error loading UI config", e); }
}

function applyRenderTheme(themeStr) {
    currentActiveTheme = themeStr;
    document.documentElement.setAttribute('data-theme', themeStr);

    let colors = uiConfig.colors[themeStr];
    if (!colors) return;
    updateLiveColor('title', colors.title, false);
    updateLiveColor('text', colors.text, false);
    updateLiveColor('accent', colors.accent, false);
    updateLiveColor('tab_text', colors.tab_text, false);
    updateLiveColor('btn_start_bg', colors.btn_start_bg, false);
    updateLiveColor('btn_start_text', colors.btn_start_text, false);
    updateLiveColor('btn_stop_bg', colors.btn_stop_bg, false);
    updateLiveColor('btn_stop_text', colors.btn_stop_text, false);

    let activeTabBtn = document.querySelector(".tab-btn.active");
    if (activeTabBtn) {
        let tabMatch = activeTabBtn.getAttribute("onclick").match(/'([^']+)'/);
        if (tabMatch) updateBackground(tabMatch[1]);
    }
}

function changeThemeMode(mode) {
    uiConfig.theme_mode = mode;
    let resolvedTheme = mode === 'system' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : mode;
    applyRenderTheme(resolvedTheme);
}

function updateLiveColor(key, hexVal, saveToConfig = true) {
    let cssKey = key;
    if (key === 'title') cssKey = 'title-color';
    else if (key === 'text') cssKey = 'text-color';
    else if (key === 'accent') cssKey = 'accent-color';
    else cssKey = key.replace(/_/g, '-');

    document.documentElement.style.setProperty(`--${cssKey}`, hexVal);

    let colorInput = document.getElementById(`color_${key}`);
    if (colorInput) colorInput.value = hexVal;

    if (saveToConfig) uiConfig.colors[currentActiveTheme][key] = hexVal;
}

function renderWallpaperGrid() {
    let ui = document.getElementById("wpGridUI");
    if (!ui) return;
    ui.innerHTML = "";
    Object.keys(uiConfig.wallpapers).forEach(tab => {
        let boxIdDark = `file_${tab}_dark`;
        let boxIdLight = `file_${tab}_light`;

        ui.innerHTML += `
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <span style="color: var(--text-color); font-size: 13px; font-weight: bold;">${tab}</span>
                <div style="display: flex; gap: 10px;">
                    <div class="wp-box dark-mode" onclick="document.getElementById('${boxIdDark}').click()">
                        Dark Mode
                        <input type="file" id="${boxIdDark}" accept="image/*" style="display:none" onchange="uploadWpBox('${tab}', 'dark', this)">
                    </div>
                    <div class="wp-box light-mode" onclick="document.getElementById('${boxIdLight}').click()">
                        Light Mode
                        <input type="file" id="${boxIdLight}" accept="image/*" style="display:none" onchange="uploadWpBox('${tab}', 'light', this)">
                    </div>
                </div>
            </div>
        `;
    });
}

async function uploadWpBox(tabName, mode, fileInput) {
    if (!fileInput.files || fileInput.files.length === 0) return;
    let formData = new FormData();
    formData.append("file", fileInput.files[0]);
    try {
        let resp = await fetch("/api/upload_wallpaper", { method: "POST", body: formData });
        let result = await resp.json();
        if (result.success) {
            uiConfig.wallpapers[tabName][mode] = result.filename;
            fileInput.parentElement.style.border = "2px solid var(--title-color)";
            setTimeout(() => fileInput.parentElement.style.border = "", 1000);

            let activeTabBtn = document.querySelector(".tab-btn.active");
            if (activeTabBtn && activeTabBtn.getAttribute("onclick").includes(`'${tabName}'`) && currentActiveTheme === mode) {
                updateBackground(tabName);
            }
        }
    } catch (e) { alert("Upload failed: " + e); }
    fileInput.value = "";
}

function updateBackground(tabName) {
    let wp = uiConfig.wallpapers && uiConfig.wallpapers[tabName];
    if (!wp) return;
    let filename = wp[currentActiveTheme] || wp['dark'];
    if (filename) {
        document.body.style.backgroundImage = `url('wallpaper/${filename}')`;
    }
}

// =====================================
// === COLOR PALETTE SAVE & RESET ===
// =====================================
async function saveColors() {
    await fetch("/api/ui_config", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(uiConfig) });
    let status = document.getElementById("colorSaveStatus");
    status.textContent = "Colors Saved!";
    setTimeout(()=> status.textContent = "", 2000);
}

async function resetColors() {
    if (!confirm("Are you sure you want to reset all COLORS to default? Wallpapers will not be changed.")) return;

    uiConfig.colors = {
        "dark": {
            "title": "#00d2d3", "text": "#ffffff", "accent": "#ff9ff3", "tab_text": "#ffffff",
            "btn_start_bg": "#00d2d3", "btn_start_text": "#0a0a0a",
            "btn_stop_bg": "#ff9ff3", "btn_stop_text": "#1a0a1a"
        },
        "light": {
            "title": "#004d4d",
            "text": "#1a1a2e",
            "accent": "#a0008a",
            "tab_text": "#1a1a2e",
            "btn_start_bg": "#004d4d", "btn_start_text": "#ffffff",
            "btn_stop_bg": "#a0008a", "btn_stop_text": "#ffffff"
        }
    };

    applyRenderTheme(currentActiveTheme);
    await saveColors();

    let status = document.getElementById("colorSaveStatus");
    status.textContent = "Colors Reset!";
    status.style.color = "var(--title-color)";
    setTimeout(() => { status.textContent = ""; }, 2000);
}


// =====================================
// === WALLPAPERS SAVE & RESET ===
// =====================================
async function saveWallpapersUI() {
    await fetch("/api/ui_config", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(uiConfig) });
    let status = document.getElementById("wpSaveStatusUI");
    status.textContent = "Wallpapers Saved!";
    setTimeout(()=> status.textContent = "", 2000);
}

async function resetWallpapersUI() {
    if (!confirm("Are you sure you want to reset all WALLPAPERS to default? Colors will not be changed.")) return;

    uiConfig.wallpapers = {
        "Main": {"dark": "Rem_main_d.png", "light": "Rem_main_l.png"},
        "Neko": {"dark": "Rem_neko_d.png", "light": "Rem_neko_l.png"},
        "NekosLife": {"dark": "Rem_nekolife_d.png", "light": "Rem_nekolife_l.png"},
        "Zero": {"dark": "Rem_zero_d.png", "light": "Rem_zero_l.png"},
        "Waifu": {"dark": "Rem_waifu_d.png", "light": "Rem_waifu_l.png"},
        "Safe": {"dark": "Rem_safe_d.png", "light": "Rem_safe_l.png"},
        "Gelbooru": {"dark": "Rem_gelbooru_d.png", "light": "Rem_gelbooru_l.png"},
        "Rule34": {"dark": "Rem_rule34_d.png", "light": "Rem_rule34_l.png"},
        "Yande": {"dark": "Rem_yande_d.png", "light": "Rem_yande_l.png"},
        "History": {"dark": "Rem_history_d.png", "light": "Rem_history_l.png"},
        "Options": {"dark": "Rem_option_d.png", "light": "Rem_option_l.png"},
        "Customize": {"dark": "Rem_custom_d.png", "light": "Rem_custom_l.png"}
    };

    renderWallpaperGrid();
    await saveWallpapersUI();
    updateBackground("Customize");

    let status = document.getElementById("wpSaveStatusUI");
    status.textContent = "Wallpapers Reset!";
    status.style.color = "var(--accent-color)";
    setTimeout(() => { status.textContent = ""; status.style.color = "var(--title-color)"; }, 2000);
}

const socket = io();

socket.on("python_log", function (data) {
    logToConsole(data.worker, data.msg);
});

socket.on("update_history", function () {
    loadTagsData();
});

window.onload = async function () {
    try {
        let resp = await fetch("/api/config");
        let config = await resp.json();
        if (config) {
            globalNetConfig = config;
            document.getElementById("proxyEnabled").checked = config.use_proxy || false;
            document.getElementById("proxyUrl").value = config.proxy_url || "http://127.0.0.1:10808";
            document.getElementById("apiTimeout").value = config.api_timeout || 10;
            document.getElementById("retryWait").value = config.retry_wait || 5;
            document.getElementById("antiBanPause").value = config.anti_ban_pause || 3;
            document.getElementById("downloadRetries").value = config.download_retries || 3;
        }
    } catch (e) { console.error("Config error:", e); }

    try {
        let resp = await fetch("/api/folder");
        let data = await resp.json();
        if (data.folder) document.getElementById("folderDisplay").innerText = data.folder;
    } catch (e) {}

    updateNekoDropdown();
    updateNekosLifeType();
    await loadUIConfig();

    try {
        let resp = await fetch("/api/tags/waifu", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(globalNetConfig)
        });
        let waifuTags = await resp.json();
        let wl = document.getElementById("waifuList");
        let wHtml = "";
        waifuTags.forEach(t => wHtml += `<option value="${t}">`);
        wl.innerHTML = wHtml;
        if (waifuTags.length > 0) document.getElementById("waifuTag").value = waifuTags[0];
    } catch (e) {}

    await loadTagsData();
    await loadApiSettings();
};

const nekoImages = ["husbando", "kitsune", "neko", "waifu"];
const nekoGifs = ["angry", "baka", "bite", "bleh", "blowkiss", "blush", "bonk", "bored", "carry", "clap", "confused", "cry", "cuddle", "dance", "facepalm", "feed", "handhold", "handshake", "happy", "highfive", "hug", "kabedon", "kick", "kiss", "lappillow", "laugh", "lurk", "nod", "nom", "nope", "nya", "pat", "peck", "poke", "pout", "punch", "run", "salute", "shake", "shoot", "shocked", "shrug", "sip", "slap", "sleep", "smile", "smug", "spin", "stare", "tableflip", "teehee", "think", "thumbsup", "tickle", "wag", "wave", "wink", "yawn", "yeet"];

function updateNekoDropdown() {
    let fmt = document.getElementById("nekoFormat").value;
    let sel = document.getElementById("nekoCat");
    sel.innerHTML = "";
    
    let targetList = fmt === "Images" ? nekoImages : nekoGifs;
    targetList.forEach(t => {
        let opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;
        sel.appendChild(opt);
    });
}

function toggleGifExclusion(formatId, checkboxId) {
    let format = document.getElementById(formatId).value;
    let checkbox = document.getElementById(checkboxId);
    let label = checkbox.nextElementSibling;
    if (format === 'gifs') {
        checkbox.style.display = 'none';
        label.style.display = 'none';
    } else {
        checkbox.style.display = '';
        label.style.display = '';
    }
}

function updateNekosLifeType() {
    const gifOnly = ["ngif", "hug", "pat", "cuddle", "tickle", "feed", "slap", "kiss", "smug"];
    const staticOnly = ["gecg", "meow", "neko", "lewd", "gasm", "8ball", "avatar", "woof", "fox_girl", "waifu"];
    const mixed = ["goose", "wallpaper", "lizard", "span"];
    
    let cat = document.getElementById("nekosLifeCat").value;
    let typeEl = document.getElementById("nekosLifeType");
    
    if (gifOnly.includes(cat)) {
        typeEl.textContent = "[GIF]";
        typeEl.style.color = "var(--accent-color)";
    } else if (staticOnly.includes(cat)) {
        typeEl.textContent = "[STATIC]";
        typeEl.style.color = "#00d2d3";
    } else if (mixed.includes(cat)) {
        typeEl.textContent = "[MIXED]";
        typeEl.style.color = "#ffd93d";
    } else {
        typeEl.textContent = "";
    }
}

async function saveProxySettings() {
    globalNetConfig.use_proxy = document.getElementById("proxyEnabled").checked;
    globalNetConfig.proxy_url = document.getElementById("proxyUrl").value;
    try {
        await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(globalNetConfig) });
        logToConsole("main", "Proxy updated.");
    } catch (e) {}
}

async function browseFolder() {
    let folder = prompt("Enter the master download folder path:");
    if (!folder) return;
    try {
        let resp = await fetch("/api/folder", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ folder: folder }) });
        let data = await resp.json();
        if (data.folder) {
            document.getElementById("folderDisplay").innerText = data.folder;
            logToConsole("main", `Master folder updated to: ${data.folder}`);
        }
    } catch(e) {}
}

function openTab(tabName, btn) {
    let contents = document.getElementsByClassName("tab-content");
    for (let i = 0; i < contents.length; i++) contents[i].style.display = "none";
    let buttons = document.getElementsByClassName("tab-btn");
    for (let i = 0; i < buttons.length; i++) buttons[i].classList.remove("active");

    document.getElementById(tabName).style.display = "flex";
    btn.classList.add("active");
    updateBackground(tabName);
}

function logToConsole(tabID, msg) {
    let boxMap = {
        "main": "consoleLog_main", "neko": "consoleLog_neko", "nekos_life": "consoleLog_nekos_life",
        "zero": "consoleLog_zero", "waifu": "consoleLog_waifu", "safe": "consoleLog_safe",
        "rule34": "consoleLog_rule34", "gelbooru": "consoleLog_gelbooru", "yande": "consoleLog_yande"
    };
    let cb = document.getElementById(boxMap[tabID.toLowerCase()] || "consoleLog_main");
    if (cb) {
        let line = document.createElement("div");
        line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
        cb.appendChild(line);
        cb.scrollTop = cb.scrollHeight;
    }
}

function startWorker(workerName) {
    let payload = { worker: workerName, net_config: { ...globalNetConfig } };
    payload.net_config.api_timeout = document.getElementById("apiTimeout").value;
    payload.net_config.retry_wait = document.getElementById("retryWait").value;
    payload.net_config.anti_ban_pause = document.getElementById("antiBanPause").value;
    
    if (workerName === 'zero') {
        payload.tag = document.getElementById('zeroTag').value;
        payload.limit = document.getElementById('zeroLimit').value;
    } else if (workerName === 'waifu') {
        payload.tag = document.getElementById('waifuTag').value;
        payload.limit = document.getElementById('waifuLimit').value;
        payload.nsfw = document.getElementById('waifuNsfw').checked;
    } else if (workerName === 'neko') {
        payload.category = document.getElementById('nekoCat').value;
        payload.limit = document.getElementById('nekoAmount').value;
    } else if (workerName === 'nekos_life') {
        payload.category = document.getElementById('nekosLifeCat').value;
        payload.limit = document.getElementById('nekosLifeAmount').value;
    } else if (workerName === 'safe') {
        payload.tag = document.getElementById('safeTag').value;
        payload.limit = document.getElementById('safeLimit').value;
        
        let format = document.getElementById('safeFormat').value;
        let ex = [];
        if (format === 'images') ex.push('-video');
        else if (format === 'videos') {
            ex.push('-image');
            payload.tag += " video";
        }
        payload.exclusions = ex;

    } else if (workerName === 'gelbooru') {
        payload.tag = document.getElementById('gelbooruTag').value;
        payload.limit = document.getElementById('gelbooruLimit').value;
        
        let format = document.getElementById('gelFormat').value;
        let ex = [];
        if (format === 'images') ex.push('-video');
        else if (format === 'videos') {
            ex.push('-image');
            payload.tag += " video";
        }
        payload.exclusions = ex;
        if (document.getElementById('gelNoAI').checked) payload.tag += " -ai_generated";

    } else if (workerName === 'yande') {
        payload.tag = document.getElementById('yandeTag').value;
        payload.limit = document.getElementById('yandeLimit').value;
        payload.rating = document.getElementById('yandeRating').value;

    } else if (workerName === 'rule34') {
        payload.tag = document.getElementById('rule34Tag').value;
        payload.limit = document.getElementById('rule34Limit').value;
        payload.method = document.getElementById('rule34Method').value;
        payload.sort_type = document.getElementById('rule34SortType').value;
        payload.sort_order = document.getElementById('rule34SortOrder').value;
        
        let format = document.getElementById('rule34Format').value;
        let ex = [];
        if (format === 'images') ex.push('-video');
        else if (format === 'gifs') {
            ex.push('-video');
            ex.push('-image');
        }
        else if (format === 'videos') {
            ex.push('-image');
            payload.tag += " video";
        }
        
        if (document.getElementById('exGif').checked) ex.push('-gif');
        if (document.getElementById('exComic').checked) ex.push('-comic');
        if (document.getElementById('ex3D').checked) ex.push('-3d');
        payload.exclusions = ex;
    }
    
    socket.emit("start_worker", payload);
    setTimeout(loadTagsData, 1000); // آپدیت خودکار لیست هیستوری بعد از یک ثانیه
}

function stopWorker(workerName) {
    socket.emit("stop_worker", { worker: workerName });
}

async function loadApiSettings() {
    let resp = await fetch("/api/api-settings");
    let settings = await resp.json();
    document.getElementById("r34Key").value = settings.rule34_api_key || "";
    document.getElementById("r34Uid").value = settings.rule34_user_id || "";
    document.getElementById("gelKey").value = settings.gelbooru_api_key || "";
    document.getElementById("gelUid").value = settings.gelbooru_user_id || "";
}

async function saveApiSettings() {
    let payload = {
        rule34_api_key: document.getElementById("r34Key").value.trim(),
        rule34_user_id: document.getElementById("r34Uid").value.trim(),
        gelbooru_api_key: document.getElementById("gelKey").value.trim(),
        gelbooru_user_id: document.getElementById("gelUid").value.trim()
    };
    let resp = await fetch("/api/api-settings", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
    });
    let result = await resp.json();
    let statusEl = document.getElementById("apiSaveStatus");
    statusEl.textContent = result.success ? "Saved!" : "Error!";
    setTimeout(()=> statusEl.textContent = "", 2000);
}

async function saveDownloadSettings() {
    globalNetConfig.api_timeout = document.getElementById("apiTimeout").value;
    globalNetConfig.retry_wait = document.getElementById("retryWait").value;
    globalNetConfig.anti_ban_pause = document.getElementById("antiBanPause").value;
    globalNetConfig.download_retries = document.getElementById("downloadRetries").value;
    await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(globalNetConfig) });
    document.getElementById("dlSettingsStatus").textContent = "Saved!";
    setTimeout(()=> document.getElementById("dlSettingsStatus").textContent = "", 2000);
}

// ==========================================
// === AUTO-SUGGEST FIX ===
// ==========================================
async function fetchZero(val) {
    if (val.length < 3) return;
    try {
        let resp = await fetch("/api/tags/zerochan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: val, net_config: globalNetConfig }) });
        let tags = await resp.json();
        let dl = document.getElementById("zeroList");
        let dHtml = "";
        tags.forEach(t => dHtml += `<option value="${t}">`);
        dl.innerHTML = dHtml;
    } catch(e) {}
}

async function fetchSafe(val) {
    if (val.length < 2) return;
    let words = val.split(" "); let lastWord = words[words.length - 1]; if(lastWord.length < 2) return;
    try {
        let resp = await fetch("/api/tags/safe", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: lastWord }) });
        let tags = await resp.json();
        let dl = document.getElementById("safeList");
        let dHtml = "";
        tags.forEach(t => dHtml += `<option value="${words.slice(0,-1).join(" ") + (words.length>1?" ":"") + t}">`);
        dl.innerHTML = dHtml;
    } catch(e) {}
}

async function fetchRule34(val) {
    if (val.length < 2) return;
    try {
        let resp = await fetch("/api/tags/rule34", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: val, net_config: globalNetConfig }) });
        let tags = await resp.json();
        let dl = document.getElementById("rule34List");
        let dHtml = "";
        tags.forEach(t => dHtml += `<option value="${t}">`);
        dl.innerHTML = dHtml;
    } catch(e) {}
}

async function fetchYande(val) {
    if (val.length < 2) return;
    let words = val.split(" "); let lastWord = words[words.length - 1]; if(lastWord.length < 2) return;
    try {
        let resp = await fetch("/api/tags/yande", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: lastWord }) });
        let tags = await resp.json();
        let dl = document.getElementById("yandeList");
        let dHtml = "";
        tags.forEach(t => dHtml += `<option value="${words.slice(0,-1).join(" ") + (words.length>1?" ":"") + t}">`);
        dl.innerHTML = dHtml;
    } catch(e) {}
}

async function fetchGelbooru(val) {
    if (val.length < 2) return;
    try {
        let resp = await fetch("/api/tags/rule34", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: val, net_config: globalNetConfig }) });
        let tags = await resp.json();
        let dl = document.getElementById("gelbooruList");
        let dHtml = "";
        tags.forEach(t => dHtml += `<option value="${t}">`);
        dl.innerHTML = dHtml;
    } catch(e) {}
}

// ==========================================
// === HISTORY & FAVORITES SYSTEM ===
// ==========================================
let historyTags = [];
let favoriteTags = [];
let imageHistory = [];

async function loadTagsData() {
    try {
        let resHist = await fetch("/api/history");
        historyTags = await resHist.json();
        
        let resFav = await fetch("/api/favorites");
        favoriteTags = await resFav.json();

        let resImgHist = await fetch("/api/image_history");
        imageHistory = await resImgHist.json();
        
        renderHistory();
        renderFavorites();
        renderImageHistory();
    } catch(e) { console.error("Error loading tags", e); }
}

function isFavorite(site, tag) {
    return favoriteTags.some(x => x.site === site && x.tag === tag);
}

function renderHistory() {
    let ui = document.getElementById("historyListUI");
    if(!ui) return;
    let currentScroll = ui.parentElement.scrollTop;
    let htmlStr = "";
    if (historyTags.length === 0) {
        htmlStr = "<p style='color: var(--text-color); opacity: 0.7; font-size: 13px;'>No search history yet.</p>";
    } else {
        historyTags.forEach(item => {
            let isFav = isFavorite(item.site, item.tag);
            let heartIcon = isFav ? "💖" : "🤍";

            htmlStr += `
                <div style="display: flex; justify-content: space-between; align-items: center; background: var(--input-bg); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border-color);">
                    <div>
                        <span style="color: var(--accent-color); font-size: 11px; text-transform: uppercase; border: 1px solid var(--accent-color); padding: 2px 5px; border-radius: 4px; margin-right: 10px;">${item.site}</span>
                        <span style="font-size: 14px; color: var(--text-color);">${item.tag}</span>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="action-btn" style="padding: 4px 8px; font-size: 12px; background: transparent; border: 1px solid var(--border-color); color: var(--text-color);" onclick="jumpToSite('${item.site}', '${item.tag}')">➡️</button>
                        <button class="action-btn" style="padding: 4px 8px; font-size: 12px; background: transparent; border: 1px solid var(--border-color);" onclick="toggleFavorite('${item.site}', '${item.tag}')">${heartIcon}</button>
                        <button class="action-btn stop-btn" style="padding: 4px 8px; font-size: 12px;" onclick="removeFromHistory('${item.site}', '${item.tag}')">❌</button>
                    </div>
                </div>
            `;
        });
    }
    ui.innerHTML = htmlStr;
    ui.parentElement.scrollTop = currentScroll;
}

function renderFavorites() {
    let ui = document.getElementById("favoritesListUI");
    if(!ui) return;
    ui.innerHTML = "";
    if (favoriteTags.length === 0) {
        ui.innerHTML = "<p style='color: var(--text-color); opacity: 0.7; font-size: 12px;'>Click 🤍 in the History tab to add favorites.</p>";
        return;
    }

    favoriteTags.forEach(item => {
        ui.innerHTML += `
            <div style="background: var(--tab-active-bg); border: 1px solid var(--title-color); padding: 5px 10px; border-radius: 20px; font-size: 13px; display: flex; align-items: center; gap: 5px; transition: 0.2s;">
                <span onclick="jumpToSite('${item.site}', '${item.tag}')" style="cursor: pointer; display: flex; align-items: center; gap: 5px; flex: 1; color: var(--text-color);">
                    <span>❄️</span>
                    <span style="color: var(--title-color); font-weight: bold; font-size: 10px; text-transform: uppercase;">[${item.site}]</span>
                    <span>${item.tag}</span>
                </span>
                <button onclick="event.stopPropagation(); toggleFavorite('${item.site}', '${item.tag}')" style="background: transparent; border: none; color: #ff6b6b; cursor: pointer; font-size: 12px; padding: 0 0 0 5px; line-height: 1;">✕</button>
            </div>
        `;
    });
}

async function toggleFavorite(site, tag) {
    let action = isFavorite(site, tag) ? "remove" : "add";
    let resp = await fetch("/api/favorites", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ site: site, tag: tag, action: action })
    });
    let data = await resp.json();
    favoriteTags = data.favorites;
    renderHistory();
    renderFavorites();
    renderImageHistory();
}

async function removeFromHistory(site, tag) {
    await fetch("/api/history/remove", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ site: site, tag: tag })
    });
    await loadTagsData();
}

async function clearHistory() {
    if(confirm("Are you sure you want to delete all search history?")) {
        await fetch("/api/history/clear", { method: "POST" });
        await loadTagsData();
    }
}

// تابع پرش از صفحه اصلی به تب سایت و پر کردن خودکار
function jumpToSite(site, tag) {
    let siteMap = {
        "zero":      { tab: "Zero",     input: "zeroTag" },
        "waifu":     { tab: "Waifu",    input: "waifuTag" },
        "neko":      { tab: "Neko",     input: null },
        "nekos_life":{ tab: "NekosLife", input: null },
        "safe":      { tab: "Safe",     input: "safeTag" },
        "gelbooru":  { tab: "Gelbooru", input: "gelbooruTag" },
        "yande":     { tab: "Yande",    input: "yandeTag" },
        "rule34":    { tab: "Rule34",    input: "rule34Tag" }
    };
    let mapping = siteMap[site] || { tab: "Safe", input: "safeTag" };

    let btn = Array.from(document.querySelectorAll('.tab-btn')).find(el => el.textContent.toLowerCase().includes(mapping.tab.toLowerCase()));
    if(btn) openTab(mapping.tab, btn);

    if(mapping.input) {
        let inputEl = document.getElementById(mapping.input);
        if(inputEl) inputEl.value = tag;
    }
}

function renderImageHistory() {
    let ui = document.getElementById("imageHistoryUI");
    if(!ui) return;
    
    let currentScroll = ui.parentElement.scrollTop;
    let htmlStr = "";
    
    if (imageHistory.length === 0) {
        htmlStr = "<p style='color: var(--text-color); opacity: 0.7; font-size: 13px;'>No images downloaded yet.</p>";
    } else {
        imageHistory.forEach(img => {
            let tagsHtml = img.tags.map(t => {
                let isFav = isFavorite(img.site, t);
                let bgColor = isFav ? "var(--tab-active-bg)" : "var(--input-bg)";
                let borderColor = isFav ? "var(--accent-color)" : "transparent";
                let textColor = isFav ? "var(--accent-color)" : "var(--text-color)";
                return `<span onclick="addFavoriteFromImage('${img.site}', '${t}')" style="background: ${bgColor}; border: 1px solid ${borderColor}; color: ${textColor}; padding: 4px 10px; border-radius: 6px; font-size: 11px; cursor: pointer; transition: 0.2s; white-space: nowrap; display: inline-block;">${t}</span>`;
            }).join('');

            let artistHtml = img.artists && img.artists.length > 0 
                ? `<div style="margin-top: 10px; border-top: 1px solid var(--border-color); padding-top: 8px;">
                       <span style="color: var(--title-color); font-size: 12px; font-weight: bold;">Artists:</span> 
                       <span style="font-size: 12px; color: var(--text-color); opacity: 0.8;">${img.artists.join(', ')}</span>
                   </div>` 
                : "";

            htmlStr += `
                <div style="background: var(--input-bg); padding: 15px; border-radius: 8px; border: 1px solid var(--border-color); position: relative;">
                    <button onclick="removeImageHistory('${img.filename}')" class="action-btn stop-btn" style="position: absolute; top: 10px; right: 10px; padding: 2px 6px; font-size: 10px;">&#10060;</button>
                    <h3 style="color: var(--text-color); font-size: 16px; margin-bottom: 12px; padding-right: 30px; word-break: break-all;">${img.filename} <span style="font-size: 10px; color: var(--accent-color); border: 1px solid var(--accent-color); padding: 2px 4px; border-radius: 4px; vertical-align: middle; margin-left: 10px;">${img.site}</span></h3>
                    
                    <div style="display: flex; flex-wrap: wrap; gap: 6px; max-height: 150px; overflow-y: auto; padding-right: 5px;">
                        ${tagsHtml}
                    </div>
                    ${artistHtml}
                </div>
            `;
        });
    }
    ui.innerHTML = htmlStr;
    ui.parentElement.scrollTop = currentScroll;
}

async function addFavoriteFromImage(site, tag) {
    if(isFavorite(site, tag)) return;

    await fetch("/api/favorites", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ site: site, tag: tag, action: "add" })
    });
    await loadTagsData();
}

async function removeImageHistory(filename) {
    await fetch("/api/image_history/remove", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: filename })
    });
    await loadTagsData();
}

async function clearImageHistory() {
    if(confirm("Delete all image tag history?")) {
        await fetch("/api/image_history/clear", { method: "POST" });
        await loadTagsData();
    }
}