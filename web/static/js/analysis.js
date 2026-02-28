/**
 * 風格分析頁 v3 - 互動式解釋面板
 * 使用真實 FFT 分析數據（來自 style_features.json）
 */

// 書法家顏色設定
const CALLIGRAPHER_COLORS = {
    '智永': { color: '#E63946', light: '#FFE9EA' },
    '沈尹默': { color: '#457B9D', light: '#E8F1F5' },
    '顏真卿': { color: '#2A9D8F', light: '#E6F5F3' },
    '歐陽詢': { color: '#F4A261', light: '#FFF4E8' },
    '褚遂良': { color: '#9B59B6', light: '#F5EEF8' },
    '柳公權': { color: '#3498DB', light: '#EBF5FB' },
    '趙孟頫': { color: '#8B5A2B', light: '#FFF8E1' }
};

// 特徵圖示（對應 7 個易懂標籤）
const FEATURE_ICONS = {
    low_freq: '🏛️',
    mid_freq: '✒️',
    high_freq: '🔍',
    centroid: '⚖️',
    dc_ratio: '🔗',
    slope: '🎨',
    hf_decay: '✨'
};

// 全域狀態
let radarChart = null;
let analysisData = {
    radarData: null,
    similarityData: null,
    featuresData: null,
    selectedCalligraphers: [],
    allCalligraphers: [],
    calligrapherFeatures: {}
};

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', async () => {
    await loadAllAnalysisData();
    initCalligrapherSelector();
    updateSelectedCount();
    initRadarChart();
    initSimilarityGrid();
    initFeatureAccordion();
    initStyleOverview();
});

// ========== 資料載入 ==========
async function loadAllAnalysisData() {
    const statusDiv = document.getElementById('analysisStatus');

    try {
        const [radarRes, simRes, featRes] = await Promise.all([
            api('/api/analysis/radar-data').catch(e => null),
            api('/api/analysis/similarity').catch(e => null),
            api('/api/analysis/features').catch(e => null)
        ]);

        analysisData.radarData = radarRes;
        analysisData.similarityData = simRes;
        analysisData.featuresData = featRes;

        // 提取書法家列表
        if (radarRes && radarRes.available && radarRes.calligraphers) {
            analysisData.allCalligraphers = radarRes.calligraphers;
            analysisData.selectedCalligraphers = [...radarRes.calligraphers];
        } else if (simRes && simRes.available && simRes.calligraphers) {
            analysisData.allCalligraphers = simRes.calligraphers;
            analysisData.selectedCalligraphers = [...simRes.calligraphers];
        }

        // 提取特徵資料
        if (radarRes && radarRes.data) {
            analysisData.calligrapherFeatures = radarRes.data;
        }

        // 檢查是否有資料
        if ((!radarRes || !radarRes.available) && (!simRes || !simRes.available)) {
            statusDiv.innerHTML = `
                <div class="info-msg">
                    分析資料尚未生成。請先執行 FFT 風格分析：<br>
                    <code>python analyze_styles.py 30</code>
                </div>
            `;
        }

    } catch (err) {
        statusDiv.innerHTML = `<div class="error-msg">載入分析資料失敗: ${escapeHtml(err.message)}</div>`;
    }
}

// ========== 書法家選擇器 ==========
function initCalligrapherSelector() {
    const toggleGroup = document.getElementById('calToggles');
    if (!toggleGroup) return;

    toggleGroup.innerHTML = '';

    if (analysisData.allCalligraphers.length === 0) {
        toggleGroup.innerHTML = '<div class="info-msg">無書法家資料</div>';
        return;
    }

    analysisData.allCalligraphers.forEach(cal => {
        const colors = CALLIGRAPHER_COLORS[cal] || { color: '#8B5A2B', light: '#FFF8E1' };

        const toggle = document.createElement('label');
        toggle.className = 'cal-toggle active';
        toggle.style.setProperty('--cal-color', colors.color);
        toggle.style.setProperty('--cal-color-light', colors.light);
        toggle.innerHTML = `
            <span class="cal-dot"></span>
            <span class="cal-name">${escapeHtml(cal)}</span>
        `;
        toggle.dataset.calligrapher = cal;

        toggle.addEventListener('click', () => {
            toggle.classList.toggle('active');
            updateSelectedCalligraphers();
        });

        toggleGroup.appendChild(toggle);
    });
}

function updateSelectedCalligraphers() {
    const toggles = document.querySelectorAll('.cal-toggle.active');
    analysisData.selectedCalligraphers = Array.from(toggles).map(t => t.dataset.calligrapher);
    updateSelectedCount();
    updateRadarChart();
}

// ========== 互動式雷達圖 ==========
function initRadarChart() {
    const container = document.getElementById('radarContainer');
    if (!container) return;

    if (typeof Chart === 'undefined') {
        loadStaticRadarImage(container);
        return;
    }

    if (!analysisData.radarData || !analysisData.radarData.available || !analysisData.radarData.labels) {
        loadStaticRadarImage(container);
        return;
    }

    const canvas = container.querySelector('canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const labels = analysisData.radarData.labels || [];

    const datasets = createRadarDatasets();

    radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 1,
                    ticks: {
                        stepSize: 0.2,
                        font: { size: 10 },
                        callback: (val) => {
                            if (val === 0 || val === 0.5 || val === 1) return val;
                            return '';
                        }
                    },
                    pointLabels: {
                        font: { size: 13, weight: 'bold' },
                        color: '#5B3A29'
                    },
                    grid: {
                        color: 'rgba(0,0,0,0.08)'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 18,
                        usePointStyle: true,
                        font: { size: 13, weight: 'bold' }
                    }
                },
                tooltip: {
                    callbacks: {
                        title: (items) => items[0]?.label || '',
                        label: (context) => {
                            const val = context.raw;
                            const pct = (val * 100).toFixed(0);
                            const bar = '\u2588'.repeat(Math.round(val * 10)) + '\u2591'.repeat(10 - Math.round(val * 10));
                            return `${context.dataset.label}: ${pct}% ${bar}`;
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'point'
            }
        }
    });
}

function createRadarDatasets() {
    const datasets = [];
    const data = analysisData.calligrapherFeatures;

    analysisData.selectedCalligraphers.forEach((cal) => {
        if (!data[cal]) return;

        const colors = CALLIGRAPHER_COLORS[cal] || { color: '#8B5A2B' };
        const values = data[cal];

        datasets.push({
            label: cal,
            data: Array.isArray(values) ? values : Object.values(values),
            borderColor: colors.color,
            backgroundColor: hexToRgba(colors.color, 0.12),
            borderWidth: 2.5,
            pointRadius: 5,
            pointBackgroundColor: colors.color,
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointHoverRadius: 8
        });
    });

    return datasets;
}

function updateRadarChart() {
    if (!radarChart) return;
    radarChart.data.datasets = createRadarDatasets();
    radarChart.update();
}

async function loadStaticRadarImage(container) {
    try {
        const data = await api('/api/analysis/images');
        if (data.radar_image) {
            container.innerHTML = `
                <div class="radar-image-container">
                    <img src="${data.radar_image}" alt="風格雷達圖"
                         onclick="openImageModal('${data.radar_image.replace(/'/g, "\\'")}', '書法風格雷達圖')">
                </div>
            `;
        } else {
            container.innerHTML = '<div class="not-generated"><p>雷達圖尚未生成</p></div>';
        }
    } catch (err) {
        container.innerHTML = '<div class="error-msg">載入雷達圖失敗</div>';
    }
}

// ========== 互動式相似度矩陣 ==========
function initSimilarityGrid() {
    const gridContainer = document.getElementById('similarityGrid');
    if (!gridContainer) return;

    const simData = analysisData.similarityData;

    if (!simData || !simData.available || !simData.matrix || !simData.calligraphers) {
        loadStaticSimilarityImage(gridContainer);
        return;
    }

    const calligraphers = simData.calligraphers;
    const matrix = simData.matrix;
    const n = calligraphers.length;

    gridContainer.style.gridTemplateColumns = `repeat(${n + 1}, 1fr)`;
    gridContainer.innerHTML = '';

    // 角落空格
    const corner = document.createElement('div');
    corner.className = 'sim-cell header corner';
    gridContainer.appendChild(corner);

    // 標題列
    calligraphers.forEach(cal => {
        const headerCell = document.createElement('div');
        headerCell.className = 'sim-cell header';
        headerCell.textContent = cal;
        gridContainer.appendChild(headerCell);
    });

    // 資料列
    calligraphers.forEach((rowCal, i) => {
        const rowHeader = document.createElement('div');
        rowHeader.className = 'sim-cell header';
        rowHeader.textContent = rowCal;
        gridContainer.appendChild(rowHeader);

        calligraphers.forEach((colCal, j) => {
            const cell = document.createElement('div');
            cell.className = 'sim-cell';

            const sim = matrix[i][j];
            const pct = (sim * 100).toFixed(0);
            cell.textContent = `${pct}%`;
            cell.dataset.sim = sim;

            // 設定顏色
            cell.style.backgroundColor = getSimColor(sim);
            cell.style.color = sim >= 0.5 ? '#fff' : '#333';
            cell.style.fontWeight = '600';

            if (i !== j) {
                cell.addEventListener('click', () => {
                    showSimilarityDetail(rowCal, colCal, sim, i, j);
                    highlightCell(cell);
                });
            } else {
                cell.style.cursor = 'default';
                cell.style.opacity = '0.5';
            }

            gridContainer.appendChild(cell);
        });
    });
}

function getSimColor(sim) {
    if (sim >= 0.8) return '#1B5E20';
    if (sim >= 0.6) return '#4CAF50';
    if (sim >= 0.4) return '#FFB300';
    if (sim >= 0.2) return '#E65100';
    return '#B71C1C';
}

function highlightCell(cell) {
    document.querySelectorAll('.sim-cell.selected').forEach(c => c.classList.remove('selected'));
    cell.classList.add('selected');
}

function showSimilarityDetail(cal1, cal2, similarity, i, j) {
    const container = document.getElementById('similarityDetail');
    if (!container) return;

    const pct = (similarity * 100).toFixed(1);
    let simClass, simText;
    if (similarity >= 0.7) { simClass = 'high'; simText = '風格接近'; }
    else if (similarity >= 0.4) { simClass = 'medium'; simText = '有共同特點'; }
    else { simClass = 'low'; simText = '風格迥異'; }

    const features1 = analysisData.calligrapherFeatures[cal1];
    const features2 = analysisData.calligrapherFeatures[cal2];
    const labels = analysisData.radarData?.labels || [];

    let comparisonHtml = '';
    if (features1 && features2 && labels.length > 0) {
        const vals1 = Array.isArray(features1) ? features1 : Object.values(features1);
        const vals2 = Array.isArray(features2) ? features2 : Object.values(features2);

        comparisonHtml = '<div class="detail-comparison">';
        labels.forEach((label, idx) => {
            const v1 = vals1[idx] || 0;
            const v2 = vals2[idx] || 0;
            const diff = Math.abs(v1 - v2);
            let diffIcon;
            if (diff < 0.15) diffIcon = '≈';
            else if (diff < 0.4) diffIcon = '~';
            else diffIcon = '≠';

            comparisonHtml += `
                <div class="comparison-item">
                    <span class="comparison-feature">${escapeHtml(label)}</span>
                    <span class="comparison-values">
                        <span class="cmp-bar" style="width:${Math.round(v1*100)}%; background:${CALLIGRAPHER_COLORS[cal1]?.color || '#888'}"></span>
                        <span class="cmp-bar" style="width:${Math.round(v2*100)}%; background:${CALLIGRAPHER_COLORS[cal2]?.color || '#888'}"></span>
                    </span>
                    <span class="comparison-diff">${diffIcon}</span>
                </div>
            `;
        });
        comparisonHtml += '</div>';
    }

    container.innerHTML = `
        <div class="detail-header">
            <div class="detail-title">${escapeHtml(cal1)} vs ${escapeHtml(cal2)}</div>
            <div class="detail-similarity ${simClass}">${pct}%</div>
            <div class="detail-label">${simText}</div>
        </div>
        ${comparisonHtml}
        <div class="detail-legend">
            <span style="color:${CALLIGRAPHER_COLORS[cal1]?.color || '#888'}">■ ${escapeHtml(cal1)}</span>
            <span style="color:${CALLIGRAPHER_COLORS[cal2]?.color || '#888'}">■ ${escapeHtml(cal2)}</span>
        </div>
    `;
}

async function loadStaticSimilarityImage(container) {
    try {
        const data = await api('/api/analysis/images');
        if (data.similarity_image) {
            container.parentElement.innerHTML = `
                <div class="similarity-image-container">
                    <img src="${data.similarity_image}" alt="相似度矩陣"
                         onclick="openImageModal('${data.similarity_image.replace(/'/g, "\\'")}', '書法家相似度矩陣')">
                </div>
            `;
        } else {
            container.innerHTML = '<div class="not-generated"><p>相似度矩陣尚未生成</p></div>';
        }
    } catch (err) {
        container.innerHTML = '<div class="error-msg">載入相似度矩陣失敗</div>';
    }
}

// ========== 特徵手風琴 ==========
function initFeatureAccordion() {
    const container = document.getElementById('featureAccordion');
    if (!container || !analysisData.featuresData) return;

    const features = analysisData.featuresData.features || {};
    const order = analysisData.featuresData.feature_order || Object.keys(features);

    container.innerHTML = '';

    order.forEach((key, index) => {
        const feat = features[key];
        if (!feat) return;

        const icon = FEATURE_ICONS[key] || '📋';
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
                        <div class="meaning-label">★ 書法家舉例</div>
                        <div>${escapeHtml(feat.calligraphy_meaning)}</div>
                    </div>
                </div>
            </div>
        `;

        const header = item.querySelector('.accordion-header');
        header.addEventListener('click', () => {
            item.classList.toggle('open');
        });

        container.appendChild(item);
    });
}

// ========== 書法家風格總覽 ==========
function initStyleOverview() {
    const container = document.getElementById('styleOverview');
    if (!container) return;

    container.innerHTML = '';

    const styleDescriptions = {
        '智永': {
            dynasty: '隋代',
            traits: ['筆勢圓潤', '結構端正', '氣韻平和'],
            summary: '智永書法繼承王羲之筆法，風格溫潤典雅，結構嚴謹工整，是楷書學習的典範。'
        },
        '沈尹默': {
            dynasty: '近代',
            traits: ['筆力遒勁', '結構俊逸', '法度嚴謹'],
            summary: '沈尹默被譽為近代書壇泰斗，其書法融合碑帖，形成獨特的「沈體」風格。'
        },
        '顏真卿': {
            dynasty: '唐代',
            traits: ['用筆豐腴', '氣勢磅礴', '結構寬博'],
            summary: '顏真卿創「顏體」，特點是筆畫豐厚，結構寬博，氣象雄偉，影響後世深遠。'
        },
        '歐陽詢': {
            dynasty: '唐代',
            traits: ['結構嚴謹', '筆畫勁健', '法度森嚴'],
            summary: '歐陽詢創「歐體」，以結構嚴謹、筆畫剛勁著稱，是楷書四大家之首。'
        },
        '褚遂良': {
            dynasty: '唐代',
            traits: ['筆勢婉轉', '結構秀麗', '風格清雅'],
            summary: '褚遂良書法婉媚清麗，筆勢流暢，被譽為「美人嬋娟」。'
        },
        '柳公權': {
            dynasty: '唐代',
            traits: ['骨力勁健', '結構緊密', '筆畫挺拔'],
            summary: '柳公權創「柳體」，以骨力著稱，結構緊密，與顏體並稱「顏筋柳骨」。'
        },
        '趙孟頫': {
            dynasty: '元代',
            traits: ['筆法圓轉', '結構嚴謹', '風格秀美'],
            summary: '趙孟頫創「趙體」，集晉唐書法大成，筆法圓潤流暢，是楷書四大家之一。'
        }
    };

    analysisData.allCalligraphers.forEach(cal => {
        const colors = CALLIGRAPHER_COLORS[cal] || { color: '#8B5A2B' };
        const desc = styleDescriptions[cal] || { dynasty: '', traits: [], summary: '' };
        const features = analysisData.calligrapherFeatures[cal];

        let traitsHtml = desc.traits.map(t => `<span class="style-trait">${escapeHtml(t)}</span>`).join('');

        if (features && analysisData.radarData?.labels) {
            const vals = Array.isArray(features) ? features : Object.values(features);
            const labels = analysisData.radarData.labels;

            let maxIdx = 0, minIdx = 0;
            vals.forEach((v, i) => {
                if (v > vals[maxIdx]) maxIdx = i;
                if (v < vals[minIdx]) minIdx = i;
            });

            traitsHtml += `<span class="style-trait high">${escapeHtml(labels[maxIdx])} ↑</span>`;
            traitsHtml += `<span class="style-trait low">${escapeHtml(labels[minIdx])} ↓</span>`;
        }

        const card = document.createElement('div');
        card.className = 'style-card';
        card.style.setProperty('--cal-color', colors.color);
        card.innerHTML = `
            <div class="style-card-header">
                <div class="style-card-avatar">${cal.charAt(0)}</div>
                <div>
                    <div class="style-card-name">${escapeHtml(cal)}</div>
                    <div class="style-card-dynasty">${escapeHtml(desc.dynasty)}</div>
                </div>
            </div>
            <div class="style-traits">${traitsHtml}</div>
            <div class="style-summary">${escapeHtml(desc.summary)}</div>
        `;

        container.appendChild(card);
    });
}

// ========== 工具函式 ==========
function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// ========== 檢視切換 ==========
let radarViewMode = 'chart';
let similarityViewMode = 'grid';

function toggleRadarView() {
    const chartContainer = document.getElementById('radarContainer');
    const imageContainer = document.getElementById('radarImageContainer');
    const toggleBtn = document.getElementById('radarViewToggle');

    if (radarViewMode === 'chart') {
        radarViewMode = 'image';
        chartContainer.style.display = 'none';
        imageContainer.style.display = 'block';
        toggleBtn.textContent = '切換為圖表';
        loadStaticRadarImage(imageContainer);
    } else {
        radarViewMode = 'chart';
        chartContainer.style.display = 'flex';
        imageContainer.style.display = 'none';
        toggleBtn.textContent = '切換為圖片';
    }
}

function toggleSimilarityView() {
    const gridContainer = document.getElementById('similarityPanel');
    const imageContainer = document.getElementById('similarityImageContainer');
    const toggleBtn = document.getElementById('simViewToggle');

    if (similarityViewMode === 'grid') {
        similarityViewMode = 'image';
        gridContainer.style.display = 'none';
        imageContainer.style.display = 'block';
        toggleBtn.textContent = '切換為矩陣';
        loadStaticSimilarityImageOnly(imageContainer);
    } else {
        similarityViewMode = 'grid';
        gridContainer.style.display = 'grid';
        imageContainer.style.display = 'none';
        toggleBtn.textContent = '切換為圖片';
    }
}

async function loadStaticSimilarityImageOnly(container) {
    try {
        const data = await api('/api/analysis/images');
        if (data.similarity_image) {
            container.innerHTML = `
                <img src="${data.similarity_image}" alt="相似度矩陣"
                     style="max-width:100%; cursor:pointer;"
                     onclick="openImageModal('${data.similarity_image.replace(/'/g, "\\'")}', '書法家相似度矩陣')">
            `;
        } else {
            container.innerHTML = '<div class="not-generated"><p>相似度矩陣尚未生成</p></div>';
        }
    } catch (err) {
        container.innerHTML = '<div class="error-msg">載入相似度矩陣失敗</div>';
    }
}

function updateSelectedCount() {
    const badge = document.getElementById('selectedCount');
    if (badge) {
        badge.textContent = `${analysisData.selectedCalligraphers.length}/${analysisData.allCalligraphers.length}`;
    }
}
