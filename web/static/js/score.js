/**
 * 練字評分頁面 JS (score.js)
 *
 * 功能：
 * - 檔案拖曳上傳 + 預覽
 * - 動態載入書法家選單（依輸入字元）
 * - AJAX 評分請求
 * - 動態顯示結果（環形分數、分數條動畫）
 */

'use strict';

// ─── DOM refs ──────────────────────────────────────────────────────────────
const charInput    = document.getElementById('charInput');
const calSelect    = document.getElementById('calSelect');
const uploadZone   = document.getElementById('uploadZone');
const fileInput    = document.getElementById('fileInput');
const uploadPreview = document.getElementById('uploadPreview');
const previewImg   = document.getElementById('previewImg');
const previewFilename = document.getElementById('previewFilename');
const uploadHint   = document.getElementById('uploadHint');
const analyzeBtn   = document.getElementById('analyzeBtn');
const errorBox     = document.getElementById('scoreError');
const resultsPanel = document.getElementById('scoreResults');

let selectedFile = null;
let calFetchTimer = null;
let cachedCalligraphers = [];   // 快取：目前字的書法家清單（含圖 URL）

// ─── 字元輸入 → 動態載入書法家 ────────────────────────────────────────────

charInput.addEventListener('input', () => {
    const char = charInput.value.trim();
    clearTimeout(calFetchTimer);
    if (char.length === 1) {
        calFetchTimer = setTimeout(() => loadCalligraphers(char), 300);
    } else {
        resetCalSelect();
    }
});

async function loadCalligraphers(char) {
    try {
        const resp = await fetch(`/api/score/calligraphers?char=${encodeURIComponent(char)}`);
        if (!resp.ok) return;
        const data = await resp.json();
        const cals = data.calligraphers || [];
        cachedCalligraphers = cals;   // 快取供評分後的圖庫使用

        calSelect.innerHTML = '<option value="">自動選擇（第一位）</option>';
        cals.forEach(cal => {
            const opt = document.createElement('option');
            opt.value = cal.name;
            opt.textContent = cal.name;
            calSelect.appendChild(opt);
        });
        calSelect.disabled = cals.length === 0;
    } catch {
        resetCalSelect();
    }
}

function resetCalSelect() {
    calSelect.innerHTML = '<option value="">— 請先輸入字元 —</option>';
    calSelect.disabled = true;
}

// ─── 檔案選擇 / 拖曳 ────────────────────────────────────────────────────────

uploadZone.addEventListener('dragover', e => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
});

fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(file) {
    selectedFile = file;
    uploadZone.classList.add('has-file');
    uploadHint.style.display = 'none';
    uploadPreview.classList.add('show');
    previewFilename.textContent = file.name;

    const reader = new FileReader();
    reader.onload = e => { previewImg.src = e.target.result; };
    reader.readAsDataURL(file);
}

// ─── 評分請求 ──────────────────────────────────────────────────────────────

analyzeBtn.addEventListener('click', submitAnalysis);

async function submitAnalysis() {
    const char = charInput.value.trim();

    // 驗證
    if (!char || char.length !== 1) {
        showError('請輸入一個中文字');
        return;
    }
    if (!selectedFile) {
        showError('請上傳你的手寫字圖片');
        return;
    }

    hideError();
    setBtnLoading(true);
    resultsPanel.classList.remove('show');

    const fd = new FormData();
    fd.append('file', selectedFile);
    fd.append('char', char);
    const calName = calSelect.value.trim();
    if (calName) fd.append('cal_name', calName);

    try {
        const resp = await fetch('/api/score/analyze', { method: 'POST', body: fd });
        const data = await resp.json();
        if (!resp.ok) {
            showError(data.detail || '評分失敗，請稍後再試');
            return;
        }
        displayResults(data);
    } catch (e) {
        showError('網路錯誤，請確認伺服器正常運作');
    } finally {
        setBtnLoading(false);
    }
}

// ─── 顯示結果 ──────────────────────────────────────────────────────────────

function displayResults(data) {
    const totalPct   = Math.round(data.total_score * 100);
    const shapePct   = Math.round(data.shape_score * 100);
    const balancePct = Math.round(data.balance_score * 100);
    const bd = data.balance_detail;

    // 環形分數
    setRingScore(totalPct);

    // 總分區文字
    document.getElementById('feedbackOverall').textContent = data.feedback.overall;

    // 形態相似度
    document.getElementById('shapeScoreVal').textContent  = shapePct + '%';
    document.getElementById('shapeScoreBar').style.width  = shapePct + '%';
    document.getElementById('shapeFeedback').textContent  = data.feedback.shape;

    // 結構平衡度
    document.getElementById('balanceScoreVal').textContent = balancePct + '%';
    document.getElementById('balanceScoreBar').style.width  = balancePct + '%';
    document.getElementById('balanceFeedback').textContent  = data.feedback.balance;

    // 平衡細節 chips
    document.getElementById('chipLR').textContent = `左右 ${Math.round(bd.lr_ratio * 100)}%`;
    document.getElementById('chipTB').textContent = `上下 ${Math.round(bd.tb_ratio * 100)}%`;
    const cxDev = Math.abs(bd.centroid_x - 0.5) * 100;
    const cyDev = Math.abs(bd.centroid_y - 0.5) * 100;
    document.getElementById('chipCenter').textContent =
        `重心偏移 ${Math.round(cxDev)}% / ${Math.round(cyDev)}%`;

    // 比對圖
    document.getElementById('userCompareImg').src = previewImg.src;
    const refImg = document.getElementById('refCompareImg');
    const refLabel = document.getElementById('refCalLabel');
    if (data.ref_image_url) {
        refImg.src = data.ref_image_url;
        refImg.style.display = 'block';
    } else {
        refImg.style.display = 'none';
    }
    refLabel.textContent = `大師版本（${data.ref_cal_name}）`;

    // 筆劃差異標示圖
    const diffSection = document.getElementById('diffSection');
    const diffImg     = document.getElementById('diffImg');
    if (data.diff_image) {
        diffImg.src = data.diff_image;
        diffSection.style.display = 'block';
    } else {
        diffSection.style.display = 'none';
    }

    // 全部大師版本圖庫
    showMastersGallery(cachedCalligraphers, data.ref_cal_name);

    // 顯示結果
    resultsPanel.classList.add('show');
    resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showMastersGallery(cals, refCalName) {
    const section = document.getElementById('mastersSection');
    const grid    = document.getElementById('mastersGrid');

    if (!cals || cals.length === 0) {
        section.style.display = 'none';
        return;
    }

    grid.innerHTML = cals.map(cal => {
        const isRef = cal.name === refCalName;
        return `<div class="master-gallery-item ${isRef ? 'is-ref' : ''}"
                     onclick="openImageModal('${cal.image_url}', '${cal.name}')">
            <img src="${cal.image_url}" alt="${cal.name}" loading="lazy">
            <span class="master-gallery-name">
                ${cal.name}${isRef ? '<em>評分參照</em>' : ''}
            </span>
        </div>`;
    }).join('');

    section.style.display = 'block';
}

function setRingScore(pct) {
    const circle = document.getElementById('ringFill');
    const numEl  = document.getElementById('ringNumber');
    const r = 46;
    const circumference = 2 * Math.PI * r;

    circle.style.strokeDasharray  = circumference;
    circle.style.strokeDashoffset = circumference; // start at 0

    // Animate number
    let current = 0;
    const duration = 1000;
    const start = performance.now();

    function tick(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        current = Math.round(pct * ease);
        numEl.textContent = current;
        circle.style.strokeDashoffset = circumference * (1 - ease * pct / 100);
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

// ─── 再測按鈕 ───────────────────────────────────────────────────────────────

document.getElementById('btnRetry').addEventListener('click', () => {
    resultsPanel.classList.remove('show');
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ─── Helpers ───────────────────────────────────────────────────────────────

function showError(msg) {
    errorBox.textContent = msg;
    errorBox.classList.add('show');
}

function hideError() {
    errorBox.classList.remove('show');
}

function setBtnLoading(on) {
    analyzeBtn.disabled = on;
    analyzeBtn.classList.toggle('loading', on);
}
