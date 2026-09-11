# FMCH 査読者目線レビューと改善提案

対象原稿：`manuscript/manuscript_fmch.md` / `manuscript/manuscript_fmch.docx`  
対象誌：*Family Medicine and Community Health*（BMJ Publishing Group）

---

## 今回実装済みの改善

- タイトルを一次・専門医両方を含む表現に変更：
  *"False-positive cascade from direct-to-consumer multi-cancer early detection blood tests: implications for primary and specialty care"*
- Keywords に `primary care`, `shared decision-making` を追加
- Key points / Abstract / Conclusion で一次医療・地域保健への言及を強化
- Introduction に「DTC 検査の陽性結果を最初に受け持つのは家族医・一次医療医である」という文脈を追加し、3つの一次医療文献を新規引用（Church et al. 2025; Ueberroth et al. 2024; Wade et al. 2025）
- Discussion に **"Implications for primary care and shared decision-making"**  subsection を新設
- Methods のシナリオ記述で「日本をケーススタディとし、高所得国全体に一般化可能なメカニズムであることを明記」
- Limitations に以下を追加：
  - 一次医療受診を個別にモデル化していないこと
  - 感度・特異度をがん種横断的に均一とした仮定
  - 確率論的感度分析（PSA）未実施の理由
- Active voice / first-person 表現を整理（"We used" → "A ... model was used" など）
- Ethics approval セクションを追加
- 参考文献を本文中の **first appearance order** に合わせて Vancouver 番号を振り直すロジックを追加・実行
- CJK 文字不在を確認（0文字）
- Abstract 語数：217語（FMCH 推奨 <250語に収まる）

---

## 5領域に分けた査読者レビュー

### 1. 原稿（novelty, focus, logic, methods, results）

| 優先度 | 指摘 | 修正案 |
|--------|------|--------|
| **高** | 一次医療負荷がタイトル・Discussionで強調されているが、モデルは専門医・検査室負荷しかカウントしていない。 | `pathway` に `primary_care` を追加し、陽性者1人あたり1回の一次受診をカウント。可能であれば NDB/JMSB から総合診療・内科のキャパシティも推定して利用率を出す。最低限、総受診数に一次受診を含め、別の bar/line を Figure 1/2 に追加する。 |
| 高 | タイトルは「primary and specialty care」としているが、Figure/Table は specialist/diagnostic 中心。 | 新規 Table/Figure を追加するか、既存 caption に "primary care is the first point of contact" と注記。 |
| 中 | DTC 検査の年齢構成を「2023 成人人口」で代用している点が reviewer に突かれる。 | 年齢分布を感度分析で複数シナリオ（公的年齢構造、23andMe 型二峰性、DTC 販売層想定）として提示し、Table/Supplementary に追加。 |
| 中 | 引用文献が 11 とやや少ない。ガイドライン・政策文書を補強。 | 米国予防サービス専門部会（USPSTF）の推奨一覧、NICE/MCED 報告、厚労省のがん検診ガイドライン等を限定追加。 |
| 低 | Key Points の Question が「diagnostic and specialist workload」で始まっており、新しい focus より少し狭い。 | "What primary care, diagnostic, and specialist workload..." に変更。 |

### 2. 統計設計・解析

| 優先度 | 指摘 | 修正案 |
|--------|------|--------|
| **高** | 決定論的モデルは妥当だが、不確実性の提示がない。 | 各パラメータのプラスマイナス感度分析を追加。例えば specificity 95.0–99.9%、available-for-cancer-workup share 5–50%、follow-up rate 10–90% での PPV / 超過率を Table 3 拡張または Supplementary Table に示す。 |
| 中 | ベースケースの感度 0.70 / 特異度 0.990 が単一値である。 | 現実の文献範囲（感度 0.50–0.90、特異度 0.95–0.999）をターニャード図（tornado diagram）で示す。 |
| 低 | `prevalence` を `incidence` で代用していることの影響を定量化していない。 | 別途 Patient Survey や既存プレバレンス研究からスクリーニング対象前段階の既存症例数を取得し、最低限の補正シナリオを追加。 |

### 3. 図表

| 優先度 | 指摘 | 修正案 |
|--------|------|--------|
| 中 | Figure 1/2 の y 軸 "Additional visits per 100,000 screened" / "Capacity utilization" に一次医療が含まれていない。 | 上記 primary care 追加と同時に、Figure 2 に "Primary care visits" 系列を追加（キャパシティ未定なら仮想上限）。 |
| 中 | Table 2 の "Max resource utilisation (%)" が specialist であることが分かりにくい。 | カッコ内に "usually specialist visits" と明記するか、ヘッダーを "Max capacity utilisation (%, bottleneck resource)" に変更。 |
| 低 | Figure 4 は 70% follow-up だが、Table 3 は base case 50% であることが明記されている。 | キャプションに "at 70% follow-up" と既に記載あり、問題なし。 |

### 4. 再現性

| 優先度 | 指摘 | 修正案 |
|--------|------|--------|
| 中 | `build_fmch_manuscript.py` は追加されたが、README に再現コマンドの記載がない。 | README の「再現手順」に `python build_fmch_manuscript.py` を追加。 |
| 低 |  raw NDB zip や Patient Survey PDF は data/ に散在しているが、git 追跡対象外のまま。 | `.gitignore` または README で「data/ の生データは各自ダウンロード」と明記し、再現に必要なファイル名と取得先をリスト化。 |
| 低 | Figure 3 は `age_analysis.py` の出力で再現可能。年齢構成感度分析を追加する場合は `parameters.yaml` に分布を持たせ、`age_analysis.py` 経由で回す。 | 追加解析時に同じパイプラインで実施。 |

### 5. 主張の強さ

| 優先度 | 指摘 | 修正案 |
|--------|------|--------|
| 高 | 原稿は "regulatory guardrails" "clear performance thresholds" を結論にしているが、どの閾値か具体的でない。 | Discussion に "minimum acceptable PPV" や "specificity floor" を提示するか、専門医キャパシティ超過率 100% を超えない follow-up/specificity 閾値を補足表に示す。 |
| 中 | 専門医キャパシティは "illustrative capacity ceiling" と言及しているが、読者が 20% share が恣意的に見える。 | 5% / 10% / 20% / 50% share での超過閾値を Table 5/Supplementary Table で示し、主張の頑健性を示す。 |
| 低 | "overloads primary care" と言及する場合、一次医療の定量的根拠がないと reviewer は退回を主張する。 | 上記 primary care モデル追加まで結論では "primary and specialty care" と並列させつつ "downstream" を強調。 |

---

## 優先度まとめ（実装の勧め）

1. **最優先（投稿前に推奨）**
   - `pathway` に一次医療受診を追加し、総受診・キャパシティ図に反映
   - 感度・特異度 / available share / follow-up rate の多感度分析を Table/Supplementary 化
   - Reference format を FMCH Vancouver に合わせて最終確認

2. **高優先**
   - 年齢構成のシナリオ追加（DTC 購買層想定）
   - "What this paper adds" / "Implications for practice" を Key Points または Discussion 先頭に明文化

3. **中優先**
   - USPSTF/NICE など政策・ガイドライン文献を 2–3 件追加
   - README に `build_fmch_manuscript.py` 再現手順を追加

4. **低優先 / 提出直前**
   - 図の高解像度 TIFF/EPS 出力化
   - 著者情報・所属・対応著者を含む title page 作成
   - カバーレター用 "fit statement" 作成

---

## 現在の原稿状態

- `manuscript/manuscript_fmch.md`（査読者向けレビュー反映済み）
- `manuscript/manuscript_fmch.docx`（同内容、図表インライン）
- `manuscript/manuscript_fmch_tables.docx`
- `manuscript/manuscript_fmch_figures.pptx`
- 変更は PR #351 に push 済み

次のアクションとしては、上記 **最優先 3 項目** のうちご希望のものを選択していただければ、追加実装します。特に **一次医療受診をモデルに組み込む** のは、タイトル・Discussion の主張を強力に裏付けるため、最も reviewer 抵抗を下げる修正です。
