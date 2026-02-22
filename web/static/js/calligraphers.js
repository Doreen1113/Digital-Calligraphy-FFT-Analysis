/**
 * 書法家介紹頁邏輯
 */

document.addEventListener('DOMContentLoaded', loadCalligraphers);

async function loadCalligraphers() {
    const grid = document.getElementById('calGrid');

    try {
        const data = await api('/api/calligrapher/list');
        const cals = data.calligraphers;

        grid.innerHTML = '';

        for (const cal of cals) {
            const card = document.createElement('div');
            card.className = 'cal-card';

            card.innerHTML = `
                <div class="cal-card-header">
                    <div class="cal-name">${escapeHtml(cal.display_name)}</div>
                    <div class="cal-badges">
                        <span class="badge badge-dynasty">${escapeHtml(cal.dynasty)}</span>
                        <span class="badge badge-style">${escapeHtml(cal.style)}</span>
                    </div>
                </div>
                <div class="cal-card-body">
                    <p class="cal-description">${escapeHtml(cal.description)}</p>
                    <div class="cal-stats">
                        <div class="cal-stat">
                            <div class="cal-stat-num">${cal.total_images || cal.total_chars || '-'}</div>
                            <div class="cal-stat-label">圖片數</div>
                        </div>
                        <div class="cal-stat">
                            <div class="cal-stat-num">${cal.unique_characters || '-'}</div>
                            <div class="cal-stat-label">字元數</div>
                        </div>
                    </div>
                    <div class="cal-samples-title">範例字帖</div>
                    <div class="cal-samples" id="samples-${cal.id}">
                        <span style="color:var(--text-muted);font-size:0.85rem">載入中...</span>
                    </div>
                </div>
            `;

            grid.appendChild(card);

            // 非同步載入範例圖片
            loadSampleImages(cal.id);
        }

    } catch (err) {
        grid.innerHTML = `<div class="error-msg">載入失敗: ${escapeHtml(err.message)}</div>`;
    }
}

async function loadSampleImages(calId) {
    const container = document.getElementById(`samples-${calId}`);
    try {
        const data = await api(`/api/calligrapher/${calId}`);
        const samples = data.sample_images || [];

        if (samples.length === 0) {
            container.innerHTML = '<span style="color:var(--text-muted);font-size:0.85rem">暫無範例</span>';
            return;
        }

        container.innerHTML = samples.slice(0, 6).map(url =>
            `<img src="${url}"
                  class="cal-sample-img"
                  alt="範例字帖"
                  loading="lazy"
                  onclick="openImageModal('${url.replace(/'/g, "\\'")}', '書法範例')"
                  onerror="this.style.display='none'">`
        ).join('');
    } catch (err) {
        container.innerHTML = '';
    }
}
