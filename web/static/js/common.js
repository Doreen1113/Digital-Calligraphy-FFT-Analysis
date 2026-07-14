/**
 * 書法風格分析系統 - 共用 JavaScript 工具
 */

// === 書法家識別色（全站共用單一色盤，同一位書法家在任何頁面顏色都一致）===
// 7 色仿國畫顏料命名，經 dataviz 驗證器檢查過色盲安全性（CVD ΔE、明度帶、飽和度下限、
// 對比度皆通過），固定順序指派給書法家、不循環使用。數值跟 base.css 的 --pigment-1~7
// 一致，這裡用 JS 常數是因為 Canvas/Chart.js 畫圖時無法直接讀 CSS 變數。
const CALLIGRAPHER_COLORS = {
    '智永':   { color: '#C6242E', light: '#FBE7E8' }, // 硃砂紅
    '歐陽詢': { color: '#A6790A', light: '#F6EDD9' }, // 藤黃
    '虞世南': { color: '#1F7A4D', light: '#DFF0E7' }, // 石綠
    '顏真卿': { color: '#0B849E', light: '#DCF0F3' }, // 石青
    '柳公權': { color: '#2A5FB0', light: '#E1E9F7' }, // 靛藍
    '趙孟頫': { color: '#9C2E7A', light: '#F3DFED' }, // 紫檀
    '沈尹默': { color: '#8C4A0A', light: '#F1E2D2' }, // 赭石
};

// === 捲動淡入（給靜態渲染區塊用，見 base.css .reveal） ===
document.addEventListener('DOMContentLoaded', () => {
    const els = document.querySelectorAll('.reveal');
    if (!els.length) return;
    if (!('IntersectionObserver' in window)) {
        els.forEach(el => el.classList.add('revealed'));
        return;
    }
    const io = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                io.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -10% 0px' });
    els.forEach(el => io.observe(el));
});

// === API 請求工具 ===

/**
 * 發送 API 請求並處理錯誤
 * @param {string} path - API 路徑
 * @param {object} options - fetch 選項
 * @returns {Promise<object>} JSON 回應
 */
async function api(path, options = {}) {
    try {
        const resp = await fetch(path, options);
        if (!resp.ok) {
            let errMsg = '伺服器錯誤';
            try {
                const errData = await resp.json();
                errMsg = errData.detail || errMsg;
            } catch (e) {
                errMsg = resp.statusText || errMsg;
            }
            throw new Error(errMsg);
        }
        return await resp.json();
    } catch (err) {
        if (err.name === 'TypeError' && err.message.includes('fetch')) {
            throw new Error('無法連線到伺服器');
        }
        throw err;
    }
}

/**
 * 發送 POST 請求
 * @param {string} path - API 路徑
 * @param {object} body - 請求內容
 * @returns {Promise<object>} JSON 回應
 */
async function apiPost(path, body) {
    return api(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
}

// === UI 工具 ===

/**
 * 顯示載入動畫
 */
function showLoading(el) {
    el.innerHTML = '';
    el.classList.add('loading');
}

/**
 * 隱藏載入動畫
 */
function hideLoading(el) {
    el.classList.remove('loading');
}

/**
 * 顯示錯誤訊息
 */
function showError(container, message) {
    hideLoading(container);
    container.innerHTML = `<div class="error-msg">${escapeHtml(message)}</div>`;
}

/**
 * 顯示成功訊息
 */
function showSuccess(container, message) {
    hideLoading(container);
    container.innerHTML = `<div class="success-msg">${escapeHtml(message)}</div>`;
}

/**
 * 顯示提示訊息
 */
function showInfo(container, message) {
    hideLoading(container);
    container.innerHTML = `<div class="info-msg">${escapeHtml(message)}</div>`;
}

/**
 * HTML 跳脫（防止 XSS）
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// === 圖片放大模態（支援圖庫切換） ===

/** 圖庫狀態 */
let _modalGallery = [];
let _modalIdx     = 0;

/**
 * 打開圖片放大模態（單張模式，不顯示左右鍵）
 * @param {string} imageSrc - 圖片 URL
 * @param {string} caption  - 圖片標題
 */
function openImageModal(imageSrc, caption = '') {
    openGalleryModal([{ src: imageSrc, caption }], 0);
}

/**
 * 打開圖庫模態並從指定索引開始
 * @param {Array<{src:string, caption:string}>} images - 圖庫陣列
 * @param {number} startIdx - 起始索引
 */
function openGalleryModal(images, startIdx = 0) {
    if (!images || images.length === 0) return;
    _modalGallery = images;
    _modalIdx     = Math.max(0, Math.min(startIdx, images.length - 1));
    _renderModalAt(_modalIdx);
}

/** 渲染模態至指定索引 */
function _renderModalAt(idx) {
    const modal   = document.getElementById('imageModal');
    const img     = document.getElementById('modalImage');
    const caption = document.getElementById('modalCaption');
    const prev    = document.getElementById('modalPrev');
    const next    = document.getElementById('modalNext');
    const counter = document.getElementById('modalCounter');
    if (!modal || !img) return;

    const item   = _modalGallery[idx];
    img.src      = item.src;
    if (caption) caption.textContent = item.caption || '';

    const hasNav = _modalGallery.length > 1;
    if (prev)    prev.style.display    = hasNav ? 'flex' : 'none';
    if (next)    next.style.display    = hasNav ? 'flex' : 'none';
    if (counter) {
        counter.style.display = hasNav ? 'block' : 'none';
        counter.textContent   = `${idx + 1} / ${_modalGallery.length}`;
    }

    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

/**
 * 切換前 / 後一張（dir = -1 或 +1），循環
 */
function navigateModal(dir) {
    if (!_modalGallery.length) return;
    _modalIdx = (_modalIdx + dir + _modalGallery.length) % _modalGallery.length;
    _renderModalAt(_modalIdx);
}

/**
 * 關閉圖片放大模態
 * @param {Event} event - 點擊事件（可選）
 */
function closeImageModal(event) {
    if (event && event.target.closest('.modal-content')) return;
    const modal = document.getElementById('imageModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';
    }
}

// 鍵盤：← → 切換，ESC 關閉
document.addEventListener('keydown', function(e) {
    const modal = document.getElementById('imageModal');
    if (modal && modal.classList.contains('show')) {
        if (e.key === 'ArrowLeft')  { navigateModal(-1); return; }
        if (e.key === 'ArrowRight') { navigateModal(1);  return; }
        if (e.key === 'Escape')     { closeImageModal(); return; }
    }
    if (e.key === 'Escape') {
        if (typeof closeCharDetail === 'function') closeCharDetail();
    }
});

// 手機觸控：左右滑動切換圖片
(function initModalSwipe() {
    let _touchStartX = 0;
    let _touchStartY = 0;

    document.addEventListener('touchstart', function(e) {
        const modal = document.getElementById('imageModal');
        if (!modal || !modal.classList.contains('show')) return;
        _touchStartX = e.touches[0].clientX;
        _touchStartY = e.touches[0].clientY;
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
        const modal = document.getElementById('imageModal');
        if (!modal || !modal.classList.contains('show')) return;
        if (!_modalGallery.length || _modalGallery.length < 2) return;

        const dx = e.changedTouches[0].clientX - _touchStartX;
        const dy = e.changedTouches[0].clientY - _touchStartY;
        // 水平滑動超過 50px 且主要為水平方向
        if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
            navigateModal(dx < 0 ? 1 : -1);
        }
    }, { passive: true });
})();

// === 導航列手機版選單切換 ===
function toggleNav() {
    const navLinks = document.getElementById('navLinks');
    navLinks.classList.toggle('show');
}

// 點擊頁面其他地方關閉選單
document.addEventListener('click', function(e) {
    const nav = document.querySelector('.main-nav');
    const navLinks = document.getElementById('navLinks');
    if (navLinks && !nav.contains(e.target)) {
        navLinks.classList.remove('show');
    }
});

