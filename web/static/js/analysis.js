/**
 * 風格分析頁邏輯
 */

document.addEventListener('DOMContentLoaded', () => {
    loadAnalysisImages();
    loadFeatureDescriptions();
});


/**
 * 載入分析圖片
 */
async function loadAnalysisImages() {
    const radarContainer = document.getElementById('radarContainer');
    const similarityContainer = document.getElementById('similarityContainer');
    const barsContainer = document.getElementById('barsContainer');
    const statusDiv = document.getElementById('analysisStatus');

    try {
        const data = await api('/api/analysis/images');

        if (!data.generated) {
            statusDiv.innerHTML = `
                <div class="info-msg">
                    部分分析圖片尚未生成。請先在命令列執行 FFT 風格分析：<br>
                    <code>python main.py</code> -> 選項 2（FFT 風格分析）
                </div>
            `;
        }

        // 雷達圖
        if (data.radar_image) {
            radarContainer.innerHTML = `
                <img src="${data.radar_image}"
                     alt="風格雷達圖"
                     style="cursor: pointer;"
                     onclick="openImageModal('${data.radar_image.replace(/'/g, "\\'")}', '書法風格雷達圖')">
            `;
        } else {
            radarContainer.innerHTML = '<div class="not-generated"><p>雷達圖尚未生成</p></div>';
        }

        // 相似度矩陣
        if (data.similarity_image) {
            similarityContainer.innerHTML = `
                <img src="${data.similarity_image}"
                     alt="相似度矩陣"
                     style="cursor: pointer;"
                     onclick="openImageModal('${data.similarity_image.replace(/'/g, "\\'")}', '書法家相似度矩陣')">
            `;
        } else {
            similarityContainer.innerHTML = '<div class="not-generated"><p>相似度矩陣尚未生成</p></div>';
        }

        // 特徵長條圖
        if (data.bars_image) {
            barsContainer.innerHTML = `
                <img src="${data.bars_image}"
                     alt="特徵對比"
                     style="cursor: pointer;"
                     onclick="openImageModal('${data.bars_image.replace(/'/g, "\\'")}', '特徵對比圖')">
            `;
        } else {
            barsContainer.innerHTML = '<div class="not-generated"><p>特徵對比圖尚未生成</p></div>';
        }

    } catch (err) {
        statusDiv.innerHTML = `<div class="error-msg">載入分析圖片失敗: ${escapeHtml(err.message)}</div>`;
    }
}


/**
 * 載入特徵說明卡片
 */
async function loadFeatureDescriptions() {
    const grid = document.getElementById('featureGrid');

    try {
        const data = await api('/api/analysis/features');
        const features = data.features || {};
        const order = data.feature_order || Object.keys(features);

        grid.innerHTML = '';

        for (const key of order) {
            const feat = features[key];
            if (!feat) continue;

            const card = document.createElement('div');
            card.className = 'feature-card';
            card.innerHTML = `
                <div class="feature-name">${escapeHtml(feat.name)}</div>
                <div class="feature-name-en">${escapeHtml(feat.name_en)}</div>
                <div class="feature-desc">${escapeHtml(feat.description)}</div>
                <div class="feature-meaning">
                    <span class="high">&#9650; 高值：</span> ${escapeHtml(feat.high_meaning)}<br>
                    <span class="low">&#9660; 低值：</span> ${escapeHtml(feat.low_meaning)}<br>
                    <span class="cal">&#9733; 書法：</span> ${escapeHtml(feat.calligraphy_meaning)}
                </div>
            `;
            grid.appendChild(card);
        }

    } catch (err) {
        grid.innerHTML = `<div class="error-msg">載入特徵說明失敗</div>`;
    }
}
