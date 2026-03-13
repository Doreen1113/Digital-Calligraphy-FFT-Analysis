/**
 * 字庫搜尋頁 - 瀏覽字庫，點擊前往批次比對
 */

const HISTORY_KEY = 'calligraphy_history';
const MAX_HISTORY = 20;

document.addEventListener('DOMContentLoaded', () => {
    loadCommonCharacters();
    loadStats();
    loadSiteStats();
    loadCalligrapherStats();
    renderHistory();
});


/**
 * 前往批次比對（點擊字元時觸發）
 */
function goToCompare(char) {
    window.location.href = `/compare?chars=${encodeURIComponent(char)}`;
}


/**
 * 載入共有字按鈕
 */
async function loadCommonCharacters() {
    const container  = document.getElementById('commonChars');
    const countBadge = document.getElementById('commonCount');
    try {
        const data = await api('/api/character/common');
        if (countBadge) countBadge.textContent = `${data.total} 字`;
        container.innerHTML = data.characters.map(char =>
            `<button class="char-pill" onclick="goToCompare('${char}')"
                     title="點擊比對「${char}」">${char}</button>`
        ).join('');
    } catch (err) {
        container.innerHTML = `<span class="error-msg">載入失敗: ${escapeHtml(err.message)}</span>`;
    }
}


/**
 * 載入字元統計數據
 */
async function loadStats() {
    try {
        const data = await api('/api/search/stats');
        const elTotal  = document.getElementById('statTotal');
        const elCommon = document.getElementById('statCommon');
        const hint     = document.getElementById('charTotalHint');
        if (elTotal)  elTotal.textContent  = data.total_characters || '-';
        if (elCommon) elCommon.textContent = data.common_characters_count || '-';
        if (hint && data.total_characters) hint.textContent = data.total_characters.toLocaleString();
    } catch { /* 靜默失敗 */ }
}


/**
 * 載入書法家 / 字帖 / 圖片統計
 */
async function loadCalligrapherStats() {
    try {
        const data = await api('/api/calligrapher/list');
        const calligraphers = data.calligraphers || [];
        const seenCal = new Set();
        const uniqueCals = calligraphers.filter(cal => {
            if (seenCal.has(cal.display_name)) return false;
            seenCal.add(cal.display_name);
            return true;
        });
        const elCal    = document.getElementById('statCalligraphers');
        const elBooks  = document.getElementById('statBooks');
        const elImages = document.getElementById('statImages');
        if (elCal)    elCal.textContent    = uniqueCals.length;
        if (elBooks)  elBooks.textContent  = calligraphers.length;
        const totalImages = calligraphers.reduce((s, c) => s + (c.total_images || 0), 0);
        if (elImages) elImages.textContent = totalImages.toLocaleString();
    } catch { /* 靜默失敗 */ }
}


/**
 * 載入網站訪客統計
 */
async function loadSiteStats() {
    try {
        const data = await api('/api/stats/overview');
        const elViews    = document.getElementById('statViews');
        const elVisitors = document.getElementById('statVisitors');
        if (elViews)    elViews.textContent    = data.total_views    || 0;
        if (elVisitors) elVisitors.textContent = data.unique_visitors || 0;
    } catch { /* 靜默失敗 */ }
}


// ============================
// === 歷史紀錄（localStorage）===
// ============================

function addToHistory(char) {
    if (!char) return;
    let history = getHistory();
    history = history.filter(c => c !== char);
    history.unshift(char);
    if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    renderHistory();
}

function getHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
    catch { return []; }
}

function clearHistory() {
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
}

function renderHistory() {
    const section   = document.getElementById('historySection');
    const container = document.getElementById('historyChars');
    if (!section || !container) return;
    const history = getHistory();
    if (history.length === 0) { section.style.display = 'none'; return; }
    section.style.display = 'block';
    container.innerHTML = history.map(char =>
        `<button class="char-pill" onclick="goToCompare('${escapeHtml(char)}')"
                 title="前往比對「${escapeHtml(char)}」">${escapeHtml(char)}</button>`
    ).join('');
}
