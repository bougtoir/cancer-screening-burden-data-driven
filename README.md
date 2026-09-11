# 市中「血液だけで簡単」がん検査の医療機関負荷シミュレーション

このリポジトリは、市中で販売・宣伝されている「血液だけで簡単にがん検査」類の
多発する偽陽性が、どれだけの追加医療行為を生み、どこで医療提供体制を圧迫するかを
定量的に議論するための**データ駆動型シナリオモデリング**リポジトリです。

## 目的

- スクリーニング陽性者のうち、実際に医療機関を受診する割合（follow-up rate）を
  0%〜100%まで変えたとき、がん種ごとにどれだけの偽陽性・真陽性・追加受診が生じるか。
- その結果、CT・MRI・内視鏡・専門医外来・一次医療（primary care）などの診療能力がどの程度圧迫されるか。
- 「どこかで線を引く」規制の議論に使える、仮想的な閾値や指標を提示する。

## 重要な注意

`parameters.yaml` の数値は、公開データから再現可能に生成しています。

- **実データ由来**: がん発生率（国立がん研究センター「Cancer Statistics in Japan」）、人口構成（同ファイル `pop` sheet）、診療能力（厚生労働省「医療施設（静態・動態）調査」2023）。
- **仮定として残している部分**: 市中血液がん検査の利用者年齢構成、感度・特異度のがん種別値、精密検査経路・追加受診回数、診療能力の「がん関連に使えるシェア（20%）」。これらは感度分析として明示されています。
- シミュレーションは**確定的期待値**を計算しており、個人レベルの予測ではありません。
- 有病率は未診断点有病率の公表値がないため、2023年成人（20歳以上）年齢別発生率を代理変数として使っています。

## 実行方法（再現手順）

```bash
pip install -r requirements.txt
python prepare_parameters.py   # 公開データから parameters.yaml を生成
python simulate.py             # シミュレーション本体（CSV/PNG出力）
python specialist_capacity.py  # 専門医あたり負荷（Table 4 の入力）を生成
python age_analysis.py         # 年齢別PPV分析と購買層シナリオ
python sensitivity_analysis.py # 多感度分析（特異度・受診率・キャパシティシェア・感度）
python build_manuscript.py     # 汎用原稿 Markdown + 図表 PPTX/DOCX
python build_fmch_manuscript.py  # Family Medicine and Community Health 向け原稿
python build_health_policy_manuscript.py  # Health Policy (Elsevier) 向け原稿
python build_jms_manuscript.py  # Journal of Medical Screening (Sage) 向け投稿パッケージ
```

必要な Python パッケージは `requirements.txt` に記載されています。

## 入力ファイル

- `prepare_parameters.py`: 公開データを読み込み `parameters.yaml` を生成するスクリプト。
- `parameters.yaml`: シミュレーション設定。有病率・医療能力は公開データから、感度・特異度は文献レビューから、経路・追加受診は仮定として記載。
- `simulate.py`: シミュレーション本体。
- `age_analysis.py`: 年齢別陽性適中率（PPV）を計算。
- `build_manuscript.py`: 出力ファイルから原稿用 Markdown・PPTX・DOCX を生成。

## 主な出力（`output/`）

| ファイル | 内容 |
|----------|------|
| `by_cancer_and_followup.csv` | 受診率 × がん種ごとの期待値 |
| `aggregate_by_followup.csv` | 受診率ごとの合計値と医療能力利用率 |
| `summary_default_followup.csv` | 受診率 50% 時点のがん種別サマリー |
| `specificity_sweep.csv` | 特異度を変化させた感度分析結果 |
| `age_specific_ppv.csv` | 年齢別 PPV テーブル |
| `weighted_ppv_by_distribution.csv` | 年齢構成で重み付けした PPV |
| `age_scenarios.csv` | 購買層年齢シナリオ別の集計 PPV |
| `sensitivity_summary.csv` | 多感度分析の集計表 |
| `tornado_max_capacity.png` | 診療能力利用率への一方向感度分析（トルネード図） |
| `tornado_ppv.png` | 集計 PPV への一方向感度分析（トルネード図） |
| `age_scenario_ppv.png` | 購買層年齢シナリオ別の集計 PPV |
| `total_visits_by_followup.png` | 受診率に対する総追加受診数（積み上げ） |
| `capacity_utilization.png` | 診療能力利用率の推移 |
| `ppv_by_age.png` | 年齢別 PPV の推移 |
| `ppv_by_cancer.png` | がん種ごとの陽性適中率（PPV） |
| `false_positives_by_cancer.png` | 真陽性 vs 偽陽性の比較 |
| `specificity_sweep.png` | 特異度が偽陽性数・受診負荷に与える影響 |

## 議論資料・原稿

- `discussion.md`: 市中血液がん検査への規制の線引きに関する議論（旧版）
- `healthcare_exhaustion.md`: 「無駄な検査の結果、医療が疲弊する」という議論の骨格と根拠（旧版）
- `manuscript/manuscript.md`: 英語原稿 Markdown ドラフト（数値は output から再生成）
- `manuscript/manuscript_tables.docx`: 表の編集可能ファイル
- `manuscript/manuscript_figures.pptx`: 図の編集可能ファイル
- `manuscript/manuscript_fmch.md`: Family Medicine and Community Health 向け Markdown 原稿
- `manuscript/manuscript_fmch.docx`: FMCH 向け原稿（docx、図表インライン）
- `manuscript/manuscript_fmch_tables.docx`: FMCH 向け表（Table 1-4 + Supplementary Table S1-S2）
- `manuscript/manuscript_fmch_figures.pptx`: FMCH 向け図（Figure 1-4 + Supplementary Figure S1-S3）
- `manuscript/manuscript_health_policy.md`: Health Policy 向け Markdown 原稿
- `manuscript/manuscript_health_policy.docx`: Health Policy 向け原稿（docx、図表インライン）
- `manuscript/manuscript_health_policy_tables.docx`: Health Policy 向け表（Table 1-2 + Supplementary Table S1-S4）
- `manuscript/manuscript_health_policy_figures.pptx`: Health Policy 向け図（Figure 1-2 + Supplementary Figure S1-S5）
- `manuscript/title_page_health_policy.docx`: Health Policy 用タイトルページ（匿名化審査用）
- `manuscript/cover_letter_health_policy.docx`: Health Policy 用カバーレター
- `manuscript/manuscript_jms.md` / `.docx`: Journal of Medical Screening 向け原稿（タイトルページ・構造化抄録・本文・宣言・Sage Vancouver 参考文献、図表インライン、Word ネイティブ OMML 数式）
- `manuscript/manuscript_jms_tables.docx`: JMS 向け表（Table 1-2 + Supplementary Table S1-S4）
- `manuscript/manuscript_jms_figures.pptx`: JMS 向け図（Figure 1-2 + Supplementary Figure S1-S5、編集可能）
- `manuscript/figures_jms/*.png`: JMS 向け個別図ファイル（300 dpi 以上）
- `manuscript/supplementary_jms.md` / `.docx`: JMS 向け補足資料
- `manuscript/cover_letter_jms.docx`, `manuscript/reporting_checklist_jms.docx`: JMS 用カバーレターと STROBE チェックリスト
- `manuscript/submission_package_jms.zip`: 上記をまとめた投稿パッケージ

## モデルの要点

1. 対象集団 `N` 人に対し、各がんの有病率 `p` から真の患者数を設定。
2. 感度 `Se`、特異度 `Sp` を用いて期待値で真陽性 `TP = N·p·Se`、
   偽陽性 `FP = N·(1-p)·(1-Sp)` を計算。
3. 陽性者のうち `f`（受診率）が医療機関を受診し、
   `pathway` で定義された CT / MRI / 内視鏡 / 専門医外来を受ける。
4. 真陽性には治療・経過観察の追加受診、偽陽性には再検査・安心化の追加受診を加算。
5. これらを `capacity` の各診療能力と比較し、利用率（%）と閾値を算出。

## 仮定の限界

- 各がんのマーカーは独立に評価しているため、同一人物が複数の偽陽性を持つ可能性を
  無視しています。これは「偽陽性シグナルごと」の負荷を見積もる上側近似と解釈できます。
- 有病率は「未診断の点有病率」ではなく、2023年成人（20歳以上）年齢別発生率を代理とした値です。
  より正確な議論にはスクリーニング対象集団の実際の有病率データが必要です。
- 医療能力のベースラインは「がん関連診療に使えるシェア（20%）」という仮想的な値であり、
  実際の施設能力ではありません。
- 感度・特異度は文献レビューからの代表値を使用しており、がん種別・ステージ別の差は
  感度分析として別パラメータで探っています。

## ライセンス

MIT
