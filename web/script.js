let globalNetConfig = { "proxy_url": "", "use_proxy": false, "verify_tls": false };
let globalWallpapers = {
    "Main": "Rem_main.png", "Neko": "Rem_neko.jpg", "Zero": "Rem_zero.jpg",
    "Waifu": "Rem_waifu.png", "Safe": "Rem_safe.jpg", "Rule34": "Rem_rule34.jpg",
    "Gelbooru": "Rem_gelbooru.jpg", "NekosLife": "Rem_nekos_life.jpg", "Yande": "Rem_yande.jpg", "ApiSettings": "Rem_option.jpg",
    "History": "Rem_history.jpg"
};

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

            Object.keys(globalWallpapers).forEach(key => {
                let confKey = key === "ApiSettings" ? "wp_options" : 
                             (key === "NekosLife" ? "wp_nekos_life" : `wp_${key.toLowerCase()}`);
                if(config[confKey]) globalWallpapers[key] = config[confKey];
                
                let inputEl = document.getElementById(confKey);
                if(inputEl) inputEl.value = globalWallpapers[key];
            });

            document.body.style.backgroundImage = `url('user_wallpapers/${globalWallpapers["Main"]}')`;
        }
    } catch (e) { console.error("Config error:", e); }

    try {
        let resp = await fetch("/api/folder");
        let data = await resp.json();
        if (data.folder) document.getElementById("folderDisplay").innerText = data.folder;
    } catch (e) {}

    // Initialize Nekos.best dropdown
    updateNekoDropdown();
    updateNekosLifeType();

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
        typeEl.style.color = "#ff9ff3";
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

async function uploadWallpaper(inputId, tabName, fileInput) {
    if (!fileInput.files || fileInput.files.length === 0) return;
    let file = fileInput.files[0];
    let formData = new FormData();
    formData.append("file", file);

    try {
        let resp = await fetch("/api/upload_wallpaper", { method: "POST", body: formData });
        let result = await resp.json();
        if (result.success) {
            document.getElementById(inputId).value = result.filename;
            await saveWallpapers();
            
            let activeTabBtn = document.querySelector(".tab-btn.active");
            if (activeTabBtn && activeTabBtn.getAttribute("onclick").includes(`'${tabName}'`)) {
                document.body.style.backgroundImage = `url('user_wallpapers/${result.filename}')`;
            }
        } else {
            alert("Error: " + result.error);
        }
    } catch (e) { alert("Upload failed: " + e); }

    // این خط حافظه مرورگر را پاک میکند تا بتوانی یک عکس را چند بار پشت سر هم انتخاب کنی
    fileInput.value = "";
}

async function saveWallpapers() {
    let wpConfig = {
        "wp_main": document.getElementById("wp_main").value.trim(),
        "wp_neko": document.getElementById("wp_neko").value.trim(),
        "wp_nekos_life": document.getElementById("wp_nekos_life").value.trim(),
        "wp_zero": document.getElementById("wp_zero").value.trim(),
        "wp_waifu": document.getElementById("wp_waifu").value.trim(),
        "wp_safe": document.getElementById("wp_safe").value.trim(),
        "wp_rule34": document.getElementById("wp_rule34").value.trim(),
        "wp_yande": document.getElementById("wp_yande").value.trim(),
        "wp_gelbooru": document.getElementById("wp_gelbooru").value.trim(),
        "wp_options": document.getElementById("wp_options").value.trim(),
        "wp_history": document.getElementById("wp_history").value.trim()
    };
    try {
        await fetch("/api/config", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(wpConfig) });
        
        globalWallpapers["Main"] = wpConfig.wp_main;
        globalWallpapers["Neko"] = wpConfig.wp_neko;
        globalWallpapers["NekosLife"] = wpConfig.wp_nekos_life;
        globalWallpapers["Zero"] = wpConfig.wp_zero;
        globalWallpapers["Waifu"] = wpConfig.wp_waifu;
        globalWallpapers["Safe"] = wpConfig.wp_safe;
        globalWallpapers["Rule34"] = wpConfig.wp_rule34;
        globalWallpapers["Gelbooru"] = wpConfig.wp_gelbooru;
        globalWallpapers["Yande"] = wpConfig.wp_yande;
        globalWallpapers["ApiSettings"] = wpConfig.wp_options;
        globalWallpapers["History"] = wpConfig.wp_history;

        document.getElementById("wpSaveStatus").textContent = "Saved!";
        setTimeout(()=> document.getElementById("wpSaveStatus").textContent = "", 2000);
    } catch(e){}
}

async function resetWallpapers() {
    document.getElementById('wp_main').value = 'Rem_main.png';
    document.getElementById('wp_neko').value = 'Rem_neko.jpg';
    document.getElementById('wp_nekos_life').value = 'Rem_nekos_life.jpg';
    document.getElementById('wp_zero').value = 'Rem_zero.jpg';
    document.getElementById('wp_waifu').value = 'Rem_waifu.png';
    document.getElementById('wp_safe').value = 'Rem_safe.jpg';
    document.getElementById('wp_rule34').value = 'Rem_rule34.jpg';
    document.getElementById('wp_gelbooru').value = 'Rem_gelbooru.jpg';
    document.getElementById('wp_yande').value = 'Rem_yande.jpg';
    document.getElementById('wp_options').value = 'Rem_option.jpg';
    document.getElementById('wp_history').value = 'Rem_history.jpg';
    
    await saveWallpapers();
    
    let activeTabBtn = document.querySelector(".tab-btn.active");
    if (activeTabBtn) {
        let tabMatch = activeTabBtn.getAttribute("onclick").match(/'([^']+)'/);
        if (tabMatch) document.body.style.backgroundImage = `url('user_wallpapers/${globalWallpapers[tabMatch[1]]}')`;
    }
    logToConsole('main', "All wallpapers have been reset to their defaults.");
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
    document.body.style.backgroundImage = `url('user_wallpapers/${globalWallpapers[tabName]}')`;
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
        htmlStr = "<p style='color: gray; font-size: 13px;'>No search history yet.</p>";
    } else {
        historyTags.forEach(item => {
            let isFav = isFavorite(item.site, item.tag);
            let heartIcon = isFav ? "💖" : "🤍";

            htmlStr += `
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.5); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);">
                    <div>
                        <span style="color: #ff9ff3; font-size: 11px; text-transform: uppercase; border: 1px solid #ff9ff3; padding: 2px 5px; border-radius: 4px; margin-right: 10px;">${item.site}</span>
                        <span style="font-size: 14px; color: white;">${item.tag}</span>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="action-btn" style="padding: 4px 8px; font-size: 12px; background: transparent; border: 1px solid rgba(255,255,255,0.2);" onclick="jumpToSite('${item.site}', '${item.tag}')">➡️</button>
                        <button class="action-btn" style="padding: 4px 8px; font-size: 12px; background: transparent; border: 1px solid rgba(255,255,255,0.2);" onclick="toggleFavorite('${item.site}', '${item.tag}')">${heartIcon}</button>
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
        ui.innerHTML = "<p style='color: gray; font-size: 12px;'>Click 🤍 in the History tab to add favorites.</p>";
        return;
    }

    favoriteTags.forEach(item => {
        ui.innerHTML += `
            <div style="background: rgba(0, 210, 211, 0.2); border: 1px solid #00d2d3; padding: 5px 10px; border-radius: 20px; font-size: 13px; display: flex; align-items: center; gap: 5px; transition: 0.2s;">
                <span onclick="jumpToSite('${item.site}', '${item.tag}')" style="cursor: pointer; display: flex; align-items: center; gap: 5px; flex: 1;">
                    <span>❄️</span>
                    <span style="color: #00d2d3; font-weight: bold; font-size: 10px; text-transform: uppercase;">[${item.site}]</span>
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
        htmlStr = "<p style='color: gray; font-size: 13px;'>No images downloaded yet.</p>";
    } else {
        imageHistory.forEach(img => {
            let tagsHtml = img.tags.map(t => {
                let isFav = isFavorite(img.site, t);
                let bgColor = isFav ? "rgba(255, 159, 243, 0.2)" : "rgba(255,255,255,0.1)";
                let borderColor = isFav ? "#ff9ff3" : "transparent";
                return `<span onclick="addFavoriteFromImage('${img.site}', '${t}')" style="background: ${bgColor}; border: 1px solid ${borderColor}; padding: 4px 10px; border-radius: 6px; font-size: 11px; cursor: pointer; transition: 0.2s; white-space: nowrap; display: inline-block;">${t}</span>`;
            }).join('');

            let artistHtml = img.artists && img.artists.length > 0 
                ? `<div style="margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px;">
                       <span style="color: #00d2d3; font-size: 12px; font-weight: bold;">Artists:</span> 
                       <span style="font-size: 12px; color: #ccc;">${img.artists.join(', ')}</span>
                   </div>` 
                : "";

            htmlStr += `
                <div style="background: rgba(0,0,0,0.6); padding: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); position: relative;">
                    <button onclick="removeImageHistory('${img.filename}')" class="action-btn stop-btn" style="position: absolute; top: 10px; right: 10px; padding: 2px 6px; font-size: 10px;">&#10060;</button>
                    <h3 style="color: white; font-size: 16px; margin-bottom: 12px; padding-right: 30px; word-break: break-all;">${img.filename} <span style="font-size: 10px; color: #ff9ff3; border: 1px solid #ff9ff3; padding: 2px 4px; border-radius: 4px; vertical-align: middle; margin-left: 10px;">${img.site}</span></h3>
                    
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