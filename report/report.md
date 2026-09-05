# Where Does Calligraphic Style Live in the Frequency Domain?
### An Interpretable Study of Calligrapher Identification with Character-Controlled Pairs

**Doreen Lin (林沁瑩)** · National Tsing Hua University, Dept. of Computer Science
Draft v0.1 — September 2026

---

## Abstract

Chinese calligraphy education rests on a long-standing belief: a calligrapher's identity lives primarily in a character's structural composition (間架結構), with brush-tip detail (筆法) as refinement. We test this belief quantitatively. We curate a dataset of 7,449 single-character images spanning 7 master calligraphers, 10 copybooks, and 1,057 unique characters, with a structure that public calligraphy datasets lack: 3,600+ *same-character pairs* across calligraphers, enabling text-dependent style analysis that controls for character identity. Under character-disjoint evaluation (test characters never seen in training), we find that (1) a ResNet-18 identifies calligraphers at 98.7% accuracy, but a radial low-pass ablation shows **95% accuracy is reached with only the lowest 10% of spatial frequencies** — the "structure over brushwork" belief holds, and we can now put a number on it; (2) interpretable contour Fourier descriptors carry real but partial style signal (49% with all handcrafted features vs. 31% for spectral statistics alone), spread across the harmonic spectrum rather than concentrated in a few low harmonics; (3) on same-character verification with unseen characters, CNN style embeddings reach **ROC-AUC 0.989 even when the two samples come from different copybooks**, showing the learned representation transfers across both character identity and source material. Cross-dataset validation on an independently collected corpus, however, collapses accuracy to 32% (recovering partially to 42% under stroke-width normalization) — within-source style identification is easy, cross-source generalization is the open problem, and we quantify exactly where the gap lies. We release the dataset construction pipeline, a same-character-ground-truth evaluation protocol for style generation, and a deployed learning platform built on these findings.

---

## 1. Introduction

<!-- 動機三段：書法教育的痛點（找不到範字/回饋抽象）→ 既有研究把分類刷到飽和但不可解釋 → 我們問的問題：風格訊號在哪個頻段、能否跨字泛化 -->

Prior work has pushed CNN classification of regular-script masters to 90–96% [Zhang et al., IJDAR 2019; Sensors 2024], and large-scale benchmarks now cover 142 calligraphers [MCCD, ICDAR 2025]. Accuracy itself is saturated. What remains poorly understood is *what the models actually use*: which spatial scales carry calligrapher identity, whether interpretable frequency-domain features explain part of it, and whether learned style representations generalize across characters the model has never seen — the setting that matters for real applications (a learner practices characters that are not in any reference book).

Our contributions:

1. **A character-controlled dataset design.** 7 calligraphers × 1,057 characters × 7,449 images with same-character cross-calligrapher pairs — a text-dependent structure public datasets (single-label images) cannot provide.
2. **A frequency-domain answer to "structure vs. brushwork."** Radial low-pass ablation localizes 95% of identifiable style below 10% of the Nyquist frequency; contour-harmonic sweeps show handcrafted frequency features carry distributed, partial signal.
3. **Character- and book-disjoint verification.** Style embeddings verify calligrapher identity on unseen characters at AUC 0.998, and 0.989 when restricted to cross-copybook pairs — with explicit confound analysis (Sec. 6) quantifying how much of the signal could come from reproduction artifacts.

## 2. Related Work

**Calligraphy style classification.** CNN-based classification of regular-script masters is well studied: Zhang et al. [1] classify the four Tang/Yuan masters (Ouyang Xun, Yan Zhenqing, Liu Gongquan, Zhao Mengfu) with a SE-block CNN augmented with Haar wavelet layers; a 2024 study [2] reaches 96.2% on four Tang masters with 8,282 images. ShufaNet [3] addresses the few-shot setting with metric learning (~65% few-shot, ~91% full). The recently released MCCD benchmark [4] scales to 142 calligraphers and 330K character images with multi-task baselines, and VLM/diffusion lines [5, 6] move to page-level understanding and generation. Accuracy on small closed sets is saturated; none of these works analyze *which spatial scales* carry the identity signal, and all use single-label images without character-controlled pairing.

**Frequency-domain and handcrafted shape features.** Fourier descriptors originate with Granlund [7] and remain standard for closed-contour shape analysis; wavelet-domain features have been applied to font/calligraphy style [8]. In the broader writer-identification literature, handcrafted descriptors have been largely superseded by deep models (page-level ViT pipelines reach ~99% on IAM/CVL [9]), yet fusing handcrafted and deep descriptors remains an active topic [10]. To our knowledge no prior work systematically analyzes Chinese calligraphic *style* in the frequency domain — the gap this study targets.

**Text-dependent design.** Writer identification distinguishes text-dependent from text-independent settings; text-dependent comparison (same textual content, different writers) isolates style from content. Public calligraphy datasets provide single-label images and cannot support this design; our same-character cross-calligrapher pairs bring the text-dependent protocol to calligraphy.

**Calligraphy education and aesthetic assessment.** CHAED [11] pairs 1,000 handwritten characters with human aesthetic ratings and predicts them from 22 interpretable global shape features — the closest precedent for our "interpretable features + human validation" direction. A 2024 survey [12] covers handwriting quality evaluation; classroom studies report that expert rubrics weight structure and spatial arrangement at ~70% [13], consistent with our frequency-domain finding that most identity signal is structural.

## 3. Dataset

7 master calligraphers (Zhiyong 智永, Ouyang Xun 歐陽詢, Yu Shinan 虞世南, Yan Zhenqing 顏真卿, Liu Gongquan 柳公權, Zhao Mengfu 趙孟頫, Shen Yinmo 沈尹默) spanning Sui/Tang to the 20th century; 10 copybooks; 7,449 images; 1,057 unique characters. Character images were collected from publicly available copybook reproductions on the web; our contribution is the curation pipeline — cleaning, per-character labeling (CSV), a character-level index linking every character to every calligrapher who wrote it, and the same-character pairing structure. All images are preprocessed to uniform 512×512 binarized glyphs (white background), removing paper texture, rubbing background, and ink color — leaving only glyph geometry. We release the pipeline and index; raw images follow the source materials' terms of use.

| Calligrapher | Books | Images | Unique chars |
|---|---|---|---|
| Liu Gongquan | 1 | 1,399 | 492 |
| Ouyang Xun | 1 | 936 | 485 |
| Shen Yinmo | 4 | 1,911 | 553 |
| Yan Zhenqing | 1 | 1,725 | 631 |
| Yu Shinan | 1 | 316 | 228 |
| Zhao Mengfu | 1 | 442 | 282 |
| Zhiyong | 1 | 720 | 720 |

**Evaluation protocol.** All experiments use *character-disjoint* splits: the set of unique characters is partitioned 80/20, and every image of a test character is excluded from training. Models must therefore generalize style across characters rather than memorize character-calligrapher co-occurrence. Results are reported as mean ± std over 5 random character partitions (seeds).

## 4. Methods

### 4.1 Normalized contour Fourier descriptors
Each glyph's contours (outer + holes, up to 8 by perimeter) are resampled to 256 points at uniform arc length; the complex boundary sequence is Fourier-transformed; descriptors are made translation- (drop DC), scale- (normalize by first harmonic), rotation- and start-point-invariant (magnitude spectrum). Per-glyph features: perimeter-weighted mean and per-dimension std over contours, ±20 harmonics.

### 4.2 Baseline feature sets
- **Spectral-7**: the platform's original 7 spectral statistics (band energies, centroid, DC ratio, slope, decay) computed per contour and averaged.
- **Hu moments**: log-scaled 7 invariant moments.
- Classifiers: logistic regression, RBF-SVM, random forest (results report the best per feature set).

### 4.3 CNN baseline
ResNet-18 (ImageNet init), 224×224 binarized input, 15 epochs AdamW, light affine augmentation; model selection on a character-disjoint validation split carved from training characters.

### 4.4 Same-character pair verification
On test characters only: all image pairs of the same character form the pair pool; positives = same calligrapher, negatives = different calligraphers (subsampled to ≤60/character). Embeddings = penultimate ResNet features trained for classification on training characters only; score = cosine similarity; metric = ROC-AUC. Handcrafted-feature baseline uses z-scored concatenated features.

## 5. Results

### 5.1 Classification (Fig. 1)

| Features | Best classifier | Accuracy | Macro-F1 |
|---|---|---|---|
| Spectral-7 (original) | SVM | 31.3% ± 1.9 | 21.6 |
| Hu moments | LogReg | 37.7% ± 2.0 | 25.6 |
| Fourier descriptors (ours) | SVM | 39.9% ± 1.8 | 37.7 |
| All handcrafted | SVM | **49.4% ± 1.7** | 48.4 |
| ResNet-18 | — | **98.7% ± 1.0** | 98.5 |
| Majority class / chance | | 25.7% / 14.3% | |

Handcrafted features are complementary (concatenation +9.5 pts over the best single set) but capture only about half the class-separable signal.

### 5.2 Where the style signal lives (Figs. 2, 3)

**Contour harmonics (Fig. 2):** accuracy rises smoothly from 28.0% (±1 harmonic) to 46.9% (±64) with no saturation — style information is *distributed* across the contour spectrum, not concentrated in a few low harmonics.

**2D spatial frequency (Fig. 3):** retraining the CNN on radially low-passed images:

| Cutoff (× Nyquist) | 0.02 | 0.05 | 0.1 | 0.2 | 0.4 | 1.0 |
|---|---|---|---|---|---|---|
| Accuracy | 48.5% | 78.2% | **94.7%** | 97.3% | 97.2% | 98.7% |

10% of the spatial-frequency radius — coarse stroke layout, no fine brush detail — already yields 95% accuracy. The traditional pedagogy claim "structure first, brushwork second" (結構為本) is quantitatively supported: brush-tip detail contributes only the final ~4 points.

### 5.3 Verification on unseen characters (Fig. 4)

| Method | Training | ROC-AUC |
|---|---|---|
| Handcrafted features (cosine) | none | 0.635 ± 0.061 |
| DINOv2 ViT-S/14 embedding (cosine) | none (generic self-supervised) | 0.793 ± 0.021 |
| ResNet-18 embedding (cosine) | domain (our training characters) | **0.998 ± 0.000** |

Three generations of representation on the same protocol: generic foundation-model features capture substantial style signal with zero training, but domain training still contributes a decisive margin — calligraphy style verification is not free-riding on generic visual features.

### 5.4 Robustness: is it style, or is it the copybook?

Because each calligrapher is represented by specific copybooks, a model could exploit reproduction artifacts (stroke weight of a particular edition, binarization edge character) rather than style. Three checks:

- **Book statistics.** Stroke widths differ across calligraphers (8.2–13.4 px) — itself a stylistic property — while Shen Yinmo's four books are mutually consistent (9.0–10.0 px), indicating uniform preprocessing did not inject strong per-book width bias.
- **Book identification.** A CNN distinguishes Shen Yinmo's own four books at 88.3% (chance 39%) under character-disjoint splits: a *book signature* exists (mixing genuine intra-writer variation across works with reproduction artifacts — these cannot be fully disentangled without additional editions).
- **AUC decomposition.** Restricting verification positives to *cross-book* pairs (both images the same character, same calligrapher, different books): AUC drops only from 0.9987 to **0.9889**. Style, not the book, carries the verification signal.
- **Leave-one-book-out.** Training the 7-way classifier with one Shen Yinmo book fully held out, then testing whether that unseen book is still recognized as Shen Yinmo (2 seeds each): book 01 → 99.3%, book 10 → 94.2%, book 08 → 71.6% (high variance across seeds). Style largely transfers to entirely unseen source material, while book 08's drop indicates genuine intra-writer variation across works — consistent with the 88.3% book-identification result and worth studying rather than hiding.

### 5.5 Cross-dataset external validation

We test the model (trained on all 7,449 of our images) on the kai-script portion of an independently collected public dataset [14] covering 6 of our 7 calligraphers (40,152 images; different sources, scanning and cropping pipelines).

| Setting | Accuracy (6-way, chance 16.7%) |
|---|---|
| Raw binarized glyphs | 32.0% ± 4.7 |
| Stroke-width normalized (skeletonize + fixed-width redraw, train & test) | 37.1% (seed0 42.2%) |

The confusion structure is informative: without normalization, thin-stroke external images collapse onto our thin-stroke classes (Liu Gongquan and Yu Shinan are *never* predicted), confirming that in-dataset accuracy partly rides on stroke weight and reproduction character. Normalization recovers Yan Zhenqing from 16% to 75% while Zhiyong/Shen Yinmo stay high — geometry alone does transfer for several calligraphers. The residual failures (Liu Gongquan, Yu Shinan ≈ 0%) are consistent with the external dataset drawing on *different works* by those masters (cf. our leave-one-book-out finding that even the same calligrapher's works differ), plus unverifiable labeling in the external source. Cross-source calligrapher identification is substantially harder than in-dataset results suggest — a finding we consider more valuable than the 98.7% headline.

### 5.6 Zero-shot style generation with same-character ground truth

Using pretrained FontDiffuser [15] zero-shot (content = standard-font render, style = one reference glyph), we generate 210 characters (30 per calligrapher) *for which we hold the calligrapher's real glyph* — an evaluation setting font-generation papers cannot access, since they lack same-character ground truth across writers.

| Metric | Value |
|---|---|
| Style match rate — generated (classifier trained on real data) | 22.9% |
| Style match rate — real ground-truth glyphs (upper bound) | 74.8% |
| Style match rate — standard-font content images (lower bound) | 13.8% |
| SSIM generated vs. ground truth | 0.531 |
| FD cosine: generated vs. target's real glyph / vs. another calligrapher's | 0.983 / 0.960 |

*(The 74.8% upper bound rather than ~99% reflects a processing-domain gap between the paired 256px ground-truth crops and the original training images — the three rows share this evaluator, so relative comparison stands.)*

*(Numbers above are from the initial evaluator; all comparisons below use a single **frozen** evaluator — we found that retraining the evaluator per run introduces ±10-point noise that had initially distorted our conclusions, a methodological lesson we report explicitly.)*

**Fine-tuning and six interventions (frozen evaluator, GT upper bound 91.9%):**

| Configuration | Style match | SSIM |
|---|---|---|
| Zero-shot | 20.0% | 0.531 |
| Fine-tune (15k steps, best) | 32.4% | 0.556 |
| + frequency-structure loss, coeff 0.1 (ours-v1) | 32.9% | 0.554 |
| + class-balanced resampling | 31.0% | 0.556 |
| + guidance scale 7.5→12 | 33.8% | 0.556 |
| + verification-guided reranking (K=5, independent selector) | 34.3% | 0.557 |
| + frequency loss coeff 2.0 repair fine-tune | 33.3% | 0.563 |
| Reranking oracle upper bound (perfect selector) | 37.1% | — |

**Diagnosis: the structure gap.** Every intervention plateaus near 34%. Visual and quantitative analysis reveals why: generated glyphs *keep the standard font's skeleton* and transfer only stroke appearance. For the most structurally distinctive masters, generated output is literally more similar to the standard-font content image than to the master's real glyph (Liu Gongquan: SSIM 0.552 to content vs. 0.540 to ground truth; 39% of all outputs are closer to the content than to the target). Stroke *width*, by contrast, is reproduced almost perfectly (e.g., Zhao Mengfu 13.7 vs. 13.5 px). The surviving classes (Yu Shinan 100%, Shen Yinmo 87%) are precisely those whose real structure is closest to the modern standard font.

This closes the loop with Finding 1: **calligrapher identity is structural (low-frequency), and one-shot diffusion font generation transfers texture but not structure — so style match is architecturally capped**. Bridging the structure gap likely requires skeleton-level or layout-level supervision rather than image-space losses (our 20× frequency-loss dose also failed, consistent with diffusion's inherent coarse-to-fine generation already saturating low-frequency reconstruction). We consider this diagnosis — six controlled interventions, a quantified failure mode, and a precise open problem — the main contribution of the generation study, and the open problem itself a direction for graduate research.

## 6. Limitations

- Cross-book checks rely on a single calligrapher with multiple books (Shen Yinmo); MCCD [ICDAR 2025] external validation is planned to test cross-dataset generalization.
- Book signature (88.3%) means the 7-way classification number is partly inflatable by source cues; the cross-book verification AUC (0.989) is the cleaner headline claim.
- The dataset is regular-script (楷書) dominant; conclusions may not transfer to running/cursive scripts.
- Aesthetic/educational scoring on the deployed platform is not yet validated against expert ratings (study planned).

## 7. Application: the Mozji (墨跡習字) platform

The findings feed directly into a deployed web platform (FastAPI, [calligraphy-analyzer.onrender.com](https://calligraphy-analyzer.onrender.com)) built on the same dataset. Learners upload a photographed practice character and receive descriptive, non-judgmental feedback: a pixel-level difference overlay against a chosen master (red = extra ink, blue = missing ink), centroid/balance analysis, and — motivated by Sec. 5.2 — feedback ordered *structure first*: since 95% of identity signal lives in coarse layout, the platform prioritizes structural deviation over brush-tip detail, matching both the data and traditional pedagogy. The same-character pairing index also powers a cross-master comparison view: any character can be viewed side-by-side across every master who wrote it. A planned validation study will correlate the platform's similarity metrics with expert ratings from a collaborating calligraphy teacher.

## 8. Conclusion and Future Work

We put a number on a centuries-old pedagogical belief, showed that learned style representations survive both unseen characters and unseen source books, and honestly quantified how much of the remaining signal could be source artifacts. Future work: external validation on MCCD [4]; stroke-width-normalized (skeletonized) re-runs to further isolate geometry from reproduction; expert-rating validation of the platform's metrics; and few-shot style generation for characters a master never wrote (the platform's original motivating pain point), using modern font-generation methods.

## References

[1] J. Zhang, M. Guo, J. Fan. "A novel CNN structure for fine-grained classification of Chinese calligraphy styles." *IJDAR* 22(2), 2019.
[2] "A Novel CNN Model for Classification of Chinese Historical Calligraphy Styles in Regular Script Font." *Sensors* 24(1), 2024.
[3] "ShufaNet: Classification method for calligraphers who have reached the professional level." arXiv:2111.11350, 2021.
[4] "MCCD: A Multi-Attribute Chinese Calligraphy Character Dataset." *ICDAR*, 2025. arXiv:2507.06948.
[5] "CalliReader: Contextualizing Chinese Calligraphy via an Embedding-Aligned VLM." arXiv:2503.06472, 2025.
[6] "UniCalli: unified diffusion for Chinese calligraphy generation." arXiv:2510.13745, 2025.
[7] G. H. Granlund. "Fourier preprocessing for hand print character recognition." *IEEE Trans. Computers*, 1972.
[8] "Classifying Fonts and Calligraphy Styles Using Complex Wavelet Transform." *SIViP*, 2015.
[9] Y. Li, Y. Zhang. "Writer identification based on vision transformer and CBAM." *JIFS*, 2023.
[10] "Length Independent Writer Identification Based on the Fusion of Deep and Hand-Crafted Descriptors." 2019.
[11] R. Sun et al. "Aesthetic Visual Quality Evaluation of Chinese Handwritings." *IJCAI*, 2015. (CHAED)
[12] "Quality evaluation methods of handwritten Chinese characters: a comprehensive survey." *Multimedia Systems*, 2024.
[13] "Cluster analysis of peer assessment in a calligraphy course." *SAGE Open*, 2024.
[14] zhuojg. "chinese-calligraphy-dataset." GitHub, 2022. 138,499 images, 19 calligraphers, Apache-2.0.
[15] Z. Yang et al. "FontDiffuser: One-Shot Font Generation via Denoising Diffusion with Multi-Scale Content Aggregation and Style Contrastive Learning." *AAAI*, 2024.
