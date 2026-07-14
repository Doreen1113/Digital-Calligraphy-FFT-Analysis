'use strict';

let writer = null;
let currentChar = '';
let currentSpeed = 1.0;
let totalStrokes = 0;
let strokesDone = 0;

const CANVAS_SIZE = Math.min(window.innerWidth - 80, 320);

// 頁面載入後若 URL 有 ?char= 參數，自動載入
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('strokeInput');

    // IME 支援
    let composing = false;
    input.addEventListener('compositionstart', () => { composing = true; });
    input.addEventListener('compositionend', () => {
        composing = false;
        trimInput();
    });
    input.addEventListener('input', () => {
        if (!composing) trimInput();
    });
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') loadCharacter();
    });

    const params = new URLSearchParams(location.search);
    const ch = params.get('char') || '永';   // 沒指定字時，預設顯示「永」（永字八法，涵蓋楷書基本筆畫）
    input.value = ch;
    loadCharacter();
});

function trimInput() {
    const input = document.getElementById('strokeInput');
    const val = input.value;
    if (val.length > 1) input.value = val[val.length - 1];
}

function quickLoad(ch) {
    document.getElementById('strokeInput').value = ch;
    loadCharacter();
}

function highlightQuickChar(ch) {
    document.querySelectorAll('.quick-char-btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent === ch);
    });
}

function loadCharacter() {
    const input = document.getElementById('strokeInput');
    const ch = input.value.trim();
    if (!ch || ch.length !== 1) return;

    currentChar = ch;
    strokesDone = 0;
    highlightQuickChar(ch);

    const target = document.getElementById('strokeTarget');
    target.innerHTML = '';

    document.getElementById('strokeMain').style.display = 'none';
    document.getElementById('strokeNotFound').style.display = 'none';
    document.getElementById('strokeProgressRow').style.display = 'none';

    // 建立 HanziWriter（需要非同步載入字元資料）
    try {
        writer = HanziWriter.create('strokeTarget', ch, {
            width: CANVAS_SIZE,
            height: CANVAS_SIZE,
            padding: 20,
            showOutline: true,
            strokeColor: '#231F1C',   // 濃墨黑（帶一點暖褐），比原本的淺褐色更接近真實墨色
            outlineColor: '#D4C5A0',
            strokeAnimationSpeed: currentSpeed,
            delayBetweenStrokes: 300,
            onLoadCharDataSuccess: (data) => {
                // 成功載入
                totalStrokes = data.strokes ? data.strokes.length : 0;
                document.getElementById('strokeCharTitle').textContent = `「${ch}」共 ${totalStrokes} 畫`;
                buildStepButtons(totalStrokes);
                document.getElementById('strokeMain').style.display = 'block';
                document.getElementById('strokeNotFound').style.display = 'none';
                // 自動播放一次
                animateChar();
            },
            onLoadCharDataError: () => {
                document.getElementById('notFoundChar').textContent = ch;
                document.getElementById('strokeNotFound').style.display = 'block';
                document.getElementById('strokeMain').style.display = 'none';
            },
        });
    } catch (e) {
        document.getElementById('notFoundChar').textContent = ch;
        document.getElementById('strokeNotFound').style.display = 'block';
    }

    loadInkRevealPickers(ch);
}

// ─── 真跡漸進浮現：用書法家真實筆跡，不是印刷字型 ──────────────────────────
let lastInkSvg = null;

async function loadInkRevealPickers(ch) {
    const section = document.getElementById('inkRevealSection');
    const picker = document.getElementById('inkCalPicker');
    const wrap = document.getElementById('inkRevealWrap');
    const replayBtn = document.getElementById('btnReplayInk');
    if (!section || !picker) return;

    wrap.style.display = 'none';
    replayBtn.style.display = 'none';
    lastInkSvg = null;

    try {
        const data = await api(`/api/character/info/${encodeURIComponent(ch)}`);
        const entries = Object.entries(data.calligraphers || {});
        if (!entries.length) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'flex';
        picker.innerHTML = '';
        entries.forEach(([label, images], idx) => {
            if (!images.length) return;
            const btn = document.createElement('button');
            btn.className = `ink-cal-btn${idx === 0 ? ' active' : ''}`;
            btn.textContent = label;
            btn.addEventListener('click', () => {
                picker.querySelectorAll('.ink-cal-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                showInkReveal(images[0].image_url);
            });
            picker.appendChild(btn);
        });

        // 預設顯示第一位書法家
        showInkReveal(entries[0][1][0].image_url);
    } catch (e) {
        section.style.display = 'none';
    }
}

async function showInkReveal(imageUrl) {
    const wrap = document.getElementById('inkRevealWrap');
    const target = document.getElementById('inkRevealTarget');
    const replayBtn = document.getElementById('btnReplayInk');
    if (!target) return;

    const relPath = imageUrl.replace(/^\/fonts\//, '');
    try {
        const data = await api(`/api/character/ink-reveal?path=${encodeURIComponent(relPath)}`);
        lastInkSvg = data.svg;
        target.innerHTML = lastInkSvg;
        wrap.style.display = 'flex';
        replayBtn.style.display = 'inline-flex';
    } catch (e) {
        wrap.style.display = 'none';
        replayBtn.style.display = 'none';
    }
}

function replayInkReveal() {
    const target = document.getElementById('inkRevealTarget');
    if (!target || !lastInkSvg) return;
    // 重新插入同一份 SVG，讓 CSS 動畫從頭開始播放
    target.innerHTML = '';
    // 強制 reflow，確保瀏覽器真的把舊的 SVG 移除後才插入新的（否則動畫不會重播）
    void target.offsetWidth;
    target.innerHTML = lastInkSvg;
}

function animateChar() {
    if (!writer) return;
    strokesDone = 0;
    updateStepButtons(-1);
    writer.animateCharacter({
        onComplete: () => {
            strokesDone = totalStrokes;
            updateStepButtons(totalStrokes - 1);
        }
    });
}

function showOutline() {
    if (!writer) return;
    writer.showCharacter({ duration: 400 });
}

function hideChar() {
    if (!writer) return;
    writer.hideCharacter({ duration: 300 });
    strokesDone = 0;
    updateStepButtons(-1);
}

function startQuiz() {
    if (!writer) return;
    strokesDone = 0;
    updateStepButtons(-1);
    writer.quiz({
        onMistake: (strokeData) => {
            // 畫錯時紅色提示（HanziWriter 內建）
        },
        onCorrectStroke: (strokeData) => {
            strokesDone = strokeData.strokeNum + 1;
            updateStepButtons(strokeData.strokeNum);
        },
        onComplete: (summaryData) => {
            updateStepButtons(totalStrokes - 1);
        }
    });
}

function updateSpeed(val) {
    currentSpeed = parseFloat(val);
    document.getElementById('speedLabel').textContent = currentSpeed.toFixed(1) + 'x';
    if (writer) {
        writer.updateColor('strokeColor', '#231F1C');   // 觸發設定更新（workaround）
        // HanziWriter 3.x 可用 setOption（若有）
        try { writer.setOptions({ strokeAnimationSpeed: currentSpeed }); } catch {}
    }
}

function buildStepButtons(n) {
    const container = document.getElementById('strokeStepBtns');
    container.innerHTML = '';
    for (let i = 1; i <= n; i++) {
        const btn = document.createElement('button');
        btn.className = 'step-btn';
        btn.textContent = i;
        btn.title = `顯示到第 ${i} 畫`;
        btn.addEventListener('click', () => showToStroke(i - 1));
        container.appendChild(btn);
    }
    document.getElementById('strokeProgressRow').style.display = n > 0 ? 'flex' : 'none';
}

function updateStepButtons(doneIdx) {
    const btns = document.querySelectorAll('.step-btn');
    btns.forEach((btn, i) => {
        btn.classList.toggle('done', i <= doneIdx);
    });
}

function showToStroke(idx) {
    if (!writer) return;
    writer.animateCharacter({
        strokeAnimationSpeed: 3,
        delayBetweenStrokes: 0,
        onComplete: () => {}
    });
    // 先顯示到指定筆畫：hideCharacter 再逐筆 animateStroke
    writer.hideCharacter({ duration: 0 });
    let i = 0;
    function nextStroke() {
        if (i > idx) {
            updateStepButtons(idx);
            return;
        }
        writer.animateStroke(i, {
            strokeAnimationSpeed: 3,
            onComplete: () => { i++; nextStroke(); }
        });
    }
    nextStroke();
}
