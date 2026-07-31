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
    info_box,
    limitation_notice,
    page_header,
    section_header,
    success_box,
    timeline_event,
    warning_box,
)
from app.ui.locale import t


def render_student_home(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Home: task summary, latest status, next action."""
    page_header("student_home_title", "student_home_subtitle", lang)

    student_id = st.text_input(
        t("student_id", lang), key="home_student",
        placeholder=t("student_id_placeholder", lang),
    )

    if not student_id.strip():
        info_box("student_home_enter_id", lang)
        return

    try:
        targets = api_client.get_practice_targets(student_id.strip())
        traces = api_client.get_engagement_traces(student_id.strip())
        transfer = api_client.get_transfer_evidence(student_id.strip())
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return

    section_header("student_home_current_task", lang)
    if not targets:
        st.write(t("student_home_no_submissions", lang))
    else:
        active = [t for t in targets if t.get("status") == "active"]
        completed = [t for t in targets if t.get("status") == "completed"]
        st.markdown(
            f'<div class="px-card">'
            f'<strong>{t("student_home_active_targets", lang)}: {len(active)}</strong><br>'
            f'{t("student_home_completed_targets", lang)}: {len(completed)}'
            f'</div>',
            unsafe_allow_html=True,
        )

    section_header("student_home_latest_status", lang)
    if traces:
        latest = traces[-1]
        status = latest.get("status", "")
        label_map = {
            "target_identified": "student_home_target_identified",
            "practice_available": "student_home_practice_available",
            "practice_attempted": "student_home_practice_attempted",
            "practice_response_candidate": "student_home_response_observed",
            "within_task_response_candidate": "student_home_revision_observed",
            "later_task_recurrence": "student_home_recurrence",
            "later_task_nonrecurrence": "student_home_nonrecurrence",
            "insufficient_evidence": "student_home_insufficient",
        }
        st.markdown(
            f'<div class="px-card">'
            f'<strong>{t(label_map.get(status, status), lang)}</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.write(t("student_home_no_events", lang))

    section_header("student_home_next_action", lang)
    if not targets:
        info_box("student_home_action_submit", lang)
    elif not traces:
        info_box("student_home_action_submit", lang)
    else:
        last_status = traces[-1].get("status", "")
        if last_status in ("target_identified", "practice_available"):
            info_box("student_home_action_practice", lang)
        elif last_status == "practice_attempted":
            info_box("student_home_action_revise", lang)
        elif last_status == "within_task_response_candidate":
            info_box("student_home_action_new_task", lang)
        else:
            info_box("student_home_action_continue", lang)

    limitation_notice("student_home_boundary", lang)


# ---------------------------------------------------------------------------
# Writing page
# ---------------------------------------------------------------------------

def render_writing_page(api_client: WritingFeedbackApiClient, lang: str) -> None:
    """Student Writing page: submission form with clear field grouping."""
    page_header("student_writing_title", "student_writing_subtitle", lang)

    student_id = st.text_input(
        t("student_id", lang), key="writing_student",
        placeholder=t("student_id_placeholder", lang),
    )

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

    if not student_id.strip():
        st.error(t("student_writing_need_id", lang))
        return
    if not essay_text.strip():
        st.error(t("student_writing_need_text", lang))
        return
    if is_revision and revision_of_submission_id is None:
        st.error(t("submission_choose_revision", lang))
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

    with st.container(border=True):
        st.caption(f"Essay #{result.get('submission_id', '?')} | {result.get('ui_submission', {}).get('draft_stage', '')}")
        st.caption(f"{t('provider_label', lang)}: {provider.get('provider_name', '')}")

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

    student_id = st.text_input(
        t("student_id", lang), key="practice_student_v2",
        placeholder=t("student_id_placeholder", lang),
    )

    if not student_id.strip():
        info_box("no_active_target", lang)
        return

    if st.button(t("load_practice", lang), key="practice_load"):
        try:
            targets = api_client.get_practice_targets(student_id.strip())
            st.session_state["practice_targets_v2"] = targets
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

    source_text = st.text_area(
        t("student_practice_source_text", lang), key="practice_source_v2", height=80,
        placeholder=t("student_practice_source_placeholder", lang),
    )
    if st.button(t("generate_exercise", lang), key="practice_gen"):
        payload = {"practice_target": selected, "source_text": source_text}
        try:
            exercise = api_client.create_exercise(selected.get("practice_target_id", ""), payload)
            st.session_state["current_exercise_v2"] = exercise
            st.session_state["exercise_attempts_v2"] = []
        except ApiClientError as exc:
            render_api_error(exc, lang)
            return

    exercise = st.session_state.get("current_exercise_v2")
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
    """Student Learning Journey: chronological observable events timeline."""
    page_header("learning_journey", "journey_caption", lang)

    student_id = st.text_input(
        t("student_id", lang), key="journey_student_v2",
        placeholder=t("student_id_placeholder", lang),
    )

    if not student_id.strip():
        info_box("enter_student_id", lang)
        return

    if not st.button(t("load_journey", lang), key="journey_load_v2"):
        return

    try:
        traces = api_client.get_engagement_traces(student_id.strip())
        transfer = api_client.get_transfer_evidence(student_id.strip())
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return

    events = []

    for t_item in traces:
        ts = t_item.get("status", "")
        label_map = {
            "target_identified": "journey_target_identified",
            "practice_available": "journey_practice_available",
            "practice_attempted": "journey_practice_attempted",
            "practice_response_candidate": "journey_response_candidate",
            "within_task_response_candidate": "journey_within_task",
            "later_task_recurrence": "journey_recurrence",
            "later_task_nonrecurrence": "journey_nonrecurrence",
            "later_task_mixed_evidence": "journey_mixed",
            "insufficient_evidence": "insufficient_evidence",
        }
        events.append({
            "event": t(label_map.get(ts, ts), lang),
            "time": t_item.get("created_at", ""),
            "target": t_item.get("target_code", ""),
            "detail": "",
            "boundary": "",
        })

    for te in transfer:
        events.append({
            "event": t("transfer_evidence", lang),
            "time": te.get("created_at", ""),
            "target": te.get("target_code", ""),
            "detail": te.get("observed_status", ""),
            "boundary": t("transfer_boundary", lang),
        })

    events.sort(key=lambda e: e.get("time", ""))

    if not events:
        info_box("empty_events", lang)
        return

    section_header("journey_timeline", lang)
    for ev in events:
        timeline_event(
            event_label=ev["event"],
            timestamp=ev["time"],
            target_code=ev["target"],
            detail=ev["detail"],
            boundary=ev["boundary"],
            lang=lang,
        )

    limitation_notice("all_descriptive", lang)