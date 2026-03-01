/**
 * 書法風格分析系統 - 共用 JavaScript 工具
 */

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

// === 圖片放大模態 ===

/**
 * 打開圖片放大模態
 * @param {string} imageSrc - 圖片 URL
 * @param {string} caption - 圖片標題
 */
function openImageModal(imageSrc, caption = '') {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const modalCaption = document.getElementById('modalCaption');

    if (modal && modalImage && modalCaption) {
        modalImage.src = imageSrc;
        modalCaption.textContent = caption;
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';  // 防止背景滾動
    }
}

/**
 * 關閉圖片放大模態
 * @param {Event} event - 點擊事件（可選）
 */
function closeImageModal(event) {
    // 如果是點擊事件且點擊在內容上，則不關閉
    if (event && event.target.closest('.modal-content')) {
        return;
    }

    const modal = document.getElementById('imageModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = 'auto';  // 恢復背景滾動
    }
}

// 按 ESC 鍵關閉模態
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeImageModal();
        // 也關閉字元詳情 popup（如果存在）
        if (typeof closeCharDetail === 'function') closeCharDetail();
    }
});

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

