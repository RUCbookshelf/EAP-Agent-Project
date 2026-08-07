# 独立复核报告 — SWECCL 2.0 L2 语料准备包（sweccl2-weccl20-v0.1.0）

- 复核角色：独立复核员（fresh reviewer；不沿用协调者假设，全部基于实际文件独立验证）
- 首次复核日期：2026-08-07
- 复核包路径：`A:\EAP Agent Project\writing-feedback-mvp\docs\corpus-readiness\sweccl2\`
- 工具路径：`A:\EAP Agent Project\writing-feedback-mvp\scripts\corpus_readiness\`（01-10 脚本 + tests）
- 语料物理根：`A:\[Linguistics Data] Corpus\SWECCL 2.0\`
- 首次复核运行时：`A:\EAP Agent Project\tmp\corpus-readiness-venv\Scripts\python.exe`（当时有效；该临时环境已在收口后删除，后续复验使用重建的隔离环境）

## 复核方法

对 Goal 第 23 节十项范围逐项独立核验：清单与磁盘双向对照、SHA-256 重算、
派生文件编码往返核对、重复组文件级抽查、报告与机器工件交叉比对、禁用词扫描、
git 状态检查、测试套件实跑。复核期间未修改任何 corpus 数据、未改动
`.agent-workflow/` 规划文件、未删除任何文件。

## 逐项结果（首次复核，均通过数据工件级验证）

### 1. 物理清点完整性 — PASS

- `data/physical_inventory.csv`：19,858 数据行（含 4 个根级工件），sha256 全部非空（0 空值），19,858/19,858 physical_status=ok。
- 组件计数与磁盘实况一致：WECCL20/RAW 4950、LEMMA 4950、TAGGED 4950、SECCL20/AUDIO 2139、TEXTS 2852、TOOLS 13。
- 根目录实况（4 文件：autorun.exe、autorun.inf、fltrp.avi、SWECCL2.0_语料库概况报告.md）与当前清单一致；发现快照中的
  manual PDF（15,126,818 字节）已移出根目录，哈希保留于 `physical_inventory_discovery_snapshot.csv`，与
  `corpus_version.json` 说明相符。快照与当前清单仅差该 PDF 与概况报告.md 一对文件，其余 19,857 项完全一致。
- `corpus_version.json` 中 `manifest_hash` 为 11 个清单文件的复合 SHA-256，重算结果
  `0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9` 与记录一致（MATCH）。

### 2. 清单完整性 — PASS

- `data/corpus_manifest.csv`：4,950 行、4,950 个唯一 document_id；document_id 集合与 RAW 物理文件名集合完全一致。
- 六个维度（genre、prompt_id、major_type、entry_year、grade、timed_status）均 4,950/4,950 已填充，覆盖 100%。
- 文档对照与物理一致：total 4,950；argumentative 4,680 / expository 270；timed 2,499 / untimed 2,451。
- 全部 4,950 行 `source_sha256` 与 `physical_inventory.csv` 中 RAW 文件的 sha256 一致（0 处不匹配）。
- 可用性标志：raw_usable yes=4,949/no=1，lemma_usable yes=4,949/no=1，tagged_usable yes=4,950，与
  `corpus_version.json` 的 usable_variants（4949/4949/4950）一致。
- `data/documentation_vs_physical.csv`：43 行 N 状态全部 MATCH（token 状态 41 MISMATCH 均注明为计数工具差异，
  物理 1,248,026 vs 文档 1,248,476，偏差 0.04%，属已记录方法学说明）。

### 3. 哈希溯源 — PASS

- 抽查 5 个文件重算 SHA-256（WECCL20/RAW/WARG0001、WECCL20/LEMMA/WARG2081、WECCL20/TAGGED/WARG2081、
  SECCL20/TEXTS/TASK1/2003/03-130/03-130-01A、TOOLS/antconc.exe）：5/5 与清单一致。
- 派生 UTF-8 往返抽查 3 个文件（ascii 的 RAW/WARG0001、gbk 的 SECCL 03-160-29A、cp1250 的 LEMMA/WARG2730）：
  源字节按检测编码解码、UTF-8 派生解码、回编源编码，三者逐字一致；源/派生 sha256 与 `derived_manifest.csv`
  一致（3/3）。`derived_relative_path` 以 `PREPARED\utf8\` 为基准；磁盘派生层 17,703 个文件与清单 17,703 行一致。

### 4. 变体配对 — PASS

- `data/variant_pairing.csv`：4,950 行、document_id 与 manifest 完全一致；raw/lemma/tagged present 均为 4,950。
- WARG2081：RAW 实际 2,157 字节全 NUL、LEMMA 实际 2,150 字节全 NUL（均验证）；TAGGED 完好（423 tokens，
  CLAWS4 风格词_码内容，格式率 1.0）。配对表中 raw/lemma usable=corrupt_all_nul、tagged=usable，正确。
- 无缺失变体（缺失数 0），header 跨变体一致 4,950/4,950。

### 5. 质量与重复 — PASS（数据工件层面）

- `data/quality_issues.csv`：90 行，分类计数 all_nul_bytes 2 / extremely_short_text 1 / variant_identical_bytes 1 /
  non_ascii_learner_content 74 / chinese_annotator_note_in_transcript 12，合计 90，与 `quality_summary.json` 一致。
- 抽查 2 个文本重复组（WARG2725/WARG4127、WARG4215/WARG4605）：正文规范化后逐字相等（非空）；另抽查 1 个字节重复组
  （LEMMA/WARG0378/WARG4122）：SHA-256 相同。
- `duplicate_report.csv`：348 组（raw text 115、raw byte 12、lemma byte 117、tagged byte 104），与 06 报告表一致。
- 唯一受影响文档数复核：230（text）+ 234（byte）- 224（重叠）= 240，加 WARG2081 = 241；与 06 报告、
  `leakage_plan.json`（240）、`reference_group_summary.json`（241）、holdout 计数（511 = 240 + 1 + 270，重复组与
  expository 零重叠）全部自洽。
- 候选排除：`corpus_exclusions_draft.csv` 2 行（WARG2081 RAW/LEMMA），状态 candidate，未静默删除。

### 6. 构成统计 — PASS

- `data/documentation_vs_physical.csv` 43 行 N 状态全部 MATCH；各维度（genre/major_type/entry_year/grade/timed_status/
  prompt_id）的 physical_n 与 manifest 独立重算一致（抽查 ARG01=133、ARG02=426、TOO_SPARSE ARG13=14/ARG19=18 等）。

### 7. 参照组、特征可行性与泄漏计划（逻辑一致性）— PASS

- 参照组：42 个候选 = 27 prompts + 2 genre + 2 timed + 2 major_type + 5 entry_year + 4 grade；状态 33/7/2
  （TOO_SPARSE 恰为 ARG13 N=14、ARG19 N=18，低于 min-N=30 且注明非规范性，最终政策归 Researcher）。
- 特征：10 项，READY 4 / PROMISING 4 / REQUIRES_VALIDATION 2，优先清单 8 项，与 `feature_summary.json` 一致；
  F-LEX-FREQ 的授权词表阻塞（D11）与 F-DISC-COHESION 的 D-L2-03 spike 均如实标注，无越权承诺。
- 泄漏计划：未创建任何最终分区（与文件事实一致）；约束（重复组成员不得跨 dev/eval、同 prompt 不跨切、270 篇评分
  说明文整体保护、WARG2081 仅 tagged）与 `holdout_candidates.csv`/`leakage_plan.json` 逻辑自洽。

### 8. 许可/隐私表述 — PASS

- `01` 与 `12` 均载明 `license_status = PARTIALLY_DOCUMENTED`（外部使用 REQUIRES_REVIEW）；`11` 通过 D3 许可模型
  开放项承接同一立场（首次复核时未复述该字段值；已在收口修正中补明，见 F5）。
- 13 份报告全文扫描：无完整学生作文/原始文本引用，仅含元数据、统计与表格行，无原始文本泄漏。

### 9. 架构合规 — PASS

- 对 `data/` 全部 CSV 表头与全部 JSON 键（含 `corpus_version.json`）做独立词
  `level/score/ability/mastery/gain/cefr` 正则扫描：0 命中。`unsupported_inference` 字段值中的
  proficiency/mastery/learning-gain 系禁用推断声明而非字段名，符合冻结架构口径。
- git 状态：`writing-feedback-mvp/app` 无任何修改/未跟踪文件；仓库内改动仅为既有文件与本包新增的
  `docs/corpus-readiness/`、`scripts/corpus_readiness/`（交付物）。未改动 app 生产代码。

### 10. 测试可运行性 — PASS

- 实跑 `tmp\corpus-readiness-venv\Scripts\python.exe -m pytest scripts\corpus_readiness\tests -q`：
  8 passed（1 条 pytest 缓存目录权限警告，与测试结果无关）。

## 评审发现（历史记录，保持可审计）

首次复核在数据工件全部正确的前提下，记录了以下 5 项报告散文层差异。以下为当时的原始描述：

1. `11`/`12` 报告曾写 "29 SECCL transcripts 含中文转写注释"，而 `quality_issues.csv` 为 12 行
   （6 个不同转写 × 任务文件夹副本）。
2. `02` 报告二进制明细曾自相矛盾：正文 "2,153 binary/needs-review（… 2 pdf …）" 的枚举合计为 2,154；
   当前清单实况为 needs_review=2,153、pdf=1（manual PDF 已于发现后移出）。
3. 标签级差异：`physical_inventory.csv` 对 WARG2730/WARG4140 记 `encoding_status=cn_detect`
   （detected_encoding=cp1250），散文与 `derived_manifest.csv` 记 "cp1250"；指向同一 2 个文件。
4. `00` 散文曾写 "9-step pipeline"，实际脚本为 01-10 共 10 个（+run_all.py 编排）。
5. `11` 当时未复述 `license_status=PARTIALLY_DOCUMENTED` 字段值（以 D3 开放项承接），01/12 已完整载明。

## Review findings and post-fix resolution

以下决议表记录每项发现从发现、修正到独立复验的完整闭环。机器可读工件在发现与修正前后均保持正确，未作任何改动；
所有修正均为报告/文档散文层改动，且已与机器工件交叉核验。

| Finding | Original issue | Resolution | Verification | Final status |
| --- | --- | --- | --- | --- |
| F1 | SECCL 中文转写注释计数："29" vs 工件 12（6 唯一 × 任务夹副本） | 11/12 已改为 12 物理文件 / 6 唯一转写，与 06 及 quality_issues.csv 一致 | quality_issues.csv 12 行；06/11/12 交叉比对；唯一转写 ID 数=6 | RESOLVED |
| F2 | 02 二进制/PDF 明细合计不一致（2,153 vs 枚举 2,154） | 02 已改为当前清单口径（2,153 = 2,139 mp3 + 8 exe + 1 pdf [TOOLS User Guide] + 2 doc + 1 avi + 1 sav + 1 xls），并明确区分发现快照（含 manual PDF）与当前清单 | physical_inventory.csv 实测 needs_review=2,153、pdf=1；快照含 PDF（15,126,818 B）；corpus_version.json 说明相符 | RESOLVED |
| F3 | cp1250 vs cn_detect 标签差异 | 确认为两个字段描述同一检测结果的不同方面（detected_encoding=值；encoding_status=检测路径）；03 已新增 Terminology note 明示 | physical_inventory.csv 两字段并置核对；03/derived_manifest 用值（cp1250）；无 schema 错误，不改机器标签 | RESOLVED - TERMINOLOGY CLARIFIED |
| F4 | "9-step pipeline" vs 10 个脚本 | 00 已改为精确表述（scripts 01-10；run_all.py 编排步骤 01-09；10_version.py 生成版本记录）；README 同步补 10_version 行 | scripts 目录实计 10 个脚本 + run_all.py；README/00 全文扫描无 "9-step" 残留 | RESOLVED |
| F5 | 11 未复述 license_status 字段值 | 11 已新增 License status 节：PARTIALLY_DOCUMENTED + 外部使用 REQUIRES_REVIEW | 01/11/12 三方一致；措辞未强化未弱化 | RESOLVED |

## Post-fix verification statement

All five review-layer documentation findings were resolved after the initial
independent review and were re-verified against the machine-readable
artifacts. No review-layer documentation finding remains open.

收口复验摘要（2026-08-07）：

- F1：`quality_issues.csv` 12 行 chinese_annotator_note_in_transcript；12 个物理文件对应 6 个唯一转写 ID；06/11/12 表述一致。
- F2：`physical_inventory.csv` 实测 needs_review=2,153、pdf=1；02 枚举合计=2,153，快照/当前区分明确；`corpus_version.json` 说明一致。
- F3：清单两字段语义一致（值=cp1250、路径=cn_detect）；03 已文档化；机器标签未改。
- F4：00/README 表述精确化；全目录扫描无 "9-step"/"9 step" 残留。
- F5：01/11/12 均载明 PARTIALLY_DOCUMENTED + REQUIRES_REVIEW。
- 聚焦测试：`python -m pytest scripts/corpus_readiness/tests/ -q` → 8 passed。
- 机器可读工件：无改动（散列核对一致）；corpus 源数据、PREPARED 内容、app 生产代码：无改动。

## Resolved review findings vs ongoing corpus limitations

下列 ONGOING CORPUS LIMITATIONS 是真实的语料层面限制，与上述已解决的散文层发现无关，不得视为已解决：

- TEM8 组件在物理副本中缺失（手册记载 916 文件）。
- WARG2081 的 RAW/LEMMA 变体为全 NUL 损坏（TAGGED 完好）。
- 240 篇文档处于重复组中，评估前须裁决。
- ARG13（N=14）与 ARG19（N=18）过稀，不能单独作为参照分布。
- 许可状态 PARTIALLY_DOCUMENTED，外部分发或学习者端使用 REQUIRES_REVIEW。
- 270 篇带评分的说明文须作为整体保护块用于评估。
- 手册 PDF 于发现后被移出语料根目录（哈希留存于发现快照）。

## 结论

READY_WITH_DOCUMENTED_LIMITATIONS

该结论保持不变：十项复核范围全部通过数据工件级验证；初始发现的 5 项散文层差异均已修复并经
机器工件交叉复核确认关闭。上述 READY_WITH_DOCUMENTED_LIMITATIONS 中的 DOCUMENTED_LIMITATIONS
仅指 ONGOING CORPUS LIMITATIONS 一节的真实语料限制，不包含任何已解决的评审发现。

## BLOCKING

无。

## 复核限制

- 哈希与编码为抽查（5 文件 / 3 文件），非全量重算；清单全量字段未逐项重跑（以交叉对照覆盖）。
- 参照组/特征/泄漏仅做逻辑一致性审查，未重算全量统计（按复核范围约定）。
- 未打开/解析 TOOLS/exp.sav、exp.xls（评分关联属下一 Goal 范围，包内已如实标注）。