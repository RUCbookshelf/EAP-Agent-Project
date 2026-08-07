# 独立复核报告 — SWECCL 2.0 L2 语料准备包（sweccl2-weccl20-v0.1.0）

- 复核角色：独立复核员（fresh reviewer；不沿用协调者假设，全部基于实际文件独立验证）
- 复核日期：2026-08-07
- 复核包路径：`A:\EAP Agent Project\writing-feedback-mvp\docs\corpus-readiness\sweccl2\`
- 工具路径：`A:\EAP Agent Project\writing-feedback-mvp\scripts\corpus_readiness\`（01-10 脚本 + tests）
- 语料物理根：`A:\[Linguistics Data] Corpus\SWECCL 2.0\`
- 验证运行时：`A:\EAP Agent Project\tmp\corpus-readiness-venv\Scripts\python.exe`

## 复核方法

对 Goal 第 23 节十项范围逐项独立核验：清单与磁盘双向对照、SHA-256 重算、
派生文件编码往返核对、重复组文件级抽查、报告与机器工件交叉比对、禁用词扫描、
git 状态检查、测试套件实跑。复核期间未修改任何 corpus 数据、未改动
`.agent-workflow/` 规划文件、未删除任何文件。

## 逐项结果

### 1. 物理清点完整性 — PASS

- `data/physical_inventory.csv`：19,858 数据行（含 4 个根级工件），sha256 全部非空（0 空值），19,858/19,858 physical_status=ok。
- 组件计数与磁盘实况一致：WECCL20/RAW 4950、LEMMA 4950、TAGGED 4950、SECCL20/AUDIO 2139、TEXTS 2852、TOOLS 13。
- 根目录实况（4 文件：autorun.exe、autorun.inf、fltrp.avi、SWECCL2.0_语料库概况报告.md）与当前清单一致；发现快照中
  的 manual PDF（15,126,818 字节）已移出根目录，哈希保留于 `physical_inventory_discovery_snapshot.csv`，与
  `corpus_version.json` 说明相符。快照与当前清单仅差该 PDF ↔ 概况报告.md 一对文件，其余 19,857 项完全一致。
- `corpus_version.json` 中 `manifest_hash` 为 11 个清单文件的复合 SHA-256，重算结果
  `0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9` 与记录一致（MATCH）。

### 2. 清单完整性 — PASS

- `data/corpus_manifest.csv`：4,950 行、4,950 个唯一 document_id；document_id 集合与 RAW 物理文件名集合完全一致。
- 六个维度（genre、prompt_id、major_type、entry_year、grade、timed_status）均 4,950/4,950 已填充，覆盖 100%。
- 文档对照与物理一致：total 4,950；argumentative 4,680 / expository 270；timed 2,499 / untimed 2,451。
- 全部 4,950 行 `source_sha256` 与 `physical_inventory.csv` 中 RAW 文件的 sha256 一致（0 处不匹配）。
- 可用性标志：raw_usable yes=4,949/no=1，lemma_usable yes=4,949/no=1，tagged_usable yes=4,950 — 与
  `corpus_version.json` 的 usable_variants（4949/4949/4950）一致。
- `data/documentation_vs_physical.csv`：43 行 N 状态全部 MATCH（token 状态 41 MISMATCH 均注明为计数工具差异，
  物理 1,248,026 vs 文档 1,248,476，偏差 0.04%，属已记录方法学说明）。

### 3. 哈希溯源 — PASS

- 抽查 5 个文件重算 SHA-256（WECCL20/RAW/WARG0001、WECCL20/LEMMA/WARG2081、WECCL20/TAGGED/WARG2081、
  SECCL20/TEXTS/TASK1/2003/03-130/03-130-01A、TOOLS/antconc.exe）：5/5 与清单一致。
- 派生 UTF-8 往返抽查 3 个文件（ascii 的 RAW/WARG0001、gbk 的 SECCL 03-160-29A、cp1250 的 LEMMA/WARG2730）：
  源字节按检测编码解码 → UTF-8 派生解码 → 回编源编码，三者逐字一致；源/派生 sha256 与 `derived_manifest.csv`
  一致（3/3）。`derived_relative_path` 以 `PREPARED\utf8\` 为基准；磁盘派生层 17,703 个文件与清单 17,703 行一致。

### 4. 变体配对 — PASS

- `data/variant_pairing.csv`：4,950 行、document_id 与 manifest 完全一致；raw/lemma/tagged present 均为 4,950。
- WARG2081：RAW 实际 2,157 字节全 NUL、LEMMA 实际 2,150 字节全 NUL（均验证）；TAGGED 完好（423 tokens，
  CLAWS4 风格 `<word>_<tag>` 内容，1.0 格式率）。配对表中 raw/lemma usable=corrupt_all_nul、tagged=usable，正确。
- 无缺失变体（缺失数 0），header 跨变体一致 4,950/4,950。

### 5. 质量与重复 — PASS（数据工件层面）

- `data/quality_issues.csv`：90 行，分类计数 all_nul_bytes 2 / extremely_short_text 1 / variant_identical_bytes 1 /
  non_ascii_learner_content 74 / chinese_annotator_note_in_transcript 12，合计 90，与 `quality_summary.json` 一致。
- 抽查 2 个文本重复组（WARG2725/WARG4127、WARG4215/WARG4605）：正文规范化后逐字相等（非空）；另抽查 1 个字节重复组
  （LEMMA/WARG0378/WARG4122）：SHA-256 相同。
- `duplicate_report.csv`：348 组（raw text 115、raw byte 12、lemma byte 117、tagged byte 104），与 06 报告表一致。
- 唯一受影响文档数复核：230（text）+ 234（byte）− 224（重叠）= **240**，加 WARG2081 = 241；与 06 报告、
  `leakage_plan.json`（240）、`reference_group_summary.json`（241）、holdout 计数（511 = 240 + 1 + 270，重复组与
  expository 零重叠）全部自洽。
- 候选排除：`corpus_exclusions_draft.csv` 2 行（WARG2081 RAW/LEMMA），状态 candidate，未静默删除。

### 6. 构成统计 — PASS

- `data/documentation_vs_physical.csv` 43 行 N 状态全部 MATCH；各维度（genre/major_type/entry_year/grade/timed_status/
  prompt_id）的 physical_n 与 manifest 独立重算一致（抽查 ARG01=133、ARG02=426、TOO_SPARSE ARG13=14/ARG19=18 等）。

### 7. 参照组、特征可行性与泄漏计划（逻辑一致性）— PASS

- 参照组：42 个候选 = 27 prompts + 2 genre + 2 timed + 2 major_type + 5 entry_year + 4 grade；状态 33/7/2
  （TOO_SPARSE 恰为 ARG13 N=14、ARG19 N=18，低于 min-N=30 且注明“非规范性，最终政策归 Researcher”）。
- 特征：10 项，READY 4 / PROMISING 4 / REQUIRES_VALIDATION 2，优先清单 8 项，与 `feature_summary.json` 一致；
  F-LEX-FREQ 的授权词表阻塞（D11）与 F-DISC-COHESION 的 D-L2-03 spike 均如实标注，无越权承诺。
- 泄漏计划：未创建任何最终分区（与文件事实一致）；约束（重复组成员不得跨 dev/eval、同 prompt 不跨切、270 篇评分
  说明文整体保护、WARG2081 仅 tagged）与 `holdout_candidates.csv`/`leakage_plan.json` 逻辑自洽。

### 8. 许可/隐私表述 — PASS（含 1 项文档数字瑕疵，见差异清单）

- `01` 与 `12` 均载明 `license_status = PARTIALLY_DOCUMENTED`（外部使用 REQUIRES_REVIEW）；`11` 通过 D3 许可模型
  开放项承接同一立场，但未复述该字段值。
- 13 份报告全文扫描：无完整学生作文/原始文本引用，仅含元数据、统计与表格行（长行均为表项），无原始文本泄漏。

### 9. 架构合规 — PASS

- 对 `data/` 全部 CSV 表头与全部 JSON 键（含 `corpus_version.json`）做独立词
  `level/score/ability/mastery/gain/cefr` 正则扫描：0 命中。`unsupported_inference` 字段值中的
  “proficiency/mastery/learning-gain”系禁用推断声明而非字段名，符合冻结架构口径。
- git 状态：`writing-feedback-mvp/app` 无任何修改/未跟踪文件（diff stat 为空）；仓库内改动仅为既有文件
  （AGENTS.md、RUN_VERIFICATION_V0.7/V0.8.2）与本包新增的 `docs/corpus-readiness/`、`scripts/corpus_readiness/`
  （未跟踪，属交付物）。未改动 app 生产代码。

### 10. 测试可运行性 — PASS

- 实跑 `tmp\corpus-readiness-venv\Scripts\python.exe -m pytest scripts\corpus_readiness\tests -q`：
  **8 passed**（1 条 pytest 缓存目录权限警告，与测试结果无关）。

## 差异清单（非阻塞，均为报告散文层；数据工件全部正确）

1. **`11`/`12` 报告写 “29 SECCL transcripts 含中文转写注释”，实际为 12 个文件**（6 个不同转写 × 任务文件夹副本），
   与 `quality_issues.csv`（12 行）及 `06` 报告（12）一致；“29” 无法由任何文件事实导出。
2. **`02` 报告二进制明细自相矛盾**：正文 “2,153 binary/needs-review（… 2 pdf …）” 的枚举合计为 2,154；
   当前清单实况为 needs_review=2,153、pdf=1（manual PDF 已于发现后移出）。该明细按发现时状态书写，未随当前清单更新。
3. **标签级差异**：`physical_inventory.csv` 对 WARG2730/WARG4140 记 `encoding_status=cn_detect`（detected_encoding=cp1250），
   `02`/`03` 散文与 `derived_manifest.csv` 记 “cp1250”；指向同一 2 个文件，语义一致，仅标签层级不同。
4. **`00` 散文写 “9-step pipeline”**，实际脚本为 01–10 共 10 个（+run_all.py 编排）；属文字表述口径。
5. **`11` 未复述 `license_status=PARTIALLY_DOCUMENTED` 字段值**（以 D3 开放项承接），01/12 已完整载明。

## 验证命令与结果摘要

| 验证 | 命令/方法 | 结果 |
| --- | --- | --- |
| 清单/磁盘计数 | CSV 读取 + `Get-ChildItem` 实计 | 19,858 行、sha256 0 空；组件 4950/4950/4950/2139/2852/13 双一致 |
| 复合哈希 | 复算 10_version.py::manifest_hash() | MATCH `0d8940ff…659eb9` |
| 哈希抽查 | 重算 5 文件 sha256 | 5/5 MATCH |
| 往返核对 | 3 个派生文件源/派生双向解码 | 3/3 OK |
| 重复组抽查 | 2 文本组 + 1 字节组文件级比对 | 全部相等 |
| 禁用词扫描 | 全部 CSV 表头 + JSON 键正则 | 0 命中 |
| app 未改动 | `git status` / `git diff --stat -- app` | 无变化 |
| 测试套件 | venv `python -m pytest scripts/corpus_readiness/tests -q` | 8 passed（1 缓存目录权限警告） |

## 结论

**READY_WITH_DOCUMENTED_LIMITATIONS**

十项复核范围全部通过数据工件级验证；发现的 5 项差异均为报告散文层的数字/表述瑕疵，不涉及任何机器可读工件，
不影响语料准备包的可审计性、可复现性与下游使用。建议在下一个文档维护门修复差异清单 1–2 项（29→12、
02 二进制明细），其余为可选项。

## BLOCKING

无。

## 复核限制

- 哈希与编码为抽查（5 文件 / 3 文件），非全量重算；清单全量字段未逐项重跑（以交叉对照覆盖）。
- 参照组/特征/泄漏仅做逻辑一致性审查，未重算全量统计（按复核范围约定）。
- 未打开/解析 TOOLS/exp.sav、exp.xls（评分关联属下一 Goal 范围，包内已如实标注）。
