/**
 * 上傳比對頁邏輯
 */

let _selectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
    loadCalligraphers();
    setupDropArea();
    setupCharInput();
});


/** 動態加載書法家 checkbox */
async function loadCalligraphers() {
    try {
        const data = await api('/api/calligrapher/list');
        const cals = data.calligraphers || [];
        const container = document.getElementById('uploadCalCheckboxes');
        if (!container) return;
        container.innerHTML = cals.map(cal =>
            `<label class="checkbox-item">
                <input type="checkbox" value="${escapeHtml(cal.display_name)}" checked>
                <span>${escapeHtml(cal.display_name)} <small>${escapeHtml(cal.dynasty)}</small></span>
            </label>`
        ).join('');
    } catch (err) {
        console.error('無法加載書法家列表:', err);
    }
}


/** 監聽字元輸入，更新按鈕狀態 */
function setupCharInput() {
    const input = document.getElementById('uploadChar');
    if (!input) return;
    input.addEventListener('input', updateUploadBtn);
}


/** 判斷是否可執行上傳 */
function updateUploadBtn() {
    const char = (document.getElementById('uploadChar')?.value || '').trim();
    const btn  = document.getElementById('uploadBtn');
    if (btn) btn.disabled = !(char.length === 1 && _selectedFile);
}


/** 設定拖放區事件 */
function setupDropArea() {
    const area = document.getElementById('dropArea');
    if (!area) return;

    area.addEventListener('click', () => {
        const fi = document.getElementById('fileInput');
        if (fi) fi.click();
    });

    area.addEventListener('dragover', e => {
        e.preventDefault();
        area.classList.add('drag-over');
    });

    area.addEventListener('dragleave', () => area.classList.remove('drag-over'));

    area.addEventListener('drop', e => {
        e.preventDefault();
        area.classList.remove('drag-over');
        const file = e.dataTransfer?.files?.[0];
        if (file) handleFileSelect(file);
    });
}


/** 處理選擇的圖片檔案 */
function handleFileSelect(file) {
    if (!file || !file.type.startsWith('image/')) {
        alert('請選擇圖片檔案（JPG/PNG/WebP/BMP）');
        return;
    }
    if (file.size > 5 * 1024 * 1024) {
        alert('圖片超過 5 MB，請選擇較小的圖片');
        return;
    }

    _selectedFile = file;
    updateUploadBtn();

    // 顯示預覽
    const reader = new FileReader();
    reader.onload = e => {
        const inner = document.getElementById('dropInner');
        if (!inner) return;
        inner.innerHTML = `
            <img src="${e.target.result}" class="preview-img" alt="預覽">
            <button class="preview-overlay" onclick="clearFile(event)" title="移除">✕</button>
            <p style="font-size:0.82rem;color:var(--text-muted);margin-top:0.5rem">
                ${escapeHtml(file.name)} (${(file.size / 1024).toFixed(0)} KB)
            </p>
        `;
    };
    reader.readAsDataURL(file);
}


/** 清除已選圖片 */
function clearFile(event) {
    event?.stopPropagation();
    _selectedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('dropInner').innerHTML = `
        <div class="drop-icon">📷</div>
        <p class="drop-text">拖放圖片到這裡</p>
        <p class="drop-hint">或點擊選擇檔案</p>
        <input type="file" id="fileInput" accept="image/*" style="display:none"
               onchange="handleFileSelect(this.files[0])">
        <button class="btn btn-secondary btn-sm" onclick="document.getElementById('fileInput').click()">
            選擇圖片
        </button>
    `;
    updateUploadBtn();
}


/** 執行上傳比對 */
async function doUploadCompare() {
    const char = (document.getElementById('uploadChar')?.value || '').trim();
    if (!char || !_selectedFile) return;

    // 取得勾選的書法家
    const checkboxes = document.querySelectorAll('#uploadCalCheckboxes input[type="checkbox"]');
    const selected = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);

    // 建立 FormData
    const formData = new FormData();
    formData.append('file', _selectedFile);
    formData.append('char', char);
    if (selected.length > 0) {
        formData.append('calligraphers', selected.join(','));
    }

    // 顯示結果區（loading 狀態）
    const resultSection = document.getElementById('uploadResult');
    const resultArea    = document.getElementById('uploadResultArea');
    const resultInfo    = document.getElementById('uploadResultInfo');
    resultSection.style.display = 'block';
    showLoading(resultArea);
    resultInfo.innerHTML = '';

    const btn = document.getElementById('uploadBtn');
    btn.disabled = true;
    btn.textContent = '比對中…';

    try {
        const resp = await fetch('/api/upload/compare', {
            method: 'POST',
            body: formData,
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || '上傳失敗');
        }

        const data = await resp.json();
        const imgUrl = data.image_url + '?t=' + Date.now();

        resultArea.innerHTML = `
            <img src="${imgUrl}"
                 alt="比對結果"
                 loading="lazy"
                 onclick="openImageModal('${imgUrl.replace(/'/g, "\\'")}', '你的「${escapeHtml(char)}」與書法大師的比對')"
                 onload="hideLoading(document.getElementById('uploadResultArea'))"
                 onerror="hideLoading(document.getElementById('uploadResultArea'))">
        `;
        resultInfo.innerHTML = `<span class="found-list">✓ 已生成「${escapeHtml(char)}」的比對圖</span>`;
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    } catch (err) {
        showError(resultArea, err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '比對';
        updateUploadBtn();
    }
}


/** 重設上傳頁面 */
function resetUpload() {
    document.getElementById('uploadResult').style.display = 'none';
    document.getElementById('uploadChar').value = '';
    clearFile();
}
