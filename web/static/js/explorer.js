/**
 * 字元探索頁邏輯
 * 支援：書法家數量篩選、依書法家篩選（同個書法家）、排序、搜尋、分頁
 */

// === 狀態 ===
let currentMinCount    = 1;
let currentMaxCount    = 5;   // 動態更新為實際書法家數
let currentPage        = 1;
let currentSort        = 'default';
let currentCalligrapher = null;  // null = 全部書法家
const perPage = 200;


document.addEventListener('DOMContentLoaded', () => {
    loadFilterButtons();       // 書法家數量篩選按鈕
    loadCalligrapherFilter();  // 同個書法家篩選按鈕
    loadCharacters();
    loadStatsBar();

    // Enter 鍵搜尋
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') doSearch();
    });
});


// ============================================================
// === 篩選按鈕：書法家數量 ===
// ============================================================

/**
 * 動態加載書法家數量篩選按鈕
 */
async function loadFilterButtons() {
    try {
        const data = await api('/api/calligrapher/list');
        const calligraphers = data.calligraphers || [];
        const maxCalligraphers = calligraphers.length;
        currentMaxCount = maxCalligraphers;

        const container = document.getElementById('filterBtns');
        if (!container) return;

        const buttons = [
            { label: '全部', min: 1, max: maxCalligraphers },
            { label: `${maxCalligraphers} 位 (共有字)`, min: maxCalligraphers, max: maxCalligraphers },
        ];
        if (maxCalligraphers >= 3) buttons.push({ label: '3+ 位', min: 3, max: maxCalligraphers });
        if (maxCalligraphers >= 2) buttons.push({ label: '2+ 位', min: 2, max: maxCalligraphers });
        buttons.push({ label: '僅 1 位', min: 1, max: 1 });

        container.innerHTML = buttons.map((btn, idx) =>
            `<button class="filter-btn ${idx === 0 ? 'active' : ''}"
                     onclick="setCountFilter(this, ${btn.min}, ${btn.max})">${escapeHtml(btn.label)}</button>`
        ).join('');

    } catch (err) {
        console.error('無法加載篩選按鈕:', err);
    }
}


/**
 * 設定書法家數量篩選
 */
function setCountFilter(btn, min, max) {
    currentMinCount = min;
    currentMaxCount = max;
    currentPage = 1;
    // 只更新數量篩選按鈕的 active 狀態
    document.querySelectorAll('#filterBtns .filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadCharacters();
}


// ============================================================
// === 篩選按鈕：同個書法家 ===
// ============================================================

/**
 * 動態加載書法家篩選按鈕（同個書法家）
 */
async function loadCalligrapherFilter() {
    try {
        const data = await api('/api/calligrapher/list');
        const calligraphers = data.calligraphers || [];

        const container = document.getElementById('calFilterBtns');
        if (!container) return;

        // 「全部」 + 各書法家
        const allBtn = `<button class="filter-btn active" onclick="setCalligrapherFilter(this, null)">全部書法家</button>`;
        const calBtns = calligraphers.map(cal =>
            `<button class="filter-btn"
                     onclick="setCalligrapherFilter(this, '${escapeHtml(cal.display_name)}')"
                     title="${escapeHtml(cal.dynasty)} | ${escapeHtml(cal.total_images || 0)} 張">
                ${escapeHtml(cal.display_name)}
             </button>`
        ).join('');

        container.innerHTML = allBtn + calBtns;

    } catch (err) {
        console.error('無法加載書法家篩選:', err);
    }
}


/**
 * 設定書法家篩選（同個書法家）
 */
function setCalligrapherFilter(btn, calligrapher) {
    currentCalligrapher = calligrapher;
    currentPage = 1;
    document.querySelectorAll('#calFilterBtns .filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadCharacters();
}


// ============================================================
// === 排序 ===
// ============================================================

/**
 * 設定排序方式
 */
function setSortOrder(btn, sortBy) {
    currentSort = sortBy;
    currentPage = 1;
    document.querySelectorAll('#sortBtns .filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadCharacters();
}


// ============================================================
// === 字元載入 ===
// ============================================================

/**
 * 載入字元（依目前所有篩選條件 + 排序）
 */
async function loadCharacters() {
    const grid       = document.getElementById('charGrid');
    const pagination = document.getElementById('pagination');
    const filterInfo = document.getElementById('filterInfo');

    showLoading(grid);
    pagination.innerHTML = '';

    try {
        const params = new URLSearchParams({
            page:        currentPage,
            per_page:    perPage,
            min_count:   currentMinCount,
            max_count:   currentMaxCount,
            sort_by:     currentSort,
        });
        if (currentCalligrapher) {
            params.set('calligrapher', currentCalligrapher);
        }

        const data = await api(`/api/search/characters?${params}`);

        // 更新統計列
        let infoText = `共 ${data.total} 個字元（第 ${data.page} / ${data.total_pages} 頁）`;
        if (currentCalligrapher) infoText += ` — 篩選：${currentCalligrapher}`;
        if (currentSort !== 'default') {
            const sortLabel = { freq: '字頻序', strokes_asc: '筆畫少→多', strokes_desc: '筆畫多→少' };
            infoText += ` — 排序：${sortLabel[currentSort] || currentSort}`;
        }
        filterInfo.textContent = infoText;

        // 渲染字元網格
        if (data.characters.length === 0) {
            grid.innerHTML = '<div class="info-msg">沒有符合條件的字元</div>';
            return;
        }

        grid.innerHTML = data.characters.map(char =>
            `<div class="char-tile" onclick="goToCompare('${char}')" title="點擊比對「${char}」">${char}</div>`
        ).join('');

        renderPagination(data.page, data.total_pages);

    } catch (err) {
        showError(grid, err.message);
    }
}


// ============================================================
// === 搜尋 ===
// ============================================================

/**
 * 搜尋字元
 */
async function doSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        currentPage = 1;
        loadCharacters();
        return;
    }

    const grid       = document.getElementById('charGrid');
    const filterInfo = document.getElementById('filterInfo');
    const pagination = document.getElementById('pagination');

    showLoading(grid);
    pagination.innerHTML = '';

    try {
        const data = await api(`/api/search/query?q=${encodeURIComponent(query)}`);
        filterInfo.textContent = `搜尋「${query}」：找到 ${data.total} 個字元`;

        if (data.results.length === 0) {
            grid.innerHTML = '<div class="info-msg">沒有找到符合的字元</div>';
            return;
        }

        grid.innerHTML = data.results.map(char =>
            `<div class="char-tile" onclick="goToCompare('${char}')" title="點擊比對「${char}」">${char}</div>`
        ).join('');

    } catch (err) {
        showError(grid, err.message);
    }
}


// ============================================================
// === 統計列 ===
// ============================================================

/**
 * 載入統計資訊（初始顯示）
 */
async function loadStatsBar() {
    try {
        const data   = await api('/api/search/stats');
        const counts = data.by_calligrapher_count || {};
        const info   = document.getElementById('filterInfo');

        // 動態組合統計文字
        const parts = Object.entries(counts)
            .sort(([a], [b]) => Number(b) - Number(a))
            .map(([n, c]) => `${n} 位：${c} 字`);

        info.textContent = `共 ${data.total_characters} 個字元 | ${parts.join(' | ')}`;
    } catch (err) {
        // 靜默
    }
}


// ============================================================
// === 分頁 ===
// ============================================================

/**
 * 渲染分頁按鈕
 */
function renderPagination(current, total) {
    const pagination = document.getElementById('pagination');
    if (total <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';
    html += `<button class="page-btn" onclick="goToPage(${current - 1})" ${current <= 1 ? 'disabled' : ''}>&#8249; 上一頁</button>`;

    const maxVisible = 7;
    let start = Math.max(1, current - Math.floor(maxVisible / 2));
    let end   = Math.min(total, start + maxVisible - 1);
    if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1);

    if (start > 1) {
        html += `<button class="page-btn" onclick="goToPage(1)">1</button>`;
        if (start > 2) html += `<span style="padding:0 0.3rem;color:var(--text-muted)">…</span>`;
    }

    for (let i = start; i <= end; i++) {
        html += `<button class="page-btn ${i === current ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }

    if (end < total) {
        if (end < total - 1) html += `<span style="padding:0 0.3rem;color:var(--text-muted)">…</span>`;
        html += `<button class="page-btn" onclick="goToPage(${total})">${total}</button>`;
    }

    html += `<button class="page-btn" onclick="goToPage(${current + 1})" ${current >= total ? 'disabled' : ''}>下一頁 &#8250;</button>`;
    pagination.innerHTML = html;
}


/**
 * 跳到指定頁
 */
function goToPage(page) {
    currentPage = page;
    loadCharacters();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}


/**
 * 跳到首頁比對指定字元
 */
function goToCompare(char) {
    window.location.href = `/?char=${encodeURIComponent(char)}`;
}
