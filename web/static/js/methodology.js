/**
 * 分析方法論頁：資料樣本表、ANOVA 統計檢定表、7 維特徵解讀
 */

const FEATURE_ICONS = {
    low_freq: '低頻', mid_freq: '中頻', high_freq: '高頻', centroid: '重心',
    dc_ratio: '比例', slope: '斜度', hf_decay: '衰減',
};

function effectSizeTier(eta2) {
    if (eta2 >= 0.14) return { tier: 'large', text: '大' };
    if (eta2 >= 0.06) return { tier: 'medium', text: '中' };
    if (eta2 >= 0.01) return { tier: 'small', text: '小' };
    return { tier: 'negligible', text: '微乎其微' };
}

document.addEventListener('DOMContentLoaded', async () => {
    const [radar, features] = await Promise.all([
        api('/api/analysis/radar-data').catch(() => null),
        api('/api/analysis/features').catch(() => null),
    ]);

    if (radar && radar.available) {
        renderSampleTable(radar);
        renderStatsTable(radar);
        const countEl = document.getElementById('commonCharCount');
        if (countEl && radar.common_char_count) countEl.textContent = radar.common_char_count;
    } else {
        document.getElementById('sampleSizeTable').innerHTML = '<div class="info-msg">資料尚未生成</div>';
        document.getElementById('statsTable').innerHTML = '<div class="info-msg">資料尚未生成</div>';
    }

    if (features) {
        renderFeatureAccordion(features);
    }
});

function renderSampleTable(radar) {
    const el = document.getElementById('sampleSizeTable');
    if (!el) return;
    const sizes = radar.sample_sizes || {};
    const cals = radar.calligraphers || [];

    const rows = cals.map(cal => `
        <tr>
            <td>${escapeHtml(cal)}</td>
            <td>${sizes[cal] !== undefined ? sizes[cal] : '—'}</td>
        </tr>
    `).join('');

    el.innerHTML = `
        <table class="mini-table">
            <thead><tr><th>書法家</th><th>樣本數（共同字圖片張數）</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

function renderStatsTable(radar) {
    const el = document.getElementById('statsTable');
    if (!el) return;
    const labels = radar.labels || [];
    const pVals = radar.anova_p || [];
    const etas = radar.eta_squared || [];

    const rows = labels
        .map((label, idx) => ({ label, p: pVals[idx], eta: etas[idx] }))
        .sort((a, b) => b.eta - a.eta)
        .map(f => {
            const tier = effectSizeTier(f.eta);
            const pText = f.p < 0.001 ? 'p < 0.001' : `p = ${f.p.toFixed(3)}`;
            return `
                <tr>
                    <td>${escapeHtml(f.label)}</td>
                    <td>${pText}</td>
                    <td>${f.eta.toFixed(4)}</td>
                    <td><span class="signal-tag ${tier.tier}">${tier.text}</span></td>
                </tr>
            `;
        }).join('');

    el.innerHTML = `
        <table class="mini-table">
            <thead><tr><th>特徵</th><th>ANOVA p 值</th><th>效果量 η²</th><th>等級</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

function renderFeatureAccordion(featuresData) {
    const container = document.getElementById('featureAccordion');
    if (!container) return;

    const features = featuresData.features || {};
    const order = featuresData.feature_order || Object.keys(features);

    container.innerHTML = '';

    order.forEach((key, index) => {
        const feat = features[key];
        if (!feat) return;

        const icon = FEATURE_ICONS[key] || '—';
        const isOpen = index === 0;

        const item = document.createElement('div');
        item.className = `accordion-item ${isOpen ? 'open' : ''}`;
        item.innerHTML = `
            <div class="accordion-header">
                <div class="feature-title">
                    <div class="feature-icon">${icon}</div>
                    <div>
                        <div class="feature-name">${escapeHtml(feat.name)}</div>
                        <div class="feature-name-en">${escapeHtml(feat.name_en)}</div>
                    </div>
                </div>
                <span class="expand-icon">▼</span>
            </div>
            <div class="accordion-content">
                <div class="feature-description">${escapeHtml(feat.description)}</div>
                <div class="feature-meanings">
                    <div class="meaning-box high">
                        <div class="meaning-label">▲ 高值代表</div>
                        <div>${escapeHtml(feat.high_meaning)}</div>
                    </div>
                    <div class="meaning-box low">
                        <div class="meaning-label">▼ 低值代表</div>
                        <div>${escapeHtml(feat.low_meaning)}</div>
                    </div>
                    <div class="meaning-box cal">
                        <div class="meaning-label">★ 本次分析結果</div>
                        <div>${escapeHtml(feat.calligraphy_meaning)}</div>
                    </div>
                </div>
            </div>
        `;

        const header = item.querySelector('.accordion-header');
        header.addEventListener('click', () => item.classList.toggle('open'));

        container.appendChild(item);
    });
}
