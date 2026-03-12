/**
 * 首頁 - 同字比對邏輯
 */

// === 常數 ===
const HISTORY_KEY = 'calligraphy_history';
const GUIDE_KEY   = 'guide_dismissed';
const MAX_HISTORY = 20;


document.addEventListener('DOMContentLoaded', () => {
    loadCalligraphers();       // 動態加載書法家
    loadCommonCharacters();    // 全部共有字
    loadStats();               // 字元統計
    loadSiteStats();           // 網站瀏覽統計
    renderHistory();           // 歷史紀錄
    initGuideBanner();         // 新手引導 banner

    // Enter 鍵觸發比對
    const charInput = document.getElementById('charInput');
    charInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') doCompare();
    });

    // 輸入時自動觸發（單字輸入完成後）
    charInput.addEventListener('input', () => {
        const val = charInput.value.trim();
        if (val.length === 1 && isChinese(val)) {
            clearTimeout(charInput._timer);
            charInput._timer = setTimeout(() => doCompare(), 300);
        }
    });

    // 支援從 URL 參數載入字元（如 /?char=天）
    const urlParams = new URLSearchParams(window.location.search);
    const charFromUrl = urlParams.get('char');
    if (charFromUrl && charFromUrl.length === 1) {
        charInput.value = charFromUrl;
        setTimeout(() => doCompare(), 500);
    }
});


/**
 * 執行比對
 */
async function doCompare() {
    const charInput = document.getElementById('charInput');
    const resultSection = document.getElementById('resultSection');
    const resultArea = document.getElementById('resultArea');
    const resultInfo = document.getElementById('resultInfo');

    const char = charInput.value.trim();
    if (!char || char.length !== 1) {
        showError(resultArea, '請輸入單一中文字元');
        resultSection.style.display = 'block';
        return;
    }

    // 取得選中的書法家
    const selected = getSelectedCalligraphers();
    if (selected.length === 0) {
        showError(resultArea, '請至少勾選一位書法家');
        resultSection.style.display = 'block';
        return;
    }

    // 建構查詢參數
    const params = new URLSearchParams();
    params.set('char', char);
    if (selected.length < 99) {
        selected.forEach(s => params.append('calligraphers', s));
    }

    // 顯示載入中
    resultSection.style.display = 'block';
    showLoading(resultArea);
    resultInfo.innerHTML = '';

    try {
        const data = await api(`/api/character/compare?${params}`);

        // 顯示結果圖片
        const imgUrl = data.image_url + '?t=' + Date.now();
        resultArea.innerHTML = `
            <img src="${imgUrl}"
                 alt="字元比對: ${char}"
                 class="comparison-img"
                 loading="lazy"
                 onclick="openImageModal('${imgUrl.replace(/'/g, "\\'")}', '字元「${char}」的比對結果')"
                 onload="hideLoading(document.getElementById('resultArea'))"
                 onerror="hideLoading(document.getElementById('resultArea'))">
        `;

        // 顯示資訊
        let infoHtml = `<span class="found-list">✓ 找到 ${data.calligraphers_found.length} 位書法家：${data.calligraphers_found.join('、')}</span>`;
        if (data.calligraphers_missing && data.calligraphers_missing.length > 0) {
            infoHtml += `<br><span class="missing-list">✗ 字庫中無此字：${data.calligraphers_missing.join('、')}</span>`;
        }
        resultInfo.innerHTML = infoHtml;

        // 加入歷史紀錄
        addToHistory(char);

        // 標記快速選字按鈕
        highlightActivePill(char);

    } catch (err) {
        showError(resultArea, err.message);
    }

    // 滾動到結果區
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}


/**
 * 動態加載書法家列表
 */
async function loadCalligraphers() {
    try {
        const data = await api('/api/calligrapher/list');
        const calligraphers = data.calligraphers || [];

        const container = document.getElementById('calCheckboxes');
        if (!container) return;

        // 依 display_name 去重（同一書法家多本字帖只顯示一次）
        const seenCal = new Set();
        const uniqueCals = calligraphers.filter(cal => {
            if (seenCal.has(cal.display_name)) return false;
            seenCal.add(cal.display_name);
            return true;
        });

        container.innerHTML = uniqueCals.map(cal =>
            `<label class="checkbox-item">
                <input type="checkbox" value="${escapeHtml(cal.display_name)}">
                <span>${escapeHtml(cal.display_name)} <small>${escapeHtml(cal.dynasty)}</small></span>
            </label>`
        ).join('');

        // 更新全選按鈕狀態
        _updateSelectAllBtn();

        // 更新統計：書法家數（去重）、字帖數（全部）、圖片總數
        const statCalligraphers = document.getElementById('statCalligraphers');
        if (statCalligraphers) statCalligraphers.textContent = uniqueCals.length;

        const statBooks = document.getElementById('statBooks');
        if (statBooks) statBooks.textContent = calligraphers.length;

        const totalImages = calligraphers.reduce((sum, cal) => sum + (cal.total_images || 0), 0);
        const statImages = document.getElementById('statImages');
        if (statImages) statImages.textContent = totalImages.toLocaleString();
    } catch (err) {
        console.error('無法加載書法家列表:', err);
    }
}


/**
 * 取得勾選的書法家
 */
function getSelectedCalligraphers() {
    const checkboxes = document.querySelectorAll('#calCheckboxes input[type="checkbox"]');
    return Array.from(checkboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);
}


/**
 * 載入共有字按鈕
 */
async function loadCommonCharacters() {
    const container = document.getElementById('commonChars');
    const countBadge = document.getElementById('commonCount');

    try {
        const data = await api('/api/character/common');
        countBadge.textContent = `${data.total} 字`;

        container.innerHTML = data.characters.map(char =>
            `<button class="char-pill" onclick="quickCompare('${char}')" title="${char}">${char}</button>`
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
        document.getElementById('statTotal').textContent = data.total_characters || '-';
        document.getElementById('statCommon').textContent = data.common_characters_count || '-';
        // 更新輸入框旁的提示
        const hint = document.getElementById('charTotalHint');
        if (hint && data.total_characters) hint.textContent = data.total_characters.toLocaleString();
    } catch (err) {
        // 靜默失敗
    }
}


/**
 * 載入網站訪客統計
 */
async function loadSiteStats() {
    try {
        const data = await api('/api/stats/overview');
        const statViews    = document.getElementById('statViews');
        const statVisitors = document.getElementById('statVisitors');
        if (statViews)    statViews.textContent    = data.total_views    || 0;
        if (statVisitors) statVisitors.textContent = data.unique_visitors || 0;
    } catch (err) {
        // 靜默失敗
    }
}


/**
 * 快速比對（從共有字按鈕觸發）—— 自動選全部書法家
 */
function quickCompare(char) {
    const charInput = document.getElementById('charInput');
    charInput.value = char;
    // 先全選，確保顯示所有書法家
    const checkboxes = document.querySelectorAll('#calCheckboxes input[type="checkbox"]');
    checkboxes.forEach(cb => { cb.checked = true; });
    _updateSelectAllBtn();
    doCompare();
}


/**
 * 高亮當前選中的字
 */
function highlightActivePill(char) {
    document.querySelectorAll('.char-pill').forEach(pill => {
        pill.classList.toggle('active', pill.textContent === char);
    });
}


/**
 * 判斷是否為中文字
 */
function isChinese(char) {
    const code = char.charCodeAt(0);
    return code >= 0x4E00 && code <= 0x9FFF;
}


// ============================
// === 歷史紀錄（localStorage）===
// ============================

/**
 * 加入歷史紀錄
 */
function addToHistory(char) {
    if (!char || !isChinese(char)) return;
    let history = getHistory();
    // 移到最前（避免重複）
    history = history.filter(c => c !== char);
    history.unshift(char);
    if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    renderHistory();
}


/**
 * 讀取歷史紀錄
 */
function getHistory() {
    try {
        return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    } catch {
        return [];
    }
}


/**
 * 清除歷史紀錄
 */
function clearHistory() {
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
}


/**
 * 渲染歷史紀錄區塊
 */
function renderHistory() {
    const section   = document.getElementById('historySection');
    const container = document.getElementById('historyChars');
    if (!section || !container) return;

    const history = getHistory();
    if (history.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    container.innerHTML = history.map(char =>
        `<button class="char-pill" onclick="quickCompare('${escapeHtml(char)}')" title="${escapeHtml(char)}">${escapeHtml(char)}</button>`
    ).join('');
}


// ============================
// === 新手引導 banner ===
// ============================

/**
 * 全選 / 全取消 書法家 checkbox
 */
function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('#calCheckboxes input[type="checkbox"]');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    checkboxes.forEach(cb => { cb.checked = !allChecked; });
    _updateSelectAllBtn();
}

function _updateSelectAllBtn() {
    const btn = document.getElementById('selectAllBtn');
    if (!btn) return;
    const checkboxes = document.querySelectorAll('#calCheckboxes input[type="checkbox"]');
    const allChecked = checkboxes.length > 0 && Array.from(checkboxes).every(cb => cb.checked);
    btn.textContent = allChecked ? '全取消' : '全選';
}

// 每次 checkbox 狀態變化時同步按鈕文字
document.addEventListener('change', e => {
    if (e.target.closest('#calCheckboxes')) _updateSelectAllBtn();
});


/**
 * 初始化引導 banner：若未曾關閉則顯示
 */
function initGuideBanner() {
    if (localStorage.getItem(GUIDE_KEY)) return;
    const banner = document.getElementById('guideBanner');
    if (banner) banner.classList.add('show');
}


/**
 * 關閉引導 banner 並記住使用者選擇
 */
function dismissGuide() {
    localStorage.setItem(GUIDE_KEY, '1');
    const banner = document.getElementById('guideBanner');
    if (!banner) return;
    banner.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    banner.style.opacity = '0';
    banner.style.transform = 'translateY(-6px)';
    setTimeout(() => { banner.style.display = 'none'; }, 300);
}


