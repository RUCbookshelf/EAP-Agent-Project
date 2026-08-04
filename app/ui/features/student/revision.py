"""Student Revision feature (v0.9.5-C)."""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError
from app.errors import ErrorCategory
from app.ui.ports.student import StudentRevisionApiPort
from app.ui.components import (
    empty_state,
    error_box,
    evidence_quote,
    field_error,
    info_box,
    limitation_notice,
    loading_box,
    render_api_error,
    section_header,
    student_action_block,
    student_context_block,
    student_page_intro,
    success_box,
    technical_caption,
    warning_box,
)
from app.ui.features.student.formatting import _feedback_category_label
from app.ui.features.student.navigation import (
    _finish_revision_cycle,
    _navigate_student_page,
)
from app.ui.features.student.session import _writing_saved_for_learner
from app.ui.features.student.submit_reliability import (
    consume_pending,
    enter_pending,
    release_pending,
    render_outcome,
    store_outcome,
)
from app.ui.locale import t
from app.ui.student_context import set_selected_learner, student_id_input


def _revision_saved_for_source(
    result: dict | None, learner_id: str, source_submission_id: int | None = None
) -> bool:
    """Lock only a revision saved for this learner and, when given, source."""
    if not _writing_saved_for_learner(result, learner_id):
        return False
    saved_source = result.get("ui_submission", {}).get("revision_of_submission_id")
    return saved_source is not None and (
        source_submission_id is None or saved_source == source_submission_id
    )

def _source_priorities(source: dict) -> list[dict]:
    """Validated priority items from the persisted structured feedback.

    The bundle feedback is authoritative; malformed or missing priority items
    are dropped, never inferred (v0.9.7-A).
    """
    feedback = source.get("feedback") or {}
    raw_items = feedback.get("priority_feedback")
    if not isinstance(raw_items, list):
        return []
    items = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        if all(
            isinstance(item.get(field), str) and item.get(field)
            for field in ("category", "explanation", "revision_guidance")
        ):
            items.append(item)
    return items


def _latest_revision_of_source(candidates: list[dict], source_id: int) -> dict | None:
    """Newest candidate that is a saved revision of `source_id`, or None."""
    matches = [
        item for item in candidates
        if int(item.get("revision_of_submission_id") or 0) == source_id
    ]
    if not matches:
        return None
    return max(
        matches,
        key=lambda item: (
            str(item.get("submitted_at") or ""),
            int(item.get("essay_id") or 0),
        ),
    )


def _priority_selection(priorities: list[dict], source_id: int) -> tuple[int, bool]:
    """Revalidate the in-session active-priority selection for this source.

    Returns (index, reset) where reset is True when a stored selection existed
    but was invalid for the current source and the first priority was restored.
    """
    stored = st.session_state.get("revision_priority_selection")
    if isinstance(stored, dict) and stored.get("submission_id") == source_id:
        index = stored.get("index")
        if isinstance(index, int) and 0 <= index < len(priorities):
            return index, False
        return 0, True
    return 0, False


def _render_priority_card(item: dict, lang: str, *, instruction: bool = True) -> None:
    """Render one active-priority task card from persisted feedback fields."""
    section_header("student_revision_priority_task", lang=lang)
    student_context_block(
        [
            (
                "student_revision_priority_label",
                _feedback_category_label(item.get("category", ""), lang),
            ),
            ("student_revision_priority_reason", item.get("explanation", "")),
            ("student_revision_priority_direction", item.get("revision_guidance", "")),
        ],
        lang,
    )
    if item.get("evidence_quote"):
        section_header("student_feedback_evidence", lang=lang)
        evidence_quote(item["evidence_quote"], lang)
    if instruction:
        info_box("student_revision_instruction", lang)


def _render_priority_task(priorities: list[dict], source_id: int, lang: str) -> None:
    """Render the active-priority selection (when needed) and task card."""
    index, reset = _priority_selection(priorities, source_id)
    if reset:
        st.session_state.pop(f"revision_priority_select_{source_id}", None)
    if len(priorities) > 1:
        index = st.radio(
            t("student_revision_select_priority", lang),
            list(range(len(priorities))),
            index=index,
            key=f"revision_priority_select_{source_id}",
            format_func=lambda i: _feedback_category_label(
                priorities[i].get("category", ""), lang
            ),
        )
    st.session_state["revision_priority_selection"] = {
        "submission_id": source_id,
        "index": int(index),
    }
    if reset:
        info_box("student_revision_selection_reset", lang)
    _render_priority_card(priorities[int(index)], lang)


def _render_priority_addressed(priorities: list[dict], index: int, lang: str) -> None:
    """Completion confirmation of the priority addressed by a saved revision."""
    item = None
    if priorities and 0 <= index < len(priorities):
        item = priorities[index]
    elif priorities:
        item = priorities[0]
    if item is None:
        return
    section_header("student_revision_priority_addressed", lang=lang)
    student_context_block(
        [
            (
                "student_revision_priority_label",
                _feedback_category_label(item.get("category", ""), lang),
            ),
            ("student_revision_priority_direction", item.get("revision_guidance", "")),
        ],
        lang,
    )


def _render_revision_next_steps(lang: str) -> None:
    """Clear completion next-step actions for a finished revision cycle."""
    st.button(
        t("student_revision_finish_cycle", lang),
        type="primary",
        use_container_width=True,
        key="revision_finish_cycle",
        on_click=_finish_revision_cycle,
        args=(lang,),
    )
    st.button(
        t("student_revision_open_practice", lang),
        use_container_width=True,
        key="revision_open_practice",
        on_click=_navigate_student_page,
        args=("practice", lang),
    )
    info_box("student_revision_practice_note", lang)
    st.button(
        t("student_revision_open_journey", lang),
        use_container_width=True,
        key="revision_primary_action",
        on_click=_navigate_student_page,
        args=("learning_journey", lang),
    )


# Baseline key for the bounded linked-revision reconciliation (v0.9.6-A).
_REVISION_BASELINE_KEY = "revision_baseline_latest_submitted_at"


def _revision_baseline(candidates: list[dict], source_id: int) -> str | None:
    """Newest server submitted_at of a revision of `source_id`, or None.

    Server timestamps only; a reconciliation match with submitted_at greater
    than this baseline was created by the current submit attempt.
    """
    timestamps = [
        str(item["submitted_at"])
        for item in candidates
        if int(item.get("revision_of_submission_id") or 0) == source_id
        and item.get("submitted_at")
    ]
    return max(timestamps) if timestamps else None


def _reconcile_linked_revision(
    api_client: StudentRevisionApiPort,
    learner_id: str,
    source_id: int,
    baseline: str | None,
) -> str:
    """Bounded read-only reconciliation after a linked-revision submit timeout.

    Uses only existing read APIs (student revision candidates and the
    submission bundle). Returns CONFIRMED_SUCCESS, STILL_PROCESSING, or
    UNCONFIRMED. Never POSTs and never recurses; read failures degrade to
    UNCONFIRMED.
    """
    try:
        candidates = api_client.get_student_revision_candidates(learner_id).get("candidates", [])
    except ApiClientError:
        return "UNCONFIRMED"
    matches = [
        item for item in candidates
        if int(item.get("revision_of_submission_id") or 0) == source_id
        and item.get("submitted_at") is not None
        and (baseline is None or str(item["submitted_at"]) > baseline)
    ]
    if not matches:
        return "UNCONFIRMED"
    newest = max(matches, key=lambda item: str(item["submitted_at"]))
    try:
        bundle = api_client.get_submission(int(newest["essay_id"]))
    except ApiClientError:
        return "UNCONFIRMED"
    if not bundle:
        return "UNCONFIRMED"
    if bundle.get("feedback") is not None or bundle.get("success_status") is not None:
        return "CONFIRMED_SUCCESS"
    return "STILL_PROCESSING"


def _revision_status_label(prefix: str, value: str, lang: str) -> str:
    """Localize frozen revision observation and confidence values."""
    key = f"student_revision_{prefix}_{value}"
    localized = t(key, lang)
    return localized if localized != key else value.replace("_", " ").title()


def _revision_observation_text(value: str, lang: str) -> str:
    """Translate the finite set of service-authored conservative observations."""
    key = {
        "The revision evidence is not sufficiently comparable.": "student_revision_observed_not_comparable",
        "The prior signal is not currently observed in the linked draft.": "student_revision_observed_not_current",
        "The signal or its evidence changed in the linked draft.": "student_revision_observed_changed",
        "The prior diagnosis category is still observed.": "student_revision_observed_still_present",
        "No comparable trajectory is available.": "student_revision_observed_unavailable",
    }.get(value)
    return t(key, lang) if key else value


def _render_revision_observation(result: dict, lang: str) -> None:
    """Separate conservative system observations from learner-facing claims."""
    trajectory = result.get("within_task_revision_trajectory") or {}
    empty_states = set(result.get("ui_empty_states") or [])
    section_header("student_revision_observation", lang=lang)
    if not trajectory:
        info_box("student_revision_no_uptake", lang)
        limitation_notice("student_revision_boundary", lang)
        return

    if "MAJOR_REWRITE_LIMITS_ATTRIBUTION" in empty_states:
        warning_box("student_revision_major_rewrite", lang)

    observations = trajectory.get("feedback_uptake_candidates", [])
    if observations:
        for item in observations[:2]:
            student_context_block(
                [
                    (
                        "student_revision_observation_status",
                        _revision_status_label("status", item.get("status", ""), lang),
                    ),
                    (
                        "student_revision_observed_change",
                        _revision_observation_text(item.get("observed_change", ""), lang),
                    ),
                    (
                        "student_revision_attribution",
                        _revision_status_label(
                            "confidence", trajectory.get("attribution_confidence", ""), lang
                        ),
                    ),
                ],
                lang,
            )
    else:
        info_box("student_revision_no_uptake", lang)

    previous = trajectory.get("previous_selected_priorities", [])
    if previous:
        section_header("student_revision_priorities", lang=lang)
        for item in previous[:2]:
            student_context_block(
                [
                    (
                        "student_revision_feedback_focus",
                        _feedback_category_label(item.get("category", ""), lang),
                    ),
                    ("revision_guidance", item.get("revision_guidance", "")),
                ],
                lang,
            )
    elif "NO_PREVIOUS_PRIORITY" in empty_states:
        info_box("student_revision_no_previous", lang)

    first_latest = trajectory.get("first_to_latest_comparison") or {}
    if first_latest:
        changes = first_latest.get("token_changes", {})
        section_header("student_revision_changes", lang=lang)
        student_context_block(
            [
                (
                    "student_revision_inserted",
                    f"{float(changes.get('inserted_ratio', 0)):.1%}",
                ),
                (
                    "student_revision_deleted",
                    f"{float(changes.get('deleted_ratio', 0)):.1%}",
                ),
                (
                    "student_revision_modified",
                    f"{float(changes.get('modified_ratio', 0)):.1%}",
                ),
            ],
            lang,
        )
        info_box("student_revision_edit_note", lang)
    limitation_notice("student_revision_boundary", lang)


def render_revision_page(api_client: StudentRevisionApiPort, lang: str) -> None:
    """Student Revision page: original context, revised-text task, observation."""
    student_page_intro("student_revision_title", "student_revision_purpose", lang)

    student_id = student_id_input(
        "student_id", "revision_student", lang, placeholder_key="student_id_placeholder"
    )
    set_selected_learner(student_id)
    learner_id = student_id.strip()
    if not learner_id:
        student_action_block(
            "student_revision_current_action",
            "student_revision_enter_id",
            lang,
            state="blocked",
        )
        limitation_notice("student_revision_boundary", lang)
        return

    student_context_block([("student_context_learner", learner_id)], lang)
    saved = st.session_state.get("submission_result")
    if _revision_saved_for_source(saved, learner_id):
        release_pending("revision")
        source = saved.get("ui_submission", {}).get("revision_source", {})
        section_header("student_revision_original_context", lang=lang)
        student_context_block(
            [
                ("writing_prompt", source.get("writing_prompt", "")),
                ("student_revision_source_stage", source.get("draft_stage", "")),
            ],
            lang,
        )
        if source.get("essay_text"):
            evidence_quote(source["essay_text"], lang)
        success_box("student_revision_saved_title", lang)
        student_action_block(
            "student_revision_saved_title",
            "student_revision_step_complete",
            lang,
            state="complete",
        )
        addressed = (saved.get("within_task_revision_trajectory") or {}).get(
            "previous_selected_priorities"
        ) or []
        addressed_index = int(
            (saved.get("ui_submission") or {}).get("revision_priority_index") or 0
        )
        _render_priority_addressed(addressed, addressed_index, lang)
        technical_caption(
            f"{t('student_revision_source_reference', lang)}: "
            f"#{saved.get('ui_submission', {}).get('revision_of_submission_id', '?')} · "
            f"{t('student_revision_saved_reference', lang)}: #{saved.get('submission_id', '?')}"
        )
        _render_revision_observation(saved, lang)
        _render_revision_next_steps(lang)
        return

    try:
        with st.spinner(t("student_revision_loading", lang)):
            candidates = api_client.get_student_revision_candidates(learner_id).get(
                "candidates", []
            )
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return
    if not candidates:
        empty_state(
            "student_revision_no_eligible_title",
            "student_revision_no_eligible_desc",
            lang,
        )
        st.button(
            t("student_feedback_open_writing", lang),
            type="primary",
            use_container_width=True,
            key="revision_primary_action",
            on_click=_navigate_student_page,
            args=("student_writing_title", lang),
        )
        limitation_notice("student_revision_boundary", lang)
        return

    labels = {
        f"{item.get('writing_prompt', '')[:80]} · {item.get('draft_stage', '')} · #{item.get('essay_id', '?')}": item
        for item in candidates
    }
    preset_source = st.session_state.pop("revision_source_preset", None)
    preset_index = next(
        (
            index for index, item in enumerate(candidates)
            if int(item.get("essay_id") or 0) == preset_source
        ),
        None,
    )
    selected_label = st.selectbox(
        t("student_revision_select_source", lang),
        list(labels),
        index=preset_index if preset_index is not None else 0,
        key="revision_source_select",
    )
    selected = labels[selected_label]
    source_id = int(selected["essay_id"])
    st.session_state[_REVISION_BASELINE_KEY] = _revision_baseline(candidates, source_id)
    try:
        source = api_client.get_submission(source_id)
        targets = api_client.get_practice_targets(learner_id)
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return

    section_header("student_revision_original_context", lang=lang)
    student_context_block(
        [
            ("writing_prompt", source.get("writing_prompt", "")),
            ("student_revision_source_stage", source.get("draft_stage", "")),
        ],
        lang,
    )
    priorities = _source_priorities(source)
    existing_revision = _latest_revision_of_source(candidates, source_id)
    if not priorities:
        # No-priority sources are valid revision sources (v0.9.6-C1): the
        # absence of an automatic focus is explained, not fabricated.
        info_box("student_revision_no_auto_focus", lang)
    st.text_area(
        t("student_revision_original_text", lang),
        value=source.get("essay_text", ""),
        height=220,
        disabled=True,
        key=f"revision_original_{source_id}",
    )
    matching_targets = [
        item for item in targets
        if int(item.get("source_submission_id") or 0) == source_id
        and item.get("status") == "active"
    ]
    if matching_targets:
        student_context_block(
            [("student_revision_feedback_focus", matching_targets[0].get("target_label", ""))],
            lang,
        )
    else:
        info_box("student_revision_no_target_context", lang)
    technical_caption(f"{t('student_revision_source_reference', lang)}: #{source_id}")

    if existing_revision is not None:
        # v0.9.7-A: a saved revision is never treated as unsubmitted on
        # re-entry; show the completed state instead of a blank form so no
        # uncontrolled duplicate revision can be created from this page.
        success_box("student_revision_already_submitted_title", lang)
        student_action_block(
            "student_revision_already_submitted_title",
            "student_revision_step_complete",
            lang,
            state="complete",
        )
        _render_priority_addressed(
            priorities, _priority_selection(priorities, source_id)[0], lang
        )
        technical_caption(
            f"{t('student_revision_saved_reference', lang)}: "
            f"#{existing_revision.get('essay_id', '?')}"
        )
        _render_revision_next_steps(lang)
        limitation_notice("student_revision_boundary", lang)
        return

    if priorities:
        _render_priority_task(priorities, source_id, lang)

    validation_state = st.session_state.get("revision_validation_state") or {}
    invalid = (
        validation_state.get("student_id") == learner_id
        and validation_state.get("source_submission_id") == source_id
    )
    section_header("student_revision_revised_text", lang=lang)
    revised_text = st.text_area(
        t("student_revision_revised_text", lang),
        height=360,
        key="revision_text_input",
        help=t("student_writing_required_help", lang),
    )
    if invalid:
        field_error("student_revision_empty_text", lang)
    student_action_block(
        "student_revision_current_action", "student_revision_submit_desc", lang
    )
    if not st.button(
        t("student_revision_submit", lang),
        type="primary",
        use_container_width=True,
        key="revision_submit_primary",
    ):
        limitation_notice("student_revision_boundary", lang)
        return
    if not revised_text.strip():
        st.session_state["revision_validation_state"] = {
            "student_id": learner_id,
            "source_submission_id": source_id,
        }
        st.rerun()

    st.session_state.pop("revision_validation_state", None)
    if consume_pending("revision", "LINKED_REVISION", lang):
        # A linked-revision submit is in flight or its terminal outcome is
        # pending display; this queued click was consumed without a second POST.
        return

    submission = {
        "student_id": learner_id,
        "writing_prompt": source.get("writing_prompt", ""),
        "genre": source.get("genre", "argumentative essay"),
        "draft_stage": "revised draft",
        "timed": False,
        "time_limit_minutes": None,
        "active_writing_duration_seconds": None,
        "timing_source": "unknown",
        "timing_quality": "unavailable",
        "unexplained_interruption": False,
        "tool_use": source.get("tool_use", "none"),
        "essay_text": revised_text,
        "revision_of_submission_id": source_id,
    }
    enter_pending("revision")
    try:
        loading_box("student_revision_submitting", lang)
        result = api_client.submit_linked_revision(submission)
    except ApiClientError as exc:
        if exc.category == ErrorCategory.REQUEST_TIMEOUT:
            outcome = _reconcile_linked_revision(
                api_client, learner_id, source_id,
                st.session_state.get(_REVISION_BASELINE_KEY),
            )
            store_outcome("revision", outcome)
            render_outcome("LINKED_REVISION", outcome, lang)
            return
        release_pending("revision")
        render_api_error(exc, lang)
        return
    except Exception:
        release_pending("revision")
        error_box("submission_error", lang)
        return
    release_pending("revision")
    result["ui_submission"] = {
        "student_id": learner_id,
        "writing_prompt": source.get("writing_prompt", ""),
        "genre": source.get("genre", "argumentative essay"),
        "draft_stage": "revised draft",
        "revision_of_submission_id": source_id,
        "revision_priority_index": int(
            (st.session_state.get("revision_priority_selection") or {}).get("index", 0)
        ),
        "revision_source": {
            "writing_prompt": source.get("writing_prompt", ""),
            "draft_stage": source.get("draft_stage", ""),
            "essay_text": source.get("essay_text", ""),
        },
    }
    st.session_state["submission_result"] = result
    st.rerun()
