/**
 * 筆劃診斷頁面 JS (score.js)
 *
 * 功能：
 * - 檔案拖曳上傳 + 預覽
 * - 上傳一次圖片，一次跟全部有寫過該字的書法家比對（/api/score/analyze_all）
 * - 結果依形態相似度排序成清單，點擊某位書法家展開詳細比對
 *   （分項量測：形態相似度/結構平衡度 + 差異疊圖）
 * - 差異疊圖支援「差異敏感度」滑桿：後端回傳重心對齊後的墨跡遮罩，
 *   前端在 canvas 上即時膨脹（dilate）後重繪疊圖，不用每次調整都重打 API
 */

'use strict';

// ─── 引導 banner ──────────────────────────────────────────────────────────
(function initScoreGuide() {
    if (localStorage.getItem('score_guide_dismissed')) return;
    const banner = document.getElementById('scoreGuideBanner');
    if (banner) banner.classList.add('show');
})();

function dismissScoreGuide() {
    localStorage.setItem('score_guide_dismissed', '1');
    const banner = document.getElementById('scoreGuideBanner');
    if (!banner) return;
    banner.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    banner.style.opacity = '0';
    banner.style.transform = 'translateY(-6px)';
    setTimeout(() => { banner.style.display = 'none'; }, 300);
}

// ─── DOM refs ──────────────────────────────────────────────────────────────
const charInput      = document.getElementById('charInput');
const uploadZone      = document.getElementById('uploadZone');
const fileInput       = document.getElementById('fileInput');
const uploadPreview   = document.getElementById('uploadPreview');
const previewImg      = document.getElementById('previewImg');
const previewFilename = document.getElementById('previewFilename');
const uploadHint      = document.getElementById('uploadHint');
const analyzeBtn      = document.getElementById('analyzeBtn');
const errorBox        = document.getElementById('scoreError');
const resultsPanel    = document.getElementById('scoreResults');
const detailSection   = document.getElementById('detailSection');
const diffCanvas      = document.getElementById('diffCanvas');
const diffSensitivity = document.getElementById('diffSensitivity');
const diffSensitivityValue = document.getElementById('diffSensitivityValue');

let selectedFile = null;
let lastResults  = [];   // 快取：這次分析回傳的全部書法家比對結果
let currentMasks = null; // 目前選定書法家的墨跡遮罩 { userInk, refInk, w, h }（供滑桿即時重繪）
let maskLoadToken = 0;   // 避免使用者快速切換書法家時，較舊的圖片載入完成後蓋掉新的結果

// 手動對齊：重心自動對齊不一定準，讓使用者自己拖曳其中一層微調。
// 兩層各自獨立記錄位移量，拖曳時只移動目前選定的那一層。
let userOffset = { x: 0, y: 0 };
let refOffset  = { x: 0, y: 0 };
let dragLayer  = 'user';

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

// ─── 診斷請求 ──────────────────────────────────────────────────────────────

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
    detailSection.style.display = 'none';

    const fd = new FormData();
    fd.append('file', selectedFile);
    fd.append('char', char);

    try {
        const resp = await fetch('/api/score/analyze_all', { method: 'POST', body: fd });
        let data;
        try {
            data = await resp.json();
        } catch {
            // 伺服器回應非 JSON（可能正在冷啟動）
            if (resp.status === 503 || resp.status === 502) {
                showError('伺服器啟動中，請稍待 10 秒後再試');
            } else {
                showError(`伺服器回應異常（${resp.status}），請稍後再試`);
            }
            return;
        }
        if (!resp.ok) {
            showError(data.detail || '分析失敗，請稍後再試');
            return;
        }
        displayResults(data);
    } catch (e) {
        showError('無法連線到伺服器，請確認網路連線正常');
    } finally {
        setBtnLoading(false);
    }
}

// ─── 顯示結果：排行清單 ──────────────────────────────────────────────────────

function displayResults(data) {
    lastResults = data.results || [];

    if (lastResults.length === 0) {
        showError(`字庫中找不到「${data.char}」的書法家比對資料`);
        return;
    }

    renderRankingList(lastResults);
    selectResult(0);

    resultsPanel.classList.add('show');
    resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderRankingList(results) {
    const list = document.getElementById('rankingList');
    list.innerHTML = results.map((r, idx) => {
        const shapePct = Math.round(r.shape_score * 100);
        // 只顯示形態相似度——這是唯一會隨比對對象變化、真正用來排序的數字。
        // 結構平衡度只跟使用者自己的字有關，跟比對哪位書法家無關，全部卡片都會
        // 是同一個值，放在這裡沒有鑑別度，只留在下方「分項量測」詳細區塊呈現一次。
        return `<div class="ranking-card" data-idx="${idx}" onclick="selectResult(${idx})">
            <span class="ranking-rank">#${idx + 1}</span>
            <img src="${r.ref_image_url}" class="ranking-thumb" alt="${r.ref_cal_name}" loading="lazy">
            <div class="ranking-info">
                <span class="ranking-name">${r.ref_cal_name}</span>
                <span class="ranking-scores">形態相似度 ${shapePct}%</span>
            </div>
        </div>`;
    }).join('');
}

function selectResult(idx) {
    const r = lastResults[idx];
    if (!r) return;

    document.querySelectorAll('.ranking-card').forEach(el => {
        el.classList.toggle('active', Number(el.dataset.idx) === idx);
    });

    // 字形比對圖
    document.getElementById('userCompareImg').src = previewImg.src;
    const refImg   = document.getElementById('refCompareImg');
    const refLabel = document.getElementById('refCalLabel');
    if (r.ref_image_url) {
        refImg.src = r.ref_image_url;
        refImg.style.display = 'block';
    } else {
        refImg.style.display = 'none';
    }
    refLabel.textContent = `大師版本（${r.ref_cal_name}）`;

    // 分項量測
    showMetrics(r);

    // 筆劃差異標示圖（含差異敏感度滑桿）
    const diffSection = document.getElementById('diffSection');
    if (r.user_mask_image && r.ref_mask_image) {
        diffSection.style.display = 'block';
        diffSensitivity.value = 0;
        diffSensitivityValue.textContent = '精確比對';
        loadMasksForResult(r);
    } else {
        diffSection.style.display = 'none';
        currentMasks = null;
    }

    detailSection.style.display = 'flex';
}

// ─── 差異疊圖：載入遮罩 + 即時膨脹重繪 ──────────────────────────────────────

function loadMaskPixels(dataUrl) {
    return new Promise(resolve => {
        if (!dataUrl) { resolve(null); return; }
        const img = new Image();
        img.onload = () => {
            const off = document.createElement('canvas');
            off.width = img.width;
            off.height = img.height;
            const ctx = off.getContext('2d');
            ctx.drawImage(img, 0, 0);
            const data = ctx.getImageData(0, 0, img.width, img.height).data;
            const out = new Uint8Array(img.width * img.height);
            for (let i = 0; i < out.length; i++) {
                out[i] = data[i * 4] > 128 ? 1 : 0;   // 遮罩是灰階，R=G=B
            }
            resolve({ pixels: out, w: img.width, h: img.height });
        };
        img.onerror = () => resolve(null);
        img.src = dataUrl;
    });
}

async function loadMasksForResult(r) {
    const token = ++maskLoadToken;
    const [user, ref] = await Promise.all([
        loadMaskPixels(r.user_mask_image),
        loadMaskPixels(r.ref_mask_image),
    ]);
    if (token !== maskLoadToken) return;   // 使用者已經切到別位書法家，捨棄這次結果
    if (!user || !ref) {
        currentMasks = null;
        return;
    }
    currentMasks = { userInk: user.pixels, refInk: ref.pixels, w: user.w, h: user.h };
    userOffset = { x: 0, y: 0 };
    refOffset  = { x: 0, y: 0 };
    renderDiffCanvas();
}

function dilateMask(mask, w, h, iterations) {
    let cur = mask;
    for (let it = 0; it < iterations; it++) {
        const next = new Uint8Array(cur.length);
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const idx = y * w + x;
                if (cur[idx]) { next[idx] = 1; continue; }
                let on = 0;
                for (let dy = -1; dy <= 1 && !on; dy++) {
                    const ny = y + dy;
                    if (ny < 0 || ny >= h) continue;
                    for (let dx = -1; dx <= 1; dx++) {
                        const nx = x + dx;
                        if (nx < 0 || nx >= w) continue;
                        if (cur[ny * w + nx]) { on = 1; break; }
                    }
                }
                next[idx] = on;
            }
        }
        cur = next;
    }
    return cur;
}

// 位移取樣：每一層各自有自己的 x/y 位移（拖曳調整用），超出畫布範圍視為空白
function sampleAt(mask, w, h, x, y, offset) {
    const sx = x - offset.x, sy = y - offset.y;
    if (sx < 0 || sx >= w || sy < 0 || sy >= h) return 0;
    return mask[sy * w + sx];
}

function renderDiffCanvas() {
    if (!currentMasks) return;
    const { userInk, refInk, w, h } = currentMasks;
    const iterations = Number(diffSensitivity.value);
    const u = iterations > 0 ? dilateMask(userInk, w, h, iterations) : userInk;
    const r = iterations > 0 ? dilateMask(refInk, w, h, iterations) : refInk;

    diffCanvas.width = w;
    diffCanvas.height = h;
    const ctx = diffCanvas.getContext('2d');
    const imgData = ctx.createImageData(w, h);

    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const um = sampleAt(u, w, h, x, y, userOffset);
            const rm = sampleAt(r, w, h, x, y, refOffset);
            let cr, cg, cb;
            if (um && rm)       { cr = 70;  cg = 70;  cb = 70; }   // 相符 → 深灰
            else if (um && !rm) { cr = 220; cg = 60;  cb = 60; }   // 多寫 → 紅
            else if (!um && rm) { cr = 60;  cg = 110; cb = 220; }  // 少寫 → 藍
            else                { cr = 240; cg = 240; cb = 240; }  // 空白 → 淺灰

            const o = (y * w + x) * 4;
            imgData.data[o]     = cr;
            imgData.data[o + 1] = cg;
            imgData.data[o + 2] = cb;
            imgData.data[o + 3] = 255;
        }
    }
    ctx.putImageData(imgData, 0, 0);
}

diffSensitivity.addEventListener('input', () => {
    const level = Number(diffSensitivity.value);
    diffSensitivityValue.textContent = level === 0 ? '精確比對' : `容忍 ${level} 像素`;
    renderDiffCanvas();
});

function openDiffCanvasModal() {
    openImageModal(diffCanvas.toDataURL('image/png'), '筆劃差異標示（對齊重心後比對）');
}

// ─── 手動對齊：拖曳其中一層微調位置（兩層各自獨立可拖） ──────────────────
const diffDragToggle = document.getElementById('diffDragToggle');
const btnResetAlign  = document.getElementById('btnResetAlign');

if (diffDragToggle) {
    diffDragToggle.addEventListener('click', (e) => {
        const btn = e.target.closest('.diff-drag-btn');
        if (!btn) return;
        dragLayer = btn.dataset.layer;
        diffDragToggle.querySelectorAll('.diff-drag-btn').forEach(b => b.classList.toggle('active', b === btn));
    });
}

if (btnResetAlign) {
    btnResetAlign.addEventListener('click', () => {
        userOffset = { x: 0, y: 0 };
        refOffset  = { x: 0, y: 0 };
        renderDiffCanvas();
    });
}

let diffDragging      = false;
let diffDragStartAt   = null;
let diffDragStartOff  = null;
let diffDragMoved     = false;

function diffCanvasScale() {
    const rect = diffCanvas.getBoundingClientRect();
    return { x: diffCanvas.width / rect.width, y: diffCanvas.height / rect.height };
}

function startDiffDrag(clientX, clientY) {
    if (!currentMasks) return;
    diffDragging = true;
    diffDragMoved = false;
    diffDragStartAt = { x: clientX, y: clientY };
    const target = dragLayer === 'user' ? userOffset : refOffset;
    diffDragStartOff = { x: target.x, y: target.y };
}

function moveDiffDrag(clientX, clientY) {
    if (!diffDragging) return;
    const scale = diffCanvasScale();
    const dx = (clientX - diffDragStartAt.x) * scale.x;
    const dy = (clientY - diffDragStartAt.y) * scale.y;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) diffDragMoved = true;
    const target = dragLayer === 'user' ? userOffset : refOffset;
    target.x = Math.round(diffDragStartOff.x + dx);
    target.y = Math.round(diffDragStartOff.y + dy);
    renderDiffCanvas();
}

function endDiffDrag() {
    diffDragging = false;
}

diffCanvas.addEventListener('mousedown', (e) => {
    if (!currentMasks) return;
    startDiffDrag(e.clientX, e.clientY);
    e.preventDefault();
});
window.addEventListener('mousemove', (e) => moveDiffDrag(e.clientX, e.clientY));
window.addEventListener('mouseup', endDiffDrag);

diffCanvas.addEventListener('touchstart', (e) => {
    if (!currentMasks || !e.touches[0]) return;
    startDiffDrag(e.touches[0].clientX, e.touches[0].clientY);
}, { passive: true });
diffCanvas.addEventListener('touchmove', (e) => {
    if (!e.touches[0]) return;
    moveDiffDrag(e.touches[0].clientX, e.touches[0].clientY);
    e.preventDefault();
}, { passive: false });
diffCanvas.addEventListener('touchend', endDiffDrag);

diffCanvas.addEventListener('click', () => {
    if (diffDragMoved) return;
    openDiffCanvasModal();
});

function showMetrics(data) {
    const section = document.getElementById('metricsSection');
    if (typeof data.shape_score !== 'number' || typeof data.balance_score !== 'number') {
        section.style.display = 'none';
        return;
    }

    const shapePct = Math.round(data.shape_score * 100);
    const balancePct = Math.round(data.balance_score * 100);

    document.getElementById('shapeScoreValue').textContent = `${shapePct}%`;
    document.getElementById('shapeScoreBar').style.width = `${shapePct}%`;
    document.getElementById('shapeFeedback').textContent = data.feedback?.shape || '';

    document.getElementById('balanceScoreValue').textContent = `${balancePct}%`;
    document.getElementById('balanceScoreBar').style.width = `${balancePct}%`;
    document.getElementById('balanceFeedback').textContent = data.feedback?.balance || '';

    section.style.display = 'block';
}

// ─── 再測按鈕 ───────────────────────────────────────────────────────────────

document.getElementById('btnRetry').addEventListener('click', () => {
    resultsPanel.classList.remove('show');
    detailSection.style.display = 'none';
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
