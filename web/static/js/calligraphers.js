/**
 * 書法家介紹頁邏輯 v2
 * - 動態副標題
 * - 時代軸導覽
 * - FFT 風格特徵迷你條形圖
 * - 豐富傳記 + 風格標籤
 * - 連結到 explorer 頁
 */

// 書法家顏色
const CAL_COLORS = {
    '智永':   '#E63946',
    '沈尹默': '#457B9D',
    '顏真卿': '#2A9D8F',
    '歐陽詢': '#F4A261',
    '趙孟頫': '#8B5A2B',
    '虞世南': '#6A4C93',
    '柳公權': '#3498DB'
};

// 書法家詳細傳記（擴充版）
const CAL_BIO = {
    '智永': {
        full_name: '智永禪師',
        birth_death: '生卒年不詳，約活躍於南朝陳至隋代',
        bio: '智永禪師，本姓王，名法極，是書聖王羲之七世孫。出家後居永欣寺，潛心書法三十餘年，書寫《千字文》八百餘本，分贈浙東各寺。相傳其退筆成塚，人稱「退筆塚」。',
        masterpiece: '《真草千字文》',
        influence: '傳承二王筆法，為唐代楷書繁榮奠定基礎',
        traits: ['筆勢圓潤', '結構端正', '氣韻平和', '師法二王']
    },
    '沈尹默': {
        full_name: '沈尹默',
        birth_death: '1883 – 1971',
        bio: '沈尹默，原名君默，浙江吳興人。近代著名書法家、詩人、教育家。曾任北京大學教授、中央文史研究館副館長。他主張「回歸二王」，以碑帖融合的理念，創出獨樹一幟的書風。',
        masterpiece: '《執筆五字法》理論著作',
        influence: '被譽為近代書壇泰斗，推動書法教育現代化',
        traits: ['筆力遒勁', '結構俊逸', '法度嚴謹', '碑帖融合']
    },
    '顏真卿': {
        full_name: '顏真卿',
        birth_death: '709 – 785',
        bio: '顏真卿，字清臣，京兆萬年人。唐代名臣與書法家，創「顏體」楷書。安史之亂中率義軍抗敵，後因勸諭叛將李希烈被害殉國，諡文忠。其書法雄渾磅礴，一改初唐瘦硬書風。',
        masterpiece: '《多寶塔碑》《顏勤禮碑》《祭姪文稿》',
        influence: '開創雄渾寬博書風，與柳公權並稱「顏筋柳骨」',
        traits: ['用筆豐腴', '氣勢磅礴', '結構寬博', '忠義之氣']
    },
    '歐陽詢': {
        full_name: '歐陽詢',
        birth_death: '557 – 641',
        bio: '歐陽詢，字信本，潭州臨湘人。唐代書法家，楷書四大家之首。其書法結構嚴謹，筆畫剛勁有力，世稱「歐體」。據傳他曾於道旁見古碑，駐馬觀之，去而復返，三日不能去。',
        masterpiece: '《九成宮醴泉銘》《化度寺碑》',
        influence: '確立楷書法度，被視為學楷書的最佳入門範本',
        traits: ['結構嚴謹', '筆畫勁健', '法度森嚴', '險勁峭拔']
    },
    '趙孟頫': {
        full_name: '趙孟頫',
        birth_death: '1254 – 1322',
        bio: '趙孟頫，字子昂，號松雪道人，湖州吳興人。宋太祖後裔，入元後出仕，官至翰林學士承旨。精通書畫，提倡「用筆千古不易」，力主復古，集晉唐書法大成，創「趙體」。',
        masterpiece: '《膽巴碑》《洛神賦》',
        influence: '集晉唐之大成，楷書四大家之一，影響明清書壇',
        traits: ['筆法圓轉', '結構嚴謹', '風格秀美', '復古創新']
    },
    '虞世南': {
        full_name: '虞世南',
        birth_death: '558 – 638',
        bio: '虞世南，字伯施，越州餘姚人。唐初書法家，位列唐太宗身邊「十八學士」之首。師承智永，得二王筆法精髓。唐太宗曾言世南有「五絕」：德行、忠直、博學、文詞、書翰。',
        masterpiece: '《孔子廟堂碑》《演連珠》',
        influence: '楷書四大家之一，書風秀潤，與歐陽詢並稱「歐虞」',
        traits: ['筆法秀潤', '外柔內剛', '典雅端莊', '師承二王']
    },
    '柳公權': {
        full_name: '柳公權',
        birth_death: '778 – 865',
        bio: '柳公權，字誠懸，京兆華原人。唐代著名書法家，歷事穆、敬、文、武、宣、懿六朝，官至太子少師。其書法初學王羲之，後廣泛學習顏真卿、歐陽詢諸家，以骨力遒勁、結構緊密著稱。傳唐穆宗問柳公權筆法，答曰：「心正則筆正」，流傳千古。',
        masterpiece: '《玄秘塔碑》《神策軍碑》',
        influence: '創「柳體」楷書，與顏真卿並稱「顏筋柳骨」，為後世楷書典範',
        traits: ['骨力勁健', '結構緊密', '筆畫挺拔', '心正筆正']
    }
};

// 朝代排序（用於時代軸）
const DYNASTY_ORDER = ['南北朝', '隋代', '唐代', '宋代', '元代', '明代', '清代', '近代'];

document.addEventListener('DOMContentLoaded', loadCalligraphers);

async function loadCalligraphers() {
    const grid = document.getElementById('calGrid');
    const subtitle = document.getElementById('pageSubtitle');

    try {
        const data = await api('/api/calligrapher/list');
        const cals = data.calligraphers;

        // ── 依 display_name 去重並合併統計（同一書法家多本字帖合為一張卡片）
        const calMap = new Map();
        cals.forEach(cal => {
            if (!calMap.has(cal.display_name)) {
                calMap.set(cal.display_name, {
                    ...cal,
                    bookIds:          [cal.id],
                    bookNames:        [cal.book || ''],
                    total_images:     cal.total_images     || 0,
                    unique_characters: cal.unique_characters || 0,
                });
            } else {
                const m = calMap.get(cal.display_name);
                m.bookIds.push(cal.id);
                m.bookNames.push(cal.book || '');
                m.total_images      += (cal.total_images || 0);
                m.unique_characters  = Math.max(m.unique_characters, cal.unique_characters || 0);
            }
        });
        const uniqueCals = Array.from(calMap.values());

        // 動態副標題（以不重複書法家數為準）
        if (subtitle) {
            const numMap = {1:'一',2:'二',3:'三',4:'四',5:'五',6:'六',7:'七',8:'八',9:'九',10:'十'};
            const count = numMap[uniqueCals.length] || uniqueCals.length;
            subtitle.textContent = `收錄${count}位不同時代的楷書大師，透過 FFT 分析探索他們的風格特色`;
        }

        // 建立時代軸（去重後）
        buildDynastyTimeline(uniqueCals);

        // 建立書法家卡片
        grid.innerHTML = '';
        for (const cal of uniqueCals) {
            const card = buildCalCard(cal);
            grid.appendChild(card);
            // 載入所有字帖的範例圖片
            loadSampleImagesMulti(cal.bookIds, cal.id);
        }

    } catch (err) {
        grid.innerHTML = `<div class="error-msg">載入失敗: ${escapeHtml(err.message)}</div>`;
    }
}

/**
 * 建立時代軸
 */
function buildDynastyTimeline(cals) {
    const container = document.getElementById('dynastyTimeline');
    if (!container) return;

    // 依朝代分組
    const dynastyMap = {};
    cals.forEach(cal => {
        const d = cal.dynasty;
        if (!dynastyMap[d]) dynastyMap[d] = [];
        dynastyMap[d].push(cal);
    });

    // 按歷史順序排序
    const sortedDynasties = Object.keys(dynastyMap).sort((a, b) => {
        const ia = DYNASTY_ORDER.indexOf(a);
        const ib = DYNASTY_ORDER.indexOf(b);
        return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    });

    let html = '<div class="timeline-track">';
    sortedDynasties.forEach((dynasty, idx) => {
        const calNames = dynastyMap[dynasty].map(c => c.display_name).join('、');
        const isLast = idx === sortedDynasties.length - 1;
        html += `
            <div class="timeline-node ${isLast ? 'last' : ''}">
                <div class="timeline-dot"></div>
                <div class="timeline-label">
                    <span class="timeline-dynasty">${escapeHtml(dynasty)}</span>
                    <span class="timeline-names">${escapeHtml(calNames)}</span>
                </div>
                ${!isLast ? '<div class="timeline-line"></div>' : ''}
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

/**
 * 建立書法家卡片
 */
function buildCalCard(cal) {
    const card = document.createElement('div');
    card.className = 'cal-card';
    card.id = `cal-${cal.id}`;

    const color = CAL_COLORS[cal.display_name] || '#8B5A2B';
    card.style.setProperty('--cal-accent', color);

    const bio = CAL_BIO[cal.display_name] || {};
    const traits = bio.traits || [];
    const sf = cal.style_features || null;

    // 風格標籤 HTML
    let traitsHtml = traits.map(t =>
        `<span class="cal-trait">${escapeHtml(t)}</span>`
    ).join('');

    // FFT 最強/最弱標籤
    if (sf) {
        traitsHtml += `<span class="cal-trait fft-high" title="FFT 最高特徵">▲ ${escapeHtml(sf.strongest.label)}</span>`;
        traitsHtml += `<span class="cal-trait fft-low" title="FFT 最低特徵">▼ ${escapeHtml(sf.weakest.label)}</span>`;
    }

    // FFT 風格指紋（迷你條形圖）
    let fftHtml = '';
    if (sf && sf.feature_labels && sf.feature_values) {
        fftHtml = `
            <div class="cal-fft-section">
                <div class="cal-fft-title">FFT 風格指紋</div>
                <div class="cal-fft-bars">
                    ${sf.feature_labels.map((label, i) => {
                        const val = sf.feature_values[i];
                        const pct = Math.round(val * 100);
                        return `
                            <div class="fft-bar-row">
                                <span class="fft-bar-label">${escapeHtml(label)}</span>
                                <div class="fft-bar-track">
                                    <div class="fft-bar-fill" style="width:${pct}%; background:${color}"></div>
                                </div>
                                <span class="fft-bar-val">${pct}%</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }

    // 傳記資訊
    const birthDeath = bio.birth_death ? `<span class="cal-life">${escapeHtml(bio.birth_death)}</span>` : '';
    const bioText = bio.bio || cal.description || '';
    const masterpiece = bio.masterpiece ? `<div class="cal-info-item"><span class="cal-info-label">代表作</span><span>${escapeHtml(bio.masterpiece)}</span></div>` : '';
    const influence = bio.influence ? `<div class="cal-info-item"><span class="cal-info-label">影響</span><span>${escapeHtml(bio.influence)}</span></div>` : '';

    // 字帖標籤（單本或多本）
    const bookNames = cal.bookNames || (cal.book ? [cal.book] : []);
    const booksLabel = bookNames.length > 1
        ? `${bookNames.join('、')}（共 ${bookNames.length} 本）`
        : (bookNames[0] || '');
    const booksHtml = booksLabel
        ? `<div class="cal-info-item"><span class="cal-info-label">字帖</span><span>${escapeHtml(booksLabel)}</span></div>`
        : '';

    card.innerHTML = `
        <div class="cal-card-header" style="background:${color}">
            <div class="cal-avatar">${cal.display_name.charAt(0)}</div>
            <div class="cal-header-info">
                <div class="cal-name">${escapeHtml(cal.display_name)}</div>
                ${birthDeath}
                <div class="cal-badges">
                    <span class="badge badge-dynasty">${escapeHtml(cal.dynasty)}</span>
                    <span class="badge badge-style">${escapeHtml(cal.style)}</span>
                </div>
            </div>
        </div>
        <div class="cal-card-body">
            <div class="cal-traits">${traitsHtml}</div>
            <p class="cal-description">${escapeHtml(bioText)}</p>
            <div class="cal-info-grid">
                ${booksHtml}
                ${masterpiece}
                ${influence}
            </div>
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
            ${fftHtml}
            <div class="cal-samples-title">範例字帖</div>
            <div class="cal-samples" id="samples-${cal.id}">
                <span style="color:var(--text-muted);font-size:0.85rem">載入中...</span>
            </div>
            <div class="cal-actions">
                <a href="/explorer?calligrapher=${encodeURIComponent(cal.display_name)}" class="cal-action-btn">
                    探索此書法家的字 →
                </a>
            </div>
        </div>
    `;

    return card;
}

/**
 * 載入多本字帖的範例圖片（合併顯示到同一個容器）
 * @param {string[]} bookIds   - 字帖 id 列表（可能只有一個）
 * @param {string}   primaryId - 卡片主 id（對應 container id samples-primaryId）
 */
async function loadSampleImagesMulti(bookIds, primaryId) {
    const container = document.getElementById(`samples-${primaryId}`);
    if (!container) return;

    container.innerHTML = '';
    const perBook = Math.max(2, Math.ceil(8 / bookIds.length));

    for (const id of bookIds) {
        try {
            const data = await api(`/api/calligrapher/${id}`);
            const samples = (data.sample_images || []).slice(0, perBook);
            const bookLabel = data.book ? `《${data.book}》` : '書法範例';
            samples.forEach(url => {
                const img = document.createElement('img');
                img.src       = url;
                img.className = 'cal-sample-img';
                img.alt       = bookLabel;
                img.loading   = 'lazy';
                img.title     = bookLabel;
                img.onclick   = () => openImageModal(url, bookLabel);
                img.onerror   = () => img.style.display = 'none';
                container.appendChild(img);
            });
        } catch (_) { /* 靜默 */ }
    }

    if (!container.hasChildNodes()) {
        container.innerHTML = '<span style="color:var(--text-muted);font-size:0.85rem">暫無範例</span>';
    }
}
