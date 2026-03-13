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
    const ch = params.get('char');
    if (ch && ch.length === 1) {
        input.value = ch;
        loadCharacter();
    }
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

function loadCharacter() {
    const input = document.getElementById('strokeInput');
    const ch = input.value.trim();
    if (!ch || ch.length !== 1) return;

    currentChar = ch;
    strokesDone = 0;

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
            strokeColor: '#5B3A29',
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
        writer.updateColor('strokeColor', '#5B3A29');   // 觸發設定更新（workaround）
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
