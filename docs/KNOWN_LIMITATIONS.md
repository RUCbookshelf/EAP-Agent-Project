# v0.8 已知限制

- CALF measures are prototype research evidence and are not validated for the target population.
- MTLD/HD-D remain sensitive to normalization, text length, task, and parameter choices.
- spaCy clause/T-unit and other syntax outputs are candidates, not validated units or formal measures.
- Accuracy and lexical sophistication are unavailable; no fake zero or inferred replacement is allowed.
- WPM requires actual duration and remains a descriptive proxy. No CALF total, writing score, ability/proficiency/CEFR claim, or v0.9 loop is implemented.

- Structured status and local repair improve consistency but do not validate longitudinal measurement or educational usefulness.
- Risky positive-finding phrases are an auditable allowlist-style heuristic; semantically equivalent overclaims may still require human review.
- Provider status describes execution and validation, not feedback quality.
- Within-task trajectory uses deterministic text/metric/diagnosis comparisons and cannot establish revision quality, learning, or feedback causation; major rewrites reduce attribution confidence.
- Student/Research views are presentation modes, not authentication or authorization boundaries.

- Task clustering uses transparent metadata classes, not validated semantic task equivalence.
- Representative-draft rules are workflow assumptions; different strategies can change the displayed evidence set.
- Two-point comparisons are not trends. Three/four-point directions remain provisional; five-point labels remain descriptive only.
- Metric trajectories do not standardize for prompt difficulty, instruction, interval, genre effects, or external learning.
- Diagnostic trajectories inherit analyzer, gate, evidence and rule limitations. “Persistent” names repeated observations, not a stable learner trait.
- Strength patterns are conservative verified text-feature recurrences, not general strengths or mastery.
- History Evidence provides lineage but does not prove validity or causality.
- No CALF, T-unit, grammar-error total, CEFR, proficiency score, overall score, cloud deployment, paid embedding service, or v0.8 functionality is included.

## Retained v0.6.1 limitations

- Metric and diagnosis confidence are transparent engineering heuristics, not validated probabilities.
- Repetition, necessary-task-term, local-cluster, priority, and exercise thresholds are working assumptions awaiting literature and human-coded calibration.
- `necessary_task_term` uses conservative lexical/distributional rules, not semantic certainty or embeddings.
- Connective evidence is limited by a curated dictionary and explicit locations; implicit cohesion is not measured.
- spaCy dependency and morphology outputs remain parser candidates. They are not true clause, T-unit, CALF, or grammar-error counts.
- Evidence relevance uses category-specific deterministic checks and can miss valid pedagogical interpretations.
- A zero-priority response means automatic evidence was insufficient, not that the draft has no issues.

v0.6 图表只是已有自动信号的透明展示，不增加测量效度。配置管理没有身份认证、权限隔离或多租户能力，只适合本地研究。参数验证检查类型、范围和资源兼容性，不代表阈值已有文献或实验支持。重分析可比较算法版本，但不会使旧结果自动变得可比。CALF 扩展目前只有接口，不含完整 CALF、总分、CEFR 或准确性定论。

修订对齐采用本地表层相似度，并非语义等价判断。split/merge、major rewrite 和可比性阈值都是工作假设。一次未观察到诊断信号不表示问题已经解决或掌握。反馈采纳候选只记录可观察一致性，不能证明反馈导致修改。Analyzer/Diagnosis 版本不兼容时禁止直接比较，仍须人工审核。

> v0.4 补充：默认 spaCy 分析改善了定位和可追溯性，但没有把自动解析变成已验证测量。学习者拼写、非标准语法、代码转换和异常标点都可能导致 lemma/POS/dependency/noun chunk 错误。连接词资源不完整；未检测不等于没有衔接。MATTR 窗口 50、局部重复窗口 30 和长句阈值 30 都是工作假设。题目关键词降权也可能遗漏必要术语或错误降权。

## 分析

- 英文词与句子通过正则表达式识别，缩写、特殊标点、代码转换和非标准拼写可能被误分。
- 连接词只统计一个短列表，未统计隐性衔接或同义表达。
- `repeated_content_words` 只按表层词形和固定停用词表计算，不做词形还原或语境判断。
- TTR 强烈受文本长度影响；平均句长也不能代表句法复杂度或句长变化。
- 这 8 个指标不是完整 CALF，更不是学生能力测量。

## 诊断与反馈

- 阈值是工作假设，未通过教育实验验证。
- 诊断只提示可能值得关注的表层模式，不评价“语法能力差”等能力结论。
- LocalDemo 是确定性模板，不理解全文论证质量；外部 LLM 也可能产生不准确或不适当建议。
- Pydantic 保证结构，不保证教学内容正确。教师仍需审核。
- 本次真实 DeepSeek 两次提交验证只证明接口、结构约束、历史证据绑定和持久化链路可运行，不证明反馈具有教学效度、评分效度或跨任务稳定性。

## 历史

- 可比性只匹配 `genre`、`timed` 和 `tool_use`，没有控制题目难度、时间长度、教学干预或写作目的。
- 一条可比历史即可生成描述性对比，但绝不构成真实能力趋势证据。
- 没有可比历史时明确显示“数据不足，无法判断趋势。”；不可比记录不会被强行合并。

## 工程与部署

- SQLite 适合单机原型，不适合高并发或多租户生产环境。
- 尚无认证、授权、加密、备份、数据保留/删除、审计面板或数据库迁移框架。
- 外部 Provider 会接收作文文本、指标、诊断和历史摘要。真实部署必须完成知情同意、脱敏、服务条款和跨境数据合规评估。
- Streamlit 是原型界面，不是商业级微信小程序。
- FastAPI、Streamlit 和 SQLite 目前都运行在同一台本地电脑；“云就绪”不等于已经部署云端。
- PostgreSQL Repository、认证授权、TLS、速率限制、任务队列、微信小程序和云运维均未实现。
- v0.3 可比较性、最小样本、方向、波动性、置信度和问题轨迹阈值均为可替换的原型规则，尚未由应用语言学文献或实证数据校准。
- 线性斜率按作文序号而非连续时间建模；当前不控制教学干预、任务难度、评分者、文本质量或外部学习经历。
- `medium` 只是较强的原型证据标签，不是统计显著性、测量信度或效度；系统不输出 `high`。
- `recently_reduced` 只表示结构化诊断在最近窗口暂未出现，不表示问题解决、掌握或真实能力提升。


## v0.9.1 UI Limitations

- Streamlit AppTest-based integration tests are skipped; UI verification uses Playwright.
- The sidebar navigation uses Streamlit radio groups which reload on every interaction; session state persists results but rerenders the page.
- Mobile layout is verified at 390x844 but some Streamlit components may not fully adapt to very narrow viewports.
- The CSS is Streamlit-compatible only; no custom JavaScript or large frontend framework is used.

## v0.9.2.1 Pixel Art UI Limitations

- Streamlit primary buttons (st.button) retain a framework-controlled 1px border
  that cannot be fully overridden by application CSS without breaking the button.
- Streamlit radio options on mobile render inside a collapsed sidebar overlay;
  the sidebar must be opened via the hamburger control before labels become
  reachable. This is standard Streamlit mobile behavior, not an application defect.
- Streamlit tab headers partially respect application CSS overrides; bottom-border
  thickness (4px) and active-tab indicator (red 4px) are applied, but internal
  padding and border-radius may differ from the canonical Pixel Art design.
- The `border-collapse: collapse` on table cells uses 1px internal grid lines
  inside `.px-table-wrap` containers; these are documented structural data-grid
  elements, not primary Pixel Art components.
- On narrow viewports (390x844), the sidebar content height can exceed the viewport
  when all 8-10 radio options are visible. Scrollable overlay behavior is inherent
  to Streamlit mobile rendering.
- Focus outline color on text inputs correctly applies `#29adff` (3px solid) when
  inputs are directly focused; browser-managed focus rings on other interactive
  elements (links) use default Streamlit styling.
- Computed-style audit for primary components confirmed zero border-radius, no
  gradients, no blur, no soft shadows, zero transition duration, and no animations
  across text inputs, textareas, expanders, and alert notices.

## v0.9.3-B Error-Handling Limitations

- Error-category operation identifiers in Student/Research suffixes are English
  code identifiers (e.g., practice_targets), not localized descriptions.
- Automatic retry is limited to GET requests; a genuinely interrupted write
  requires a manual retry and the user is told the earlier request may have
  already succeeded.
- dataset-split is a deterministic computation without persistence (no table
  exists; no schema change permitted in this stage).
- On narrow mobile viewports the first Research Data tabs require horizontal
  scrolling of the Streamlit tab bar.
- Requests rejected with 429 (provider rate limiting) share the
  backend_processing_error fallback when no canonical body is present.
