# Stage 5 研究方法/方法论评审记录（Methodology_Review_v0.1）

- 评审角色：独立研究/方法论评审员（fresh deepseek-v4-flash，未参与 Stage 5 实现）
- 评审日期：2026-08-07
- 评审范围：四项研究治理决策（评分关联、重复策略、评估保护、min-N 与回退层级）
- 评审方式：只读验证（xlrd / pyreadstat 读取 exp.xls / exp.sav；CSV/JSONL 交叉核对；
  只读阅读 app/corpus/groups.py、intelligence.py、resource.py 与版本工件）；
  未修改语料、未修改代码、未改动任何准备期或 Stage 5 数据工件。
- 总体审批意见：**APPROVED_WITH_CONDITIONS**（D1/D3 直接通过；D2/D4 附条件通过；
  条件均为文档口径修正，不要求改动任何数据工件或代码，不阻塞 WU4 分布作为正式策略使用）。

---

## D1 评分关联（exp.xls / exp.sav ↔ EXP01 清单）— **APPROVED**

### 数据核对结果（全部通过）

| 核对项 | 结果 |
| --- | --- |
| exp.xls | 存在；sheet=`scores`；271 行（270 数据 + 1 表头）× 8 列 |
| exp.xls 表头 | 精确等于 `ID, Rater_A, Rater_B, Rater_C, Language, Content, Organization, Average_score` |
| exp.xls ID | 270 个 `WEXP####`，无重复（270/270），无空值 |
| exp.xls 缺失 | 8 列空值/NaN 均为 0 |
| exp.sav | 270 行 × 8 列，表头与 exp.xls 完全一致，ID 集合与 exp.xls 双向相等 |
| exp.sav 缺失 | 8 列缺失均为 0 |
| 清单 EXP01 | corpus_manifest.csv 中 `prompt_id=EXP01` 恰为 270 行，ID 唯一、格式 `WEXP####`，genre=expository，raw_usable 全部为 yes |
| 集合相等 | 评分 ID 集合 == 清单 EXP01 集合，270/270，0 缺失 / 0 多余 |
| 读取伪影 | xlrd 在 stderr 输出文档所述 OLE2 警告（`SSCS size is 0 but SSAT size is non-zero`），文件内容读取完整，与 03 文档披露一致 |
| 学习者端隔离 | app 代码中未发现 `Average_score / Rater_A / exp.xls / exp.sav` 引用；分布工件无任何评分字段 |

**结论**：评分关联已建立，仅用于评估就绪，评分未进入学习者端语料智能，声明成立。

---

## D2 重复策略（effective_sample_excludes_non_canonical_duplicate_members）— **APPROVED_WITH_CONDITIONS**

### 数据核对结果

- duplicate_report.csv：348 个重复组 × 2 成员 = 696 条成员记录，组内 n 与成员数全部一致，字符串级互不重叠。
  分组按 scope 分布：weccl_raw 127 组、weccl_lemma 117 组、weccl_tagged 104 组；组规模全部为 2。
- 文档级（按实现路径 `Path(member).stem` 归一化后）：受影响的唯一物理文档恰为 **240 篇**
  （= 230 篇 raw-scope + 10 篇仅见于 lemma/tagged scope），与政策"240 篇受影响"一致。
- 规范代表：实现按组取字典序最小 document_id（stem 级），120 个有效组各 2 篇 → 120 篇规范成员、120 篇非规范成员。
- 参照成员资格：120/120 规范成员全部进入 reference_group_membership.csv（raw_usable 全部为 yes）；
  非规范成员 0 泄漏（字符串级与文档级均为 0）。
- 物理计数与原始记录保留：240 篇受影响文档全部仍存在于 corpus_manifest.csv；与带分 EXP 文档 0 重叠。
- 评估保护联动：holdout_candidates.csv 中 `duplicate-group member` 恰为 240 行，且与该 240 篇物理文档一一对应，全部 CANDIDATE。

### 发现的口径问题（条件 1）

duplicate_report.csv 存在 scope 级冗余：240 篇受影响文档中有 232 篇出现在 ≥2 个 scope 的重复组中
（200 篇同时出现在 raw/lemma/tagged，24 篇在 lemma+raw，8 篇在 lemma+tagged）。
实现通过 `Path(member).stem` 归一化 + 确定性 last-wins 折叠为每文档至多一个组（120 组）。
因此 03 文档所述"each document maps to at most one group"仅在文档级（路径/扩展名归一化）折叠模型下成立，
对原始 CSV 的字面表述不成立。行为结果正确（240 受影响、120 排除、120 保留、0 泄漏），但政策文字需明确该折叠规则。

---

## D3 评估保护（270 篇带分说明文整体保护块）— **APPROVED**

### 数据核对结果

- holdout_candidates.csv：511 行 = 270（scored expository subset）+ 240（duplicate-group member）
  + 1（corrupt variant，WARG2081 raw/lemma NUL），protection_status 全部为 CANDIDATE。
- 270 篇带分 EXP 文档全部在保护候选内（reason 明确标注"270 texts with rater scores - high-value evaluation candidate"）。
- 重复组成员与带分文档 0 重叠；240 篇重复组成员全部进入保护候选，杜绝跨 dev/eval 拆分。
- Stage 5 未创建最终分区：l2/data 中无 train/dev/test/split/partition 工件；1050 条分布记录无任何分区字段。
- 说明：270 篇 EXP 文本以原始文本特征身份参与参照组（参照成员共 1,890 行，分布于 7 个组），
  属描述性、research_only 参照统计（learner_exposure=research_only），不含评分值，与"保护块不用于开发/评估"不冲突。

---

## D4 最小 N（min-N=30）与回退层级 — **APPROVED_WITH_CONDITIONS**

### 数据核对结果

- 获批组数：reference_group_membership.csv 恰为 **75 组**，有效规模最小值为 **30**
  （唯一恰为 30 的组：`RG-prompt_id=ARG01-timed_status=untimed`），无任何组低于 30。
- 分布工件：reference_distributions.jsonl 恰为 1,050 条 = 75 组 × 14 特征，全部 `availability=available`；
  每条均记录 `duplicate_policy=effective_sample_excludes_non_canonical_duplicate_members`；
  组集合与成员表一致；`n_effective == 成员表规模`（0 不一致）；`n_effective <= n_raw` 全部成立。
- ARG13（n_raw=14）/ ARG19（n_raw=18）：清单中 14/18 篇全部 raw_usable=yes；
  不作为独立获批分布（成员表与分布中无 `RG-prompt_id=ARG13/ARG19` 组）；
  其文档参与 11 个更宽组（genre=argumentative、grade 1/2/3、entry_year 2005/2006/2007、
  major_type 两种、timed/untimed），合计 32 篇文档 160 条成员记录。
  运行时索引会为 ARG13/ARG19 创建 availability=unavailable 的独立组，查询经缺失分布触发 CorpusUnavailableError，行为符合政策。
- 回退层级（代码只读核对，app/corpus/groups.py::resolve）：候选顺序
  prompt+timed → prompt → genre+timed → genre → 抛 `CorpusUnavailableError`（即 UNAVAILABLE），与 04 政策一致；
  genre 缺省由 prompt 前缀推导（ARG→argumentative，否则→expository）；未知组 id 抛 `CorpusInvalidRequestError`。
- 披露：每个查询结果含 `requested_reference_group / resolved_reference_group / fallback_disclosure`，
  实际使用组必然披露，silent broadening 在构造上不可能。
- 一致性复算：按 groups.py 语义（manifest + duplicates 折叠）复算 75 组 n_effective，与成员表工件 100% 一致；
  n_raw 与清单计数全部一致。
- 缺失值处理：WARG2081（raw_usable=no，唯一不可用文档）进入 7 个组的成员表，
  其缺失特征按分布披露（100 条记录 n_missing>0，最大 n_missing=2，validity_flags 标注 "missing values: k of n"）；
  完整案例下限 min(n_effective − n_missing) = 30，无任何分布低于 30，与 04"高缺失特征额外标注"承诺一致。

### 发现的口径问题（条件 2）

04_REFERENCE_GROUP_POLICY.md 第 24-25 行写"75 groups: 27 prompt groups … plus 33 prompt x timed"。
实测获批组构成：**25 个 prompt-only + 35 个 prompt×timed + 2 genre + 2 timed + 2 major_type + 4 grade + 5 entry_year = 75**。
"27"把 ARG13/ARG19 两个不可用独立组计入；"33"与实际的 35 个获批 prompt×timed 不符。总数 75 正确，但分解口径需修正。

---

## 条件清单（不阻塞，文档口径修正）

1. **（D2）** 更新 03_SCORE_DUPLICATE_EVALUATION_POLICY.md：明确重复组为文档级定义
   （按 `Path(member).stem` 归一化 document_id；raw/lemma/tagged 多 scope 重复证据确定性折叠为一组、
   last-wins），使"each document maps to at most one group"与 duplicate_report.csv 的多 scope 冗余表述不再冲突。
2. **（D4）** 修正 04_REFERENCE_GROUP_POLICY.md 组构成分解：75 组 = 25 prompt-only + 35 prompt×timed
   （+ 2 genre、2 timed、2 major_type、4 grade、5 entry_year），删除"27 prompt groups / 33 prompt x timed"表述；
   可注明 ARG13/ARG19 独立组在索引中存在但为 unavailable、不属获批组。

---

## 对 min-N 与回退层级的评审意见

- **min-N=30**：作为描述性百分位稳定性的保守下限是合理的，且已在工件层面强制生效
  （有效样本最小 30；完整案例下限亦为 30）。同意其定位为探索性下限而非规范性充分性声明，
  并建议后续按分布持续披露缺失（现行 validity_flags 机制已满足）。非阻塞性建议：组元数据可增加
  complete-case N（n_effective − n_missing）字段，便于下游区分有效样本与完整案例样本。
- **回退层级**：层级顺序正确且确定性实现，请求组/实际解析组/回退披露三者随每次查询结果返回，
  满足"结果必须披露实际使用组"的要求。非阻塞性建议：fallback_disclosure 目前返回请求候选组 id
  字符串，可补充人类可读的回退原因（如 "prompt+timed 组有效样本 < 30"）以增强可审计性。

---

## 风险与备注（无阻塞项）

- 已核实的说明性伪影与限制均如实披露：exp.xls 的 OLE2 SSCS 警告与文档一致；WARG2081 缺特征已在分布中标注。
- 佐证（非四项决策范围）：11 个清单文件复合 SHA-256
  `0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9` 与 corpus_version.json 记录一致，
  资源登记口径闭合。
- 本记录基于工件与代码的只读核对；未在原生 Excel 中重开/重算（评分关联仅做读入核对），
  该限制不影响四项治理决策结论。

---

## 审批结论汇总

| 决策 | 结论 |
| --- | --- |
| D1 评分关联 | **APPROVED** |
| D2 重复策略 | **APPROVED_WITH_CONDITIONS**（条件 1） |
| D3 评估保护 | **APPROVED** |
| D4 min-N 与回退 | **APPROVED_WITH_CONDITIONS**（条件 2） |
| 总体 | **APPROVED_WITH_CONDITIONS**（2 项文档口径条件，无数据/代码改动要求） |

评审员：Stage 5 研究方法/方法论评审（fresh reviewer） 2026-08-07
