/**
 * 字元探索頁邏輯
 */

let currentMinCount = 1;
let currentMaxCount = 4;
let currentPage = 1;
const perPage = 200;

document.addEventListener('DOMContentLoaded', () => {
    loadCharacters();
    loadStatsBar();

    // Enter 鍵搜尋
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') doSearch();
    });
});


/**
 * 設定篩選條件
 */
function setFilter(btn, min, max) {
    currentMinCount = min;
    currentMaxCount = max;
    currentPage = 1;

    // 更新按鈕狀態
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    loadCharacters();
}


/**
 * 載入字元
 */
async function loadCharacters() {
    const grid = document.getElementById('charGrid');
    const pagination = document.getElementById('pagination');
    const filterInfo = document.getElementById('filterInfo');

    showLoading(grid);
    pagination.innerHTML = '';

    try {
        const params = new URLSearchParams({
            page: currentPage,
            per_page: perPage,
            min_count: currentMinCount,
            max_count: currentMaxCount,
        });

        const data = await api(`/api/search/characters?${params}`);

        filterInfo.textContent = `共 ${data.total} 個字元（第 ${data.page} / ${data.total_pages} 頁）`;

        // 渲染字元網格
        if (data.characters.length === 0) {
            grid.innerHTML = '<div class="info-msg">沒有符合條件的字元</div>';
            return;
        }

        grid.innerHTML = data.characters.map(char =>
            `<div class="char-tile" onclick="goToCompare('${char}')" title="點擊比對「${char}」">${char}</div>`
        ).join('');

        // 渲染分頁
        renderPagination(data.page, data.total_pages);

    } catch (err) {
        showError(grid, err.message);
    }
}


/**
 * 搜尋字元
 */
async function doSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        loadCharacters();
        return;
    }

    const grid = document.getElementById('charGrid');
    const filterInfo = document.getElementById('filterInfo');
    const pagination = document.getElementById('pagination');

    showLoading(grid);
    pagination.innerHTML = '';

    try {
        const data = await api(`/api/search/query?q=${encodeURIComponent(query)}`);

        filterInfo.textContent = `搜尋「${query}」: 找到 ${data.total} 個字元`;

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


/**
 * 載入統計資訊
 */
async function loadStatsBar() {
    try {
        const data = await api('/api/search/stats');
        const counts = data.by_calligrapher_count || {};
        const info = document.getElementById('filterInfo');
        info.textContent = `共 ${data.total_characters} 個字元 | 4位共有: ${counts[4] || 0} | 3位: ${counts[3] || 0} | 2位: ${counts[2] || 0} | 1位: ${counts[1] || 0}`;
    } catch (err) {
        // 靜默
    }
}


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

    // 上一頁
    html += `<button class="page-btn" onclick="goToPage(${current - 1})" ${current <= 1 ? 'disabled' : ''}>&#8249; 上一頁</button>`;

    // 頁碼
    const maxVisible = 7;
    let start = Math.max(1, current - Math.floor(maxVisible / 2));
    let end = Math.min(total, start + maxVisible - 1);
    if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1);

    if (start > 1) {
        html += `<button class="page-btn" onclick="goToPage(1)">1</button>`;
        if (start > 2) html += `<span style="padding:0 0.3rem;color:var(--text-muted)">...</span>`;
    }

    for (let i = start; i <= end; i++) {
        html += `<button class="page-btn ${i === current ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }

    if (end < total) {
        if (end < total - 1) html += `<span style="padding:0 0.3rem;color:var(--text-muted)">...</span>`;
        html += `<button class="page-btn" onclick="goToPage(${total})">${total}</button>`;
    }

    // 下一頁
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
