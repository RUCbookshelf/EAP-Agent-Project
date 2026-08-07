# Post-Fix 独立复核报告（fresh reviewer）

* 复核角色：独立 post-fix 复核员（deepseek-v4-flash；未参与任何修正编辑）
* 复核日期：2026-08-07
* 复核范围：`docs/corpus-readiness/sweccl2/`（报告 00-12、evidence、data、corpus_version.json）与 `scripts/corpus_readiness/`
* 复核原则：只做验证与报告；未改动任何文件（唯一写入为本报告）。每个数值判定均与机器工件/实际脚本目录交叉核对。
* 测试运行时：`A:\EAP Agent Project\tmp\corpus-readiness-venv\Scripts\python.exe`（Python 3.12.13，本次可运行）

## 逐项判定表

| Finding | 判定 | 证据 | 验证命令与结果 |
| --- | --- | --- | --- |
| F1 SECCL 中文转写注释计数（29 改为 12 物理文件 / 6 唯一转写） | RESOLVED | `quality_issues.csv` 中 `chinese_annotator_note_in_transcript` 恰 12 行；唯一转写 ID 恰 6 个（04-110-04A、04-128-22B、05-010-19A、05-010-25B、05-023-02B、06-007-07A）；06 表列 N=12，11/12 均写 "12 files / 6 unique transcripts"；00-12（不含 evidence 历史节）无 "29 SECCL/29 个转写" 活动残留 | `Import-Csv quality_issues.csv | Group-Object issue_type` 结果 chinese_annotator_note_in_transcript=12；文件名去重后唯一数=6；`Select-String '29 SECCL|29 个转写|29 transcript'` 0 命中 |
| F2 二进制/PDF 计数（2,153 vs 枚举 2,154） | RESOLVED | `physical_inventory.csv` 实测 `needs_review=2,153`、pdf=1（TOOLS/User Guide.pdf，294,003 B）；02 枚举 2,139 mp3 + 8 exe + 1 pdf + 2 doc + 1 avi + 1 sav + 1 xls = 2,153 自洽；发现快照含手册 PDF（15,126,818 B，sha256 28dee8c39a46c6ca...），当前清单不含；`corpus_version.json` 明确区分快照与当前状态 | needs_review 组按扩展名分组：.mp3 2139/.exe 8/.doc 2/.sav 1/.xls 1/.avi 1/.pdf 1，合计 2,153；快照 .pdf 行含手册 PDF；`Compare-Object` 快照与当前仅差该 PDF 与概况报告.md 一对文件 |
| F3 cp1250/cn_detect 字段语义 | RESOLVED | `physical_inventory.csv` 中 WARG2730/WARG4140（LEMMA）`detected_encoding=cp1250` 且 `encoding_status=cn_detect`；`derived_manifest.csv` 同 2 文件 `encoding=cp1250`；03 已新增 Terminology note 明示两字段语义（值 vs 检测路径）；机器标签未改动 | 两字段并置过滤恰 2 行、同一文件对；`derived_manifest.csv` encoding=cp1250 恰 2 行；git 检查 data/ 零改动 |
| F4 管线数（"9-step" 改为 01-10 + run_all 编排） | RESOLVED | 脚本目录实计 10 个脚本（01-10）+ run_all.py + README.md + tests；`run_all.py` 的 STEPS 恰为 01-09；00 精确表述 "scripts 01-10；run_all.py orchestrates steps 01-09；10_version.py emits version record"；README 已补 10_version 说明与表格行；全目录 "9-step"/"9 step" 仅存在于 evidence 评审历史节 | `Get-ChildItem scripts\corpus_readiness` 列出 01-10 共 10 个脚本 + run_all.py；`run_all.py` STEPS 列表 9 项；`Select-String '9-step|9 step'` 仅 evidence/independent_review.md 3 处历史提及 |
| F5 许可表述一致性 | RESOLVED | 00、01、11、12、`corpus_version.json` 五处均表达 `PARTIALLY_DOCUMENTED` + 外部/学习者端使用 `REQUIRES_REVIEW`；11 已有独立 "License status" 节复述字段值 | 五文件全文比对；`corpus_version.json` `license_status` 字段值读取一致 |

## NEW_CONCERN 清单

无。

## 非阻塞观察（不构成 NEW_CONCERN，不影响判定）

* 06 报告的质量表列 `chinese_annotator_note_in_transcript = 12`（与 CSV 一致），但未在正文中复述 "6 unique transcripts" 的分解；该分解由 11/12 显式给出并经 CSV 唯一 ID 计数（6）机器核验。属文档详略差异，无事实错误、无残留误述。

## 收口完整性核验（验收标准 3-5）

* 历史保留：`evidence/independent_review.md` 含 "评审发现（历史记录，保持可审计）" 节，5 项原始发现全部保留原文描述；含决议表、Post-fix verification statement（"No review-layer documentation finding remains open"）。
* 过期建议：对 "维护门/maintenance gate/下次维护/待修/未修复/尚未修复/后续修/to be fixed/pending fix" 等短语全包扫描 0 命中，无"建议下个维护门再修"类过期建议。
* 真实语料限制未被误标为已解决：TEM8 缺失、WARG2081 RAW/LEMMA 全 NUL 损坏、240 重复组、ARG13(N=14)/ARG19(N=18) 过稀、许可 PARTIALLY_DOCUMENTED、270 篇评分说明文整体保护，全部仍见于 ONGOING CORPUS LIMITATIONS 节，且该节明确"不得视为已解决"；11/12/00/corpus_version.json 同步可见。
* 机器可读工件未被本次收口改动：`git -C writing-feedback-mvp status --porcelain` 中 `data/` 与 `corpus_version.json` 零改动；tracked `git diff --stat` 仅 .md 文档（00、03、evidence、scripts/corpus_readiness/README.md）外加工作区既有用户改动（AGENTS.md、RUN_VERIFICATION_V0.7.md、RUN_VERIFICATION_V0.8.2.md）。包基线为提交 93222b3，02/06/11/12 的正确内容已在基线中。
* 聚焦测试：`python -m pytest scripts/corpus_readiness/tests -q` 实跑 8 passed（1 条 pytest 缓存目录权限警告，与测试结果无关），与收口声明一致。

## 最终结论

POST-FIX DOCUMENTATION CONSISTENCY PASS

全部 5 项发现（F1-F5）均判定 RESOLVED，无 NEW HIGH/BLOCKING 问题；历史记录保留完整、无过期建议、真实语料限制未被误标为已解决、机器可读工件未因收口被改动、聚焦测试 8/8 通过。
