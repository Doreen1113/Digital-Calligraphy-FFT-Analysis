/**
 * 字庫搜尋頁邏輯
 * 支援：依字元排序、依書法家排序、單一字圖片顯示、最近查詢
 */

const COMPARE_HISTORY_KEY = 'calligraphy_history';
const COMPARE_MAX_HISTORY = 20;

document.addEventListener('DOMContentLoaded', () => {
    loadBatchCalligraphers();
    renderCompareHistory();

    const input = document.getElementById('batchInput');
    input.addEventListener('input', () => {
        document.getElementById('charCount').textContent = input.value.length;
    });
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') doBatchCompare();
    });

    // 支援從外部頁面帶入字元（?chars=天）
    const urlParams = new URLSearchParams(window.location.search);
    const charsFromUrl = urlParams.get('chars');
    if (charsFromUrl) {
        input.value = charsFromUrl.slice(0, 50);
        document.getElementById('charCount').textContent = input.value.length;
        setTimeout(() => doBatchCompare(), 600);
    }
});

// ── 最近查詢（localStorage）─────────────────────────────────────────────

function getCompareHistory() {
    try { return JSON.parse(localStorage.getItem(COMPARE_HISTORY_KEY) || '[]'); }
    catch { return []; }
}

function addToCompareHistory(chars) {
    if (!chars) return;
    let history = getCompareHistory();
    for (const char of chars) {
        history = history.filter(c => c !== char);
        history.unshift(char);
    }
    if (history.length > COMPARE_MAX_HISTORY) history = history.slice(0, COMPARE_MAX_HISTORY);
    localStorage.setItem(COMPARE_HISTORY_KEY, JSON.stringify(history));
    renderCompareHistory();
}

function clearCompareHistory() {
    localStorage.removeItem(COMPARE_HISTORY_KEY);
    renderCompareHistory();
}

function renderCompareHistory() {
    const section   = document.getElementById('compareHistorySection');
    const container = document.getElementById('compareHistoryChars');
    if (!section || !container) return;
    const history = getCompareHistory();
    if (history.length === 0) { section.style.display = 'none'; return; }
    section.style.display = 'block';
    container.innerHTML = history.map(char =>
        `<button class="char-pill" onclick="quickFillAndCompare('${escapeHtml(char)}')"
                 title="搜尋「${escapeHtml(char)}」">${escapeHtml(char)}</button>`
    ).join('');
}

function quickFillAndCompare(char) {
    const input = document.getElementById('batchInput');
    input.value = char;
    document.getElementById('charCount').textContent = char.length;
    doBatchCompare();
}


/**
 * 動態加載批次頁面的書法家列表
 */
async function loadBatchCalligraphers() {
    try {
        const data = await api('/api/calligrapher/list');
        const calligraphers = data.calligraphers || [];

        const container = document.getElementById('batchCalCheckboxes');
        if (!container) return;

        // 依 display_name 去重，只顯示書法家姓名（不顯示碑帖）
        const seenBatch = new Set();
        const uniqueBatch = calligraphers.filter(cal => {
            if (seenBatch.has(cal.display_name)) return false;
            seenBatch.add(cal.display_name);
            return true;
        });

        container.innerHTML = uniqueBatch.map(cal =>
            `<label class="checkbox-item">
                <input type="checkbox" value="${escapeHtml(cal.display_name)}" checked>
                ${escapeHtml(cal.display_name)}
            </label>`
        ).join('');
    } catch (err) {
        console.error('無法加載書法家列表:', err);
    }
}


/**
 * 取得目前選擇的排序模式
 */
function getSortMode() {
    const radios = document.querySelectorAll('input[name="sortMode"]');
    for (const radio of radios) {
        if (radio.checked) return radio.value;
    }
    return 'character';
}


/**
 * 執行批次比對
 */
async function doBatchCompare() {
    const input = document.getElementById('batchInput');
    const resultSection = document.getElementById('batchResultSection');
    const resultsDiv = document.getElementById('batchResults');
    const progressDiv = document.getElementById('batchProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const countBadge = document.getElementById('batchResultCount');

    const chars = input.value.trim();
    if (!chars) {
        alert('請輸入至少一個字元');
        return;
    }

    // 取得選中的書法家
    const checkboxes = document.querySelectorAll('#batchCalCheckboxes input:checked');
    const selected = Array.from(checkboxes).map(cb => cb.value);
    if (selected.length === 0) {
        alert('請至少選擇一位書法家');
        return;
    }

    const sortMode = getSortMode();

    // 顯示結果區與進度
    resultSection.style.display = 'block';
    progressDiv.style.display = 'flex';
    resultsDiv.innerHTML = '';
    progressFill.style.width = '0%';
    progressText.textContent = '準備中...';

    try {
        const data = await apiPost('/api/character/batch', {
            characters: chars,
            calligraphers: selected,
            sort_mode: sortMode,
        });

        const results = data.results || [];
        countBadge.textContent = `${data.success_count} / ${data.total}`;

        // 加入最近查詢紀錄（個別字元）
        addToCompareHistory([...chars]);

        // 更新進度
        progressFill.style.width = '100%';
        progressText.textContent = `完成！成功 ${data.success_count} / ${data.total}`;

        // 根據排序模式顯示結果
        if (sortMode === 'calligrapher') {
            renderByCalligrapher(results, resultsDiv);
        } else {
            renderByCharacter(results, resultsDiv);
        }

        // 設定圖庫點擊（事件委派，只需設定一次）
        if (!resultsDiv._galleryReady) {
            attachGalleryClickHandlers(resultsDiv);
            resultsDiv._galleryReady = true;
        }

    } catch (err) {
        showError(resultsDiv, err.message);
        progressDiv.style.display = 'none';
    }
}


/**
 * 依字元排序顯示（同一個字的所有書法家橫排在一起）
 */
function renderByCharacter(results, container) {
    container.innerHTML = '';
    
    results.forEach(r => {
        if (r.error) {
            // 錯誤的字元
            const errorGroup = document.createElement('div');
            errorGroup.className = 'batch-group';
            errorGroup.innerHTML = `
                <div class="batch-group-header">
                    <span class="group-title-char">${escapeHtml(r.character)}</span>
                    <span class="count-badge">錯誤</span>
                </div>
                <div class="batch-group-content">
                    <div class="char-image-card">
                        <div class="result-error">${escapeHtml(r.error)}</div>
                    </div>
                </div>
            `;
            container.appendChild(errorGroup);
            return;
        }
        
        const images = r.images || [];
        const group = document.createElement('div');
        group.className = 'batch-group';

        // 依書法家名稱排序，使同一書法家的多本字帖相鄰
        const sortedImages = [...images].sort((a, b) => {
            const artistA = a.artist || (a.calligrapher ? a.calligrapher.split('·')[0] : '');
            const artistB = b.artist || (b.calligrapher ? b.calligrapher.split('·')[0] : '');
            return artistA.localeCompare(artistB, 'zh-TW');
        });

        // 依字元排序：圖片下方只顯示書法家名稱（不含碑帖）
        group.innerHTML = `
            <div class="batch-group-header">
                <span class="group-title-char">${escapeHtml(r.character)}</span>
                <span class="count-badge">${sortedImages.length} 位書法家</span>
            </div>
            <div class="batch-group-content batch-row">
                ${sortedImages.map(img => {
                    const artist = img.artist || (img.calligrapher ? img.calligrapher.split('·')[0] : '');
                    return renderImageCardSimple(artist, img.image_url, r.character, artist, img.book || '');
                }).join('')}
            </div>
        `;
        
        container.appendChild(group);
    });
}


/**
 * 依書法家排序顯示（同一個書法家的所有字橫排在一起）
 */
function renderByCalligrapher(results, container) {
    container.innerHTML = '';
    
    // 重新組織資料：以書法家 display_name 分組（同一書法家多本字帖合在一起）
    const calGroups = {};

    results.forEach(r => {
        if (r.error) return;

        const images = r.images || [];
        images.forEach(img => {
            // 以 artist（display_name）作為分組 key，不含碑帖名
            const artist = img.artist || (img.calligrapher ? img.calligrapher.split('·')[0] : img.calligrapher);
            if (!calGroups[artist]) {
                calGroups[artist] = [];
            }
            calGroups[artist].push({
                character: r.character,
                image_url: img.image_url,
                artist:    artist,
                book:      img.book || '',
            });
        });
    });

    // 渲染各書法家的分組
    for (const artist in calGroups) {
        const chars = calGroups[artist];
        const group = document.createElement('div');
        group.className = 'batch-group';

        // 標題只顯示書法家名稱；圖片下方顯示字元；點開 modal 顯示完整出處
        group.innerHTML = `
            <div class="batch-group-header">
                <span class="group-title-cal">${escapeHtml(artist)}</span>
                <span class="count-badge">${chars.length} 個字</span>
            </div>
            <div class="batch-group-content batch-row">
                ${chars.map(item =>
                    renderImageCardSimple(item.character, item.image_url, item.character, item.artist, item.book)
                ).join('')}
            </div>
        `;

        container.appendChild(group);
    }
    
    // 顯示沒有找到的字元
    const errors = results.filter(r => r.error);
    if (errors.length > 0) {
        const errorGroup = document.createElement('div');
        errorGroup.className = 'batch-group batch-group-error';
        errorGroup.innerHTML = `
            <div class="batch-group-header" style="background: var(--accent);">
                未找到的字元
                <span class="count-badge">${errors.length} 個</span>
            </div>
            <div class="batch-group-content batch-row">
                ${errors.map(r => `
                    <div class="char-image-card-simple">
                        <div class="card-error-char">${escapeHtml(r.character)}</div>
                        <div class="card-label">未找到</div>
                    </div>
                `).join('')}
            </div>
        `;
        container.appendChild(errorGroup);
    }
}


/**
 * 渲染簡化的圖片卡片（圖片 + 下方標籤），使用 data 屬性儲存圖庫資訊
 * @param {string} label      - 顯示在圖片下方的標籤
 * @param {string} imageUrl   - 圖片 URL
 * @param {string} character  - 字元（用於 alt 與 modal 標題）
 * @param {string} calligrapher - 書法家名稱（可選）
 * @param {string} book       - 字帖名稱（可選）
 */
function renderImageCardSimple(label, imageUrl, character, calligrapher = '', book = '') {
    const imgUrlWithCache = imageUrl + '?t=' + Date.now();
    // modal 標題格式：【字】出自於 書法家 的〔字帖〕
    let modalTitle;
    if (calligrapher && book) {
        modalTitle = `【${character}】出自於 ${calligrapher} 的〔${book}〕`;
    } else if (calligrapher) {
        modalTitle = `${calligrapher}的「${character}」`;
    } else {
        modalTitle = `「${character}」`;
    }
    const alt = modalTitle;

    return `
        <div class="char-image-card-simple"
             data-img="${escapeHtml(imgUrlWithCache)}"
             data-caption="${escapeHtml(modalTitle)}">
            <img src="${imgUrlWithCache}"
                 alt="${escapeHtml(alt)}"
                 loading="lazy">
            <div class="card-label">${escapeHtml(label)}</div>
        </div>
    `;
}

/**
 * 為結果容器設定圖庫點擊事件（事件委派）
 * 點擊群組內任一卡片 → 以整個群組內的圖片建立圖庫並開啟
 */
function attachGalleryClickHandlers(container) {
    container.addEventListener('click', function(e) {
        const card = e.target.closest('.char-image-card-simple[data-img]');
        if (!card) return;

        // 找同一 batch-group-content 內的所有卡片
        const group = card.closest('.batch-group-content');
        const scope = group || container;
        const allCards = Array.from(scope.querySelectorAll('.char-image-card-simple[data-img]'));
        const idx      = allCards.indexOf(card);
        const images   = allCards.map(c => ({ src: c.dataset.img, caption: c.dataset.caption || '' }));

        openGalleryModal(images, idx >= 0 ? idx : 0);
    });
}
