/**
 * 批次比對頁邏輯
 */

document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('batchInput');
    input.addEventListener('input', () => {
        document.getElementById('charCount').textContent = input.value.length;
    });
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') doBatchCompare();
    });
});


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

    // 顯示結果區與進度
    resultSection.style.display = 'block';
    progressDiv.style.display = 'flex';
    resultsDiv.innerHTML = '';
    progressFill.style.width = '0%';
    progressText.textContent = '準備中...';

    try {
        const data = await apiPost('/api/character/batch', {
            characters: chars,
            calligraphers: selected.length < 4 ? selected : null,
        });

        const results = data.results || [];
        countBadge.textContent = `${data.success_count} / ${data.total}`;

        resultsDiv.innerHTML = '';
        results.forEach((r, idx) => {
            const item = document.createElement('div');
            item.className = 'batch-result-item';

            if (r.image_url) {
                const imgUrl = r.image_url + '?t=' + Date.now();
                item.innerHTML = `
                    <div class="result-char-label">字元：${escapeHtml(r.character)}</div>
                    <img src="${imgUrl}"
                         alt="比對: ${r.character}"
                         loading="lazy"
                         style="cursor: pointer;"
                         onclick="openImageModal('${imgUrl.replace(/'/g, "\\'")}', '字元「${r.character}」的比對結果')">
                `;
            } else {
                item.innerHTML = `
                    <div class="result-char-label">字元：${escapeHtml(r.character)}</div>
                    <div class="result-error">${escapeHtml(r.error || '比對失敗')}</div>
                `;
            }

            resultsDiv.appendChild(item);

            // 更新進度
            const pct = Math.round(((idx + 1) / results.length) * 100);
            progressFill.style.width = pct + '%';
            progressText.textContent = `${idx + 1} / ${results.length}`;
        });

        progressText.textContent = `完成！成功 ${data.success_count} / ${data.total}`;

    } catch (err) {
        showError(resultsDiv, err.message);
        progressDiv.style.display = 'none';
    }
}
