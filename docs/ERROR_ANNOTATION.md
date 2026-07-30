# Error Annotation Foundation v0.8

The append-only schema records stable annotation ID, submission and exact offsets, original span, optional correction, category, source, status, annotator, timestamp, guideline version, confidence, and adjudication status. Import rejects offsets beyond the essay and text that does not exactly match the stored span.

Allowed sources are `human`, `imported_corpus`, `automatic_candidate`, `external_tool`, and `llm_candidate`. Only confirmed `human` or `imported_corpus` annotations are eligible inputs. Even then, v0.8 reports that manually specified measures require validated denominators; it does not manufacture an Accuracy value. With no eligible evidence, value is `null` and status is unavailable, never zero.
