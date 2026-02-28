/**
 * 批次比對頁邏輯
 * 支援：依字元排序、依書法家排序、單一字圖片顯示
 */

document.addEventListener('DOMContentLoaded', () => {
    loadBatchCalligraphers();

    const input = document.getElementById('batchInput');
    input.addEventListener('input', () => {
        document.getElementById('charCount').textContent = input.value.length;
    });
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') doBatchCompare();
    });
});


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

        // 更新進度
        progressFill.style.width = '100%';
        progressText.textContent = `完成！成功 ${data.success_count} / ${data.total}`;

        // 根據排序模式顯示結果
        if (sortMode === 'calligrapher') {
            renderByCalligrapher(results, resultsDiv);
        } else {
            renderByCharacter(results, resultsDiv);
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
 * 渲染簡化的圖片卡片（圖片 + 下方書法家·字帖標籤）
 * @param {string} label      - 顯示在圖片下方的標籤（通常為 font_label）
 * @param {string} imageUrl   - 圖片 URL
 * @param {string} character  - 字元（用於 alt 與 modal 標題）
 * @param {string} calligrapher - 書法家名稱（可選，僅用於 modal 標題）
 * @param {string} book       - 字帖名稱（可選，用於 modal 標題）
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
        <div class="char-image-card-simple">
            <img src="${imgUrlWithCache}"
                 alt="${escapeHtml(alt)}"
                 loading="lazy"
                 onclick="openImageModal('${imgUrlWithCache.replace(/'/g, "\\'")}', '${escapeHtml(modalTitle)}')">
            <div class="card-label">${escapeHtml(label)}</div>
        </div>
    `;
}
