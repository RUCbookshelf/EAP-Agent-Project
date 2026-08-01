"""Student View pages for the writing-feedback-mvp Pixel Art interface.

All pages use progressive disclosure: students see only what they need
to understand feedback and take action. Internal IDs, analyzer versions,
and raw metrics are hidden.

Pixel Art v0.9.2: square corners, hard shadows, solid colors, monospace.
"""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError, WritingFeedbackApiClient
from app.ui.components import (
    render_api_error,
    card_group_header,
    empty_state,
    error_box,
    evidence_quote,
    feedback_priority_card,
    field_error,
    info_box,
    limitation_notice,
    page_header,
    section_header,
    success_box,
    technical_caption,
    timeline_event,
    validate_writing_form,
    warning_box,
)
from app.ui.locale import t


def render_student_home(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Home: task summary, latest status, next action."""
    page_header("student_home_title", "student_home_subtitle", lang)

    from app.ui.student_context import set_selected_learner, student_id_input

    student_id = student_id_input("student_id", "home_student", lang, placeholder_key="student_id_placeholder")
    set_selected_learner(student_id)

    if not student_id.strip():
        info_box("student_home_enter_id", lang)
        return

    try:
        with st.spinner(t("journey_loading", lang)):
            journey = api_client.get_journey(student_id.strip())
            targets = api_client.get_practice_targets(student_id.strip())
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return

    section_header("student_home_current_task", lang)
    counts = journey.get("counts") or {}
    if int(counts.get("submissions") or 0) == 0:
        st.write(t("student_home_no_submissions", lang))
    else:
        active = [t for t in targets if t.get("status") == "active"]
        completed = [t for t in targets if t.get("status") == "completed"]
        st.markdown(
            f'<div class="px-card">'
            f'<strong>{t("student_home_submissions", lang)}: {counts.get("submissions")}</strong><br>'
            f'{t("student_home_feedback_count", lang)}: {counts.get("feedback_records")} &middot; '
            f'{t("student_home_priority_count", lang)}: {counts.get("selected_priorities")}<br>'
            f'{t("student_home_active_targets", lang)}: {len(active)} &middot; '
            f'{t("student_home_completed_targets", lang)}: {len(completed)}'
            f'</div>',
            unsafe_allow_html=True,
        )

    section_header("student_home_latest_status", lang)
    events = journey.get("events", [])
    if events:
        latest = events[-1]
        st.markdown(
            f'<div class="px-card">'
            f'<strong>{t(latest.get("title_key", ""), lang)}</strong><br>'
            f'<span style="font-size:0.85rem;color:var(--px-muted);">{_short_timestamp(latest.get("occurred_at", ""))}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        state = journey.get("state") or "no_submissions"
        state_messages = {
            "no_submissions": "journey_empty_no_submissions_title",
            "submission_without_analysis": "journey_empty_no_analysis_title",
            "analysis_without_priority": "journey_empty_no_priority_title",
            "feedback_no_practice_target": "journey_empty_no_target_title",
            "target_no_attempt": "journey_empty_no_attempt_title",
            "attempt_no_evaluation": "journey_empty_no_evaluation_title",
            "revision_no_response": "journey_empty_no_revision_title",
        }
        st.write(t(state_messages.get(state, "student_home_no_events"), lang))

    section_header("student_home_next_action", lang)
    state = journey.get("state") or "no_submissions"
    action_map = {
        "no_submissions": "student_home_action_submit",
        "submission_without_analysis": "student_home_action_continue",
        "analysis_without_priority": "student_home_action_continue",
        "feedback_no_practice_target": "student_home_action_continue",
        "target_no_attempt": "student_home_action_practice",
        "attempt_no_evaluation": "student_home_action_practice",
        "revision_no_response": "student_home_action_revise",
        "journey_events": "student_home_action_continue",
    }
    info_box(action_map.get(state, "student_home_action_continue"), lang)

    limitation_notice("student_home_boundary", lang)


# ---------------------------------------------------------------------------
# Writing page
# ---------------------------------------------------------------------------

def render_writing_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Writing page: submission form with clear field grouping."""
    page_header("student_writing_title", "student_writing_subtitle", lang)

    from app.ui.student_context import set_selected_learner, student_id_input

    student_id = student_id_input("student_id", "writing_student", lang, placeholder_key="student_id_placeholder")
    set_selected_learner(student_id)

    st.radio(
        t("task_relationship", lang),
        [t("task_new_independent", lang), t("task_revision_within", lang)],
        key="writing_task_relationship",
        help=t("task_revision_help", lang),
    )
    is_revision = st.session_state.get("writing_task_relationship") == t("task_revision_within", lang)

    if is_revision:
        draft_stage = st.selectbox(t("draft_stage", lang), [t("draft_revised", lang), t("draft_final", lang)])
    else:
        draft_stage = st.selectbox(t("draft_stage", lang), [t("draft_first", lang), t("draft_independent", lang)])

    revision_of_submission_id = None
    candidates = []
    if student_id.strip():
        try:
            candidates = api_client.get_student_revision_candidates(student_id.strip()).get("candidates", [])
        except ApiClientError:
            candidates = []

    if is_revision:
        labels = {
            f"Essay #{item['essay_id']} | {item['submitted_at']} | {item['draft_stage']} | {item['writing_prompt'][:80]}": item["essay_id"]
            for item in candidates
        }
        if labels:
            selected = st.selectbox(t("student_writing_select_revision", lang), list(labels))
            revision_of_submission_id = labels[selected]
            info_box("student_writing_revision_note", lang)
        else:
            warning_box("student_writing_no_candidates", lang)
            return

    with st.expander(t("student_writing_task_info", lang), expanded=True):
        writing_prompt = st.text_area(t("writing_prompt", lang), height=80, key="writing_prompt_input")
        genre = st.selectbox(
            t("genre", lang),
            [t("genre_argumentative", lang), t("genre_expository", lang), t("genre_narrative", lang)],
        )

    with st.expander(t("student_writing_timing", lang), expanded=False):
        timed = st.checkbox(t("timed_writing", lang))
        time_limit_minutes = None
        active_duration_seconds = None
        if timed:
            time_limit_minutes = st.number_input(
                t("time_limit_minutes", lang), min_value=1, max_value=1440, value=30,
                help=t("time_limit_help", lang),
            )
            active_duration_seconds = st.number_input(
                t("active_duration_seconds", lang), min_value=0, max_value=86400, value=0,
                help=t("active_duration_help", lang),
            )
        timing_source = st.selectbox(
            t("timing_source", lang),
            ["unknown", "client_timer", "server_timestamp", "manual_report", "imported"],
            disabled=not timed,
        )
        timing_quality = st.selectbox(
            t("timing_quality", lang),
            ["unavailable", "verified", "estimated", "self_reported", "incomplete"],
            disabled=not timed,
        )
        unexplained_interruption = st.checkbox(t("unexplained_interruption", lang), disabled=not timed)

    with st.expander(t("student_writing_tools", lang), expanded=False):
        tool_use = st.text_input(
            t("tool_use", lang), value="none",
            help=t("tool_use_placeholder", lang),
        )

    st.subheader(t("essay_text", lang))
    essay_text = st.text_area(
        t("essay_text", lang), height=300, key="writing_essay",
        label_visibility="collapsed",
    )

    if not st.button(t("submit_button", lang), type="primary", use_container_width=True):
        saved = st.session_state.get("submission_result")
        if saved:
            success_box(t("submission_saved", lang, id=saved.get("submission_id", "?")), lang)
            with st.expander(t("student_writing_previous", lang)):
                render_feedback_content(saved, api_client, lang)
        return

    validation_errors = validate_writing_form(
        student_id,
        writing_prompt,
        essay_text,
        is_revision=is_revision,
        revision_of_submission_id=revision_of_submission_id,
    )
    if validation_errors:
        for error_key in validation_errors:
            field_error(error_key, lang)
        return

    try:
        submission = {
            "student_id": student_id,
            "writing_prompt": writing_prompt,
            "genre": genre,
            "draft_stage": draft_stage,
            "timed": timed,
            "time_limit_minutes": int(time_limit_minutes) if timed and time_limit_minutes else None,
            "active_writing_duration_seconds": float(active_duration_seconds) if timed and active_duration_seconds and active_duration_seconds > 0 else None,
            "timing_source": timing_source if timed else "unknown",
            "timing_quality": timing_quality if timed else "unavailable",
            "unexplained_interruption": bool(unexplained_interruption) if timed else False,
            "tool_use": tool_use,
            "essay_text": essay_text,
            "revision_of_submission_id": revision_of_submission_id,
        }
        with st.spinner(t("student_writing_submitting", lang)):
            result = api_client.submit(submission)
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return
    except Exception:
        st.error(t("submission_error", lang))
        return

    result["ui_submission"] = {"draft_stage": draft_stage}
    st.session_state["submission_result"] = result
    success_box(t("submission_saved", lang, id=result.get("submission_id", "?")), lang)
    render_feedback_content(result, api_client, lang)


# ---------------------------------------------------------------------------
# Feedback content (shared, student-safe)
# ---------------------------------------------------------------------------

def render_feedback_content(result: dict, api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Render student-safe feedback content."""
    provider = result.get("feedback_result", {})
    feedback = provider.get("feedback", {})
    empty_states = set(result.get("ui_empty_states") or [])

    technical_caption(
        f"Essay #{result.get('submission_id', '?')} | "
        f"{result.get('ui_submission', {}).get('draft_stage', '')}"
    )
    technical_caption(f"{t('provider_label', lang)}: {provider.get('provider_name', '')}")

    section_header("student_feedback_strengths", lang)
    pf = feedback.get("positive_finding", {})
    if pf:
        st.write(pf.get("explanation", ""))
        if pf.get("evidence_quote"):
            st.caption(f'"{pf["evidence_quote"]}"')
    else:
        info_box("student_feedback_no_strengths", lang)

    section_header("student_feedback_priorities", lang)
    priorities = feedback.get("priority_feedback", [])
    if "NO_SELECTED_PRIORITY" in empty_states or not priorities:
        empty_state("student_feedback_no_priority_title", "student_feedback_no_priority_desc", lang)
    else:
        shown = 0
        for item in priorities[:2]:
            feedback_priority_card(
                category=item.get("category", ""),
                evidence_quote_text=item.get("evidence_quote", ""),
                explanation=item.get("explanation", ""),
                revision_guidance=item.get("revision_guidance", ""),
                lang=lang,
            )
            shown += 1
        if shown == 0:
            empty_state("student_feedback_no_priority_title", "student_feedback_no_priority_desc", lang)

    section_header("student_feedback_evidence", lang)
    exercises = feedback.get("exercises", [])
    if exercises:
        for ex in exercises:
            st.markdown(
                f'<div class="px-card">'
                f'<strong>{ex.get("exercise_type", "").replace("_", " ").title()}</strong><br>'
                f'{ex.get("instructions", "")}'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        info_box("student_feedback_no_exercise", lang)

    section_header("student_feedback_next", lang)
    if priorities:
        info_box("student_feedback_next_revise", lang)
    else:
        info_box("student_feedback_next_continue", lang)

    uncertainty = feedback.get("uncertainty_note", "")
    if uncertainty:
        limitation_notice(uncertainty, lang)


# ---------------------------------------------------------------------------
# Feedback page (standalone)
# ---------------------------------------------------------------------------

def render_feedback_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Feedback page: strengths, priorities, evidence, next step."""
    page_header("student_feedback_title", "student_feedback_subtitle", lang)

    result = st.session_state.get("submission_result")
    if not result:
        info_box("student_feedback_no_result", lang)
        return

    render_feedback_content(result, api_client, lang)


# ---------------------------------------------------------------------------
# Revision page
# ---------------------------------------------------------------------------

def render_revision_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Revision page: source draft, diff, observations."""
    page_header("student_revision_title", "student_revision_subtitle", lang)

    result = st.session_state.get("submission_result")
    if not result:
        info_box("student_revision_no_result", lang)
        return

    trajectory = result.get("within_task_revision_trajectory")
    group_summary = result.get("revision_group_summary")

    if not trajectory:
        info_box("student_revision_no_history", lang)
        return

    section_header("student_revision_chain", lang)
    chain_html = ""
    for item in trajectory.get("draft_chain", []):
        chain_html += (
            f'<div class="px-timeline-node">'
            f'<div class="px-timeline-marker"></div>'
            f'<div class="px-timeline-content">'
            f'<strong>Essay #{item.get("submission_id", "?")}</strong>'
            f'<div style="font-size:0.85rem;color:var(--px-muted);">'
            f'{item.get("draft_stage", "")} &middot; {item.get("submitted_at", "")}'
            f'</div></div></div>'
        )
    st.markdown(chain_html, unsafe_allow_html=True)

    first_latest = trajectory.get("first_to_latest_comparison", {})
    if first_latest:
        section_header("student_revision_changes", lang)
        changes = first_latest.get("token_changes", {})
        st.markdown(
            f'<div class="px-card">'
            f'{t("student_revision_inserted", lang)}: {float(changes.get("inserted_ratio", 0)):.1%}<br>'
            f'{t("student_revision_deleted", lang)}: {float(changes.get("deleted_ratio", 0)):.1%}<br>'
            f'{t("student_revision_modified", lang)}: {float(changes.get("modified_ratio", 0)):.1%}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.caption(t("student_revision_edit_note", lang))

    section_header("student_revision_priorities", lang)
    empty_states = set(result.get("ui_empty_states") or [])
    if "MAJOR_REWRITE_LIMITS_ATTRIBUTION" in empty_states:
        warning_box("student_revision_major_rewrite", lang)
    elif "NO_PREVIOUS_PRIORITY" in empty_states:
        info_box("student_revision_no_previous", lang)
    else:
        for item in trajectory.get("previous_selected_priorities", []):
            st.write(f"- {item.get('category', '').replace('_', ' ').title()}: {item.get('revision_guidance', '')}")

    section_header("student_revision_uptake", lang)
    if "NO_FEEDBACK_UPTAKE_CANDIDATE" in empty_states:
        info_box("student_revision_no_uptake", lang)
    for item in trajectory.get("feedback_uptake_candidates", []):
        st.markdown(
            f'<div class="px-card">'
            f'<strong>{item.get("status", "")}</strong><br>'
            f'<span style="font-size:0.85rem;color:var(--px-muted);">{item.get("observed_change", "")}</span><br>'
            f'<span style="font-size:0.85rem;">{t("student_revision_attribution", lang)}: {trajectory.get("attribution_confidence", "")}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    limitation_notice("student_revision_boundary", lang)


# ---------------------------------------------------------------------------
# Practice page
# ---------------------------------------------------------------------------

def render_practice_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Practice page: target, exercise, attempt, evaluation."""
    page_header("practice", "practice_boundary", lang)

    from app.ui.student_context import set_selected_learner, student_id_input

    student_id = student_id_input("student_id", "practice_student_v2", lang, placeholder_key="student_id_placeholder")
    set_selected_learner(student_id)

    if not student_id.strip():
        info_box("no_active_target", lang)
        return

    if st.button(t("load_practice", lang), key="practice_load"):
        try:
            with st.spinner(t("practice_loading", lang)):
                targets = api_client.get_practice_targets(student_id.strip())
                st.session_state["practice_targets_v2"] = targets
                active = [t for t in targets if t.get("status") == "active"]
                if active:
                    instances = api_client.get_exercise_instances(active[0].get("practice_target_id", ""))
                    if instances:
                        st.session_state["current_exercise_v2"] = instances[-1]
                        st.session_state["exercise_attempts_v2"] = api_client.get_exercise_attempts(
                            instances[-1].get("exercise_id", "")
                        )
                    else:
                        st.session_state.pop("current_exercise_v2", None)
                        st.session_state["exercise_attempts_v2"] = []
        except ApiClientError as exc:
            render_api_error(exc, lang)
            return

    targets = st.session_state.get("practice_targets_v2", [])
    if not targets:
        info_box("no_active_target", lang)
        return

    active_targets = [t for t in targets if t.get("status") == "active"]
    if not active_targets:
        info_box("practice_not_available", lang)
        return

    selected = active_targets[0]

    section_header("practice_target", lang)
    st.markdown(
        f'<div class="px-card">'
        f'<strong>{selected.get("target_label", "")}</strong><br>'
        f'<span style="font-size:0.85rem;color:var(--px-muted);">'
        f'{t("student_practice_source", lang)}: {selected.get("target_code", "")} &middot; '
        f'{t("student_practice_why", lang)}: {selected.get("source_diagnosis_id", "")}'
        f'</span></div>',
        unsafe_allow_html=True,
    )

    exercise = st.session_state.get("current_exercise_v2")
    source_text = st.text_area(
        t("student_practice_source_text", lang), key="practice_source_v2", height=80,
        placeholder=t("student_practice_source_placeholder", lang),
    )
    if not exercise:
        if st.button(t("generate_exercise", lang), key="practice_gen"):
            payload = {"practice_target": selected, "source_text": source_text}
            try:
                exercise = api_client.create_exercise(selected.get("practice_target_id", ""), payload)
                st.session_state["current_exercise_v2"] = exercise
                st.session_state["exercise_attempts_v2"] = []
            except ApiClientError as exc:
                render_api_error(exc, lang)
                return
    else:
        st.caption(t("practice_exercise_loaded", lang))
    if exercise and exercise.get("status") != "practice_not_available":
        constraints_html = ""
        constraints = exercise.get("constraints", [])
        if constraints:
            constraints_html = f'<br><span style="font-size:0.85rem;">{t("exercise_constraints", lang)}: {", ".join(constraints)}</span>'

        st.markdown(
            f'<div class="px-card">'
            f'<strong>{exercise.get("exercise_type", "")}</strong><br>'
            f'{exercise.get("instructions", "")}'
            f'{constraints_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

        response_text = st.text_area(
            t("response_field", lang), key="practice_response_v2", height=100,
            placeholder=t("student_practice_response_placeholder", lang),
        )
        if st.button(t("submit_attempt", lang), key="practice_submit", type="primary"):
            if not response_text.strip():
                st.warning(t("student_practice_empty_response", lang))
            else:
                aid = exercise.get("exercise_id", "")
                payload = {
                    "student_id": student_id,
                    "response_text": response_text,
                    "attempt_number": len(st.session_state.get("exercise_attempts_v2", [])) + 1,
                }
                try:
                    attempt = api_client.submit_exercise_attempt(aid, payload)
                    attempts = st.session_state.get("exercise_attempts_v2", [])
                    attempts.append(attempt)
                    st.session_state["exercise_attempts_v2"] = attempts
                    success_box(t("student_practice_attempt_saved", lang), lang)
                    evaluation = attempt.get("evaluation")
                    if evaluation:
                        st.markdown(
                            f'<div class="px-card">'
                            f'<strong>{t("practice_evaluation_label", lang)}</strong><br>'
                            f'{t("practice_evaluation_completion", lang)}: {evaluation.get("completion_status", "")}<br>'
                            f'{t("practice_evaluation_action", lang)}: {evaluation.get("target_action_status", "")}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        limitations = evaluation.get("limitations") or []
                        if limitations:
                            st.caption(limitations[0])
                except ApiClientError as exc:
                    render_api_error(exc, lang)

    attempts = st.session_state.get("exercise_attempts_v2", [])
    if attempts:
        section_header("attempt_history", lang)
        for a in reversed(attempts):
            st.markdown(
                f'<div class="px-card">'
                f'<strong>{t("exercise_attempt", lang)} #{a.get("attempt_number", "?")}</strong><br>'
                f'<span style="font-size:0.85rem;color:var(--px-muted);">{str(a.get("response_text", ""))[:200]}</span><br>'
                f'<span style="font-size:0.85rem;">{t("metric_status", lang)}: {a.get("status", "unknown")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    limitation_notice("practice_boundary", lang)


# ---------------------------------------------------------------------------
# Learning Journey page
# ---------------------------------------------------------------------------

def render_learning_journey_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Learning Journey: chronological observable events timeline.

    Events are derived server-side from authoritative source records; nothing
    here creates events. Page rendering, navigation, locale switching, and
    refresh never write journey data.
    """
    page_header("learning_journey", "journey_caption", lang)

    from app.ui.student_context import set_selected_learner, student_id_input

    student_id = student_id_input("student_id", "journey_student_v2", lang, placeholder_key="student_id_placeholder")
    set_selected_learner(student_id)

    if not student_id.strip():
        info_box("journey_enter_student_id", lang)
        return

    if not st.button(t("load_journey", lang), key="journey_load_v2"):
        return

    try:
        with st.spinner(t("journey_loading", lang)):
            journey = api_client.get_journey(student_id.strip())
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return

    events = journey.get("events", [])
    if not events:
        _render_journey_empty_state(journey, lang)
        return

    section_header("journey_timeline", lang)
    for ev in events:
        params = dict(ev.get("description_params") or {})
        limitations = ev.get("limitations") or []
        timeline_event(
            event_label=t(ev.get("title_key", ""), lang),
            timestamp=_short_timestamp(ev.get("occurred_at", "")),
            target_code=f"#{ev['submission_id']}" if ev.get("submission_id") else "",
            detail=t(ev.get("description_key", ""), lang, **params),
            boundary=limitations[0] if limitations else "",
            lang=lang,
        )

    for state in journey.get("derived_states", []):
        message_key = state.get("message_key") or ""
        if message_key:
            warning_box(message_key, lang)

    limitation_notice("all_descriptive", lang)


def _short_timestamp(value: str) -> str:
    """Compact UTC timestamp for display (e.g., 2026-08-01 12:34)."""
    try:
        dt = __import__("datetime").datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(__import__("datetime").timezone.utc).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(value)[:16]


def _render_journey_empty_state(journey: dict, lang: str) -> None:
    """Render an accurate, classified Learning Journey empty state."""
    state = journey.get("state") or "no_submissions"
    counts = journey.get("counts") or {}
    known = [
        key for key, label in (
            ("submissions", "journey_known_submissions"),
            ("analysis_runs", "journey_known_analyses"),
            ("feedback_records", "journey_known_feedback"),
            ("selected_priorities", "journey_known_priorities"),
            ("practice_targets", "journey_known_targets"),
            ("exercise_attempts", "journey_known_attempts"),
        )
        if int(counts.get(key) or 0) > 0
    ]
    if known:
        known_text = t("journey_known_label", lang) + " " + "; ".join(
            f"{t(label, lang)}: {counts[key]}" for key, label in (
                ("submissions", "journey_known_submissions"),
                ("analysis_runs", "journey_known_analyses"),
                ("feedback_records", "journey_known_feedback"),
                ("selected_priorities", "journey_known_priorities"),
                ("practice_targets", "journey_known_targets"),
                ("exercise_attempts", "journey_known_attempts"),
            ) if int(counts.get(key) or 0) > 0
        )
        st.caption(known_text)

    mapping = {
        "no_submissions": ("journey_empty_no_submissions_title", "journey_empty_no_submissions_desc", "journey_empty_no_submissions_next"),
        "submission_without_analysis": ("journey_empty_no_analysis_title", "journey_empty_no_analysis_desc", "journey_empty_no_analysis_next"),
        "analysis_without_priority": ("journey_empty_no_priority_title", "journey_empty_no_priority_desc", "journey_empty_no_priority_next"),
        "feedback_no_practice_target": ("journey_empty_no_target_title", "journey_empty_no_target_desc", "journey_empty_no_target_next"),
        "target_no_attempt": ("journey_empty_no_attempt_title", "journey_empty_no_attempt_desc", "journey_empty_no_attempt_next"),
        "attempt_no_evaluation": ("journey_empty_no_evaluation_title", "journey_empty_no_evaluation_desc", "journey_empty_no_evaluation_next"),
        "revision_no_response": ("journey_empty_no_revision_title", "journey_empty_no_revision_desc", "journey_empty_no_revision_next"),
        "later_task_evidence_none": ("journey_empty_no_transfer_title", "journey_empty_no_transfer_desc", "journey_empty_no_transfer_next"),
    }
    title_key, desc_key, next_key = mapping.get(state, mapping["no_submissions"])
    empty_state(title_key, desc_key, lang)
    if next_key:
        info_box(next_key, lang)
    limitation_notice("journey_empty_boundary", lang)
