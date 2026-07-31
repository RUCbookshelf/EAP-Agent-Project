# UI Design v0.9.1

## Information architecture

The v0.9.1 interface uses role-based navigation with two primary modes selected from the sidebar.

### Student View (6 pages)

1. **Home** — Current writing task summary, latest submission status, feedback availability, revision priority, available practice, next recommended action.
2. **Writing** — Submission form with grouped sections: Task Information, Timing (optional), Tools Used, Essay Text. Supports new independent tasks and revisions.
3. **Feedback** — Strengths (verified positive findings only), up to 2 revision priorities with plain-language titles, evidence quotes, and actionable suggestions. No raw metric values in main feedback.
4. **Revision** — Source draft selection, previous feedback review, draft chain, first-to-latest changes, previous priorities, uptake candidates with conservative attribution.
5. **Practice** — Current Practice Target, exercise instructions, constraints, response input, attempt submission, attempt history. Empty responses rejected.
6. **Learning Journey** — Chronological observable events timeline: submission, feedback, practice availability, attempts, revision responses, later-task evidence.

### Research View (6 pages)

1. **Overview** — System status, provider configuration, data-quality warnings.
2. **Evidence** — Submission details, analysis runs, diagnosis, calibration audit.
3. **CALF Measures** — Grouped metric cards by construct (Lexical, Syntactic, Fluency) with status, confidence, limitations. Accuracy and Sophistication shown as Unavailable.
4. **Learning Process** — Complete evidence chain: Practice Targets, Engagement Traces, Transfer Evidence.
5. **Research Data** — 8 subsections: Export Preview, Privacy Mode, Dataset Filters, PII Scan, Human Review, Dataset Split, Data Quality, Export History.
6. **System Audit** — Diagnostic audit, Learner Model audit, Reanalysis, Local Administration.

## Progressive disclosure

- Student View hides: analyzer versions, metric IDs, Evidence IDs, confidence calculations, Diagnostic Gate internals, database identifiers, configuration versions, provider error details.
- Research View exposes all technical records.
- Role switching is local-only (no authorization layer).

## Reusable components

- `page_header(title, subtitle)` — consistent page headers
- `status_badge(status)` — colored status indicators
- `metric_card(metric_id, value, status, ...)` — CALF metric display
- `evidence_quote(text)` — quoted evidence spans
- `limitation_notice(text)` — consistent warning boxes
- `empty_state(title, explanation)` — informative empty states
- `timeline_event(label, timestamp, ...)` — Learning Journey events
- `audit_record(id, label, data)` — expandable research records
- `feedback_priority_card(...)` — student-facing priority cards

## Visual design

- Restrained academic palette with accessible contrast
- Responsive CSS: font scaling at <640px, word-wrap on alerts, blockquote styling
- Desktop (1280+), tablet (768+), and mobile (390x844) verified
- No large frontend framework; Streamlit-compatible CSS only

## Internationalization

- 271 keys in en.json and zh_CN.json (identical sets)
- Language switcher in sidebar; does not trigger analysis, exercise creation, or DeepSeek
- Student essays, exercise responses, quoted evidence, and historical feedback NOT auto-translated

## Accessibility

- Meaningful page headings, descriptive button labels, clear form labels
- Sufficient text contrast, no status conveyed by color alone
- Readable warning and error messages

