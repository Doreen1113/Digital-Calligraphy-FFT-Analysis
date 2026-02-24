/**
 * 首頁 - 同字比對邏輯
 */

document.addEventListener('DOMContentLoaded', () => {
    loadCalligraphers();  // 動態加載書法家
    loadCommonCharacters();
    loadStats();

    // Enter 鍵觸發比對
    const charInput = document.getElementById('charInput');
    charInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') doCompare();
    });

    // 輸入時自動觸發（單字輸入完成後）
    charInput.addEventListener('input', () => {
        const val = charInput.value.trim();
        if (val.length === 1 && isChinese(val)) {
            // 短暫延遲後自動比對
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
    if (selected.length < 4) {
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

        // 標記快速選字按鈕
        highlightActivePill(char);

    } catch (err) {
        showError(resultArea, err.message);
    }

    // 滾動到結果區
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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

        container.innerHTML = calligraphers.map(cal =>
            `<label class="checkbox-item">
                <input type="checkbox" value="${escapeHtml(cal.display_name)}" checked>
                <span>${escapeHtml(cal.display_name)} <small>${escapeHtml(cal.dynasty)}</small></span>
            </label>`
        ).join('');

        // 更新統計中的書法家數量和總圖片數
        const statCalligraphers = document.getElementById('statCalligraphers');
        if (statCalligraphers) {
            statCalligraphers.textContent = calligraphers.length;
        }

        const totalImages = calligraphers.reduce((sum, cal) => sum + (cal.total_images || 0), 0);
        const statImages = document.getElementById('statImages');
        if (statImages) {
            statImages.textContent = totalImages;
        }
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
 * 載入統計數據
 */
async function loadStats() {
    try {
        const data = await api('/api/search/stats');
        document.getElementById('statTotal').textContent = data.total_characters || '-';
        document.getElementById('statCommon').textContent = data.common_characters_count || '-';
    } catch (err) {
        // 靜默失敗
    }
}


/**
 * 快速比對（從共有字按鈕觸發）
 */
function quickCompare(char) {
    const charInput = document.getElementById('charInput');
    charInput.value = char;
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
