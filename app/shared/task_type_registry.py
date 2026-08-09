"""Namespace-scoped TaskTypeRegistry mechanism (D-04, D-22).

Shared Core provides the MECHANISM; domain departments provide CONTENT.
Task type entries are metadata-only: no comparability predicate exists
in the registry (D-22). The ``legacy_unclassified`` sentinel is an
explicit allowed value where frozen docs support it.

References: D-04, D-22, D-26.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TaskTypeEntry:
    """Metadata for a single task type within a namespace.

    Attributes are intentionally minimal. D-22 requires metadata-only
    semantics: the registry must NOT store a comparability predicate or
    imply any ordering between task types.
    """

    task_type_id: str
    namespace: str
    display_name: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# Sentinel value for unclassified legacy task types (D-22).
LEGACY_UNCLASSIFIED: str = "legacy_unclassified"

# The only registered namespaces in H1.
REGISTERED_NAMESPACES: frozenset[str] = frozenset({"l2", "academic"})


class TaskTypeRegistry:
    """Namespace-scoped registry for task type metadata.

    Keyed by ``(namespace, task_type_id)`` tuples. Two namespaces
    (``l2`` and ``academic``) coexist without collisions. Unknown
    namespaces are rejected at registration time.

    The ``l2`` namespace carries the Domain Pack v1 content (five types +
    the ``legacy_unclassified`` sentinel) registered under the qualified
    taxonomy contract (``l2-task-type-taxonomy-v1.0.0``). The ``academic``
    namespace carries the mechanism with NO content entries.
    """

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], TaskTypeEntry] = {}

    @property
    def namespaces(self) -> frozenset[str]:
        """Return the set of namespaces that have at least one entry."""
        return frozenset(ns for ns, _ in self._entries)

    def _validate_namespace(self, namespace: str) -> None:
        if namespace not in REGISTERED_NAMESPACES:
            raise ValueError(
                f"Unknown namespace: {namespace!r}. "
                f"Registered namespaces: {sorted(REGISTERED_NAMESPACES)}"
            )

    def register(self, entry: TaskTypeEntry) -> None:
        """Register a task type entry.

        Raises ``ValueError`` if the namespace is unknown or if an entry
        with the same ``(namespace, task_type_id)`` already exists.
        """
        self._validate_namespace(entry.namespace)
        key = (entry.namespace, entry.task_type_id)
        if key in self._entries:
            raise ValueError(
                f"Task type already registered: namespace={entry.namespace!r}, "
                f"task_type_id={entry.task_type_id!r}"
            )
        self._entries[key] = entry

    def get(self, namespace: str, task_type_id: str) -> TaskTypeEntry:
        """Retrieve a task type entry by namespace and id."""
        self._validate_namespace(namespace)
        key = (namespace, task_type_id)
        if key not in self._entries:
            raise ValueError(
                f"Unknown task type: namespace={namespace!r}, "
                f"task_type_id={task_type_id!r}"
            )
        return self._entries[key]

    def list_namespace(self, namespace: str) -> list[TaskTypeEntry]:
        """List all entries for a given namespace."""
        self._validate_namespace(namespace)
        return [
            entry
            for (ns, _), entry in sorted(self._entries.items())
            if ns == namespace
        ]

    def list_all(self) -> list[TaskTypeEntry]:
        """List all entries across all namespaces."""
        return [entry for _, entry in sorted(self._entries.items())]

    def has_entry(self, namespace: str, task_type_id: str) -> bool:
        """Check whether an entry exists."""
        return (namespace, task_type_id) in self._entries


def default_task_type_registry() -> TaskTypeRegistry:
    """Create a TaskTypeRegistry with H1 baseline content.

    Domain Pack v1 (authorized 2026-08-09):
    - ``l2`` namespace: five types (opinion, argumentative, discussion,
      problem_solution, general_eap) per the qualified taxonomy contract
      section 1, plus the ``legacy_unclassified`` sentinel (D-22).
    - ``academic`` namespace: mechanism only, no content entries.

    Registry content is metadata-only (D-22): no comparability predicate and
    no ordering semantics. Display names follow the taxonomy contract
    section 1 table; the canonical non-hierarchical display order and the
    zh_CN labels (D-L2-09) live in the Domain Pack v1 content
    (``app/configuration/domain_packs/l2/v1.0.0``) and the locale files.
    """
    registry = TaskTypeRegistry()

    # l2 namespace: Domain Pack v1 five-type content (metadata-only).
    _FIVE_TYPES = (
        ("opinion", "Opinion Essay", 1),
        ("argumentative", "Argumentative Essay", 2),
        ("discussion", "Discussion Essay", 3),
        ("problem_solution", "Problem-Solution Essay", 4),
        ("general_eap", "General EAP", 5),
    )
    for task_type_id, display_name, display_order in _FIVE_TYPES:
        registry.register(TaskTypeEntry(
            task_type_id=task_type_id,
            namespace="l2",
            display_name=display_name,
            description=(
                "Task-routing/task-semantics metadata per the qualified "
                "L2 task-type taxonomy (l2-task-type-taxonomy-v1.0.0)."
            ),
            metadata={
                "taxonomy_version": "l2-task-type-taxonomy-v1.0.0",
                "display_order": display_order,
                "locale_key": f"task_type_{task_type_id}",
                "pack": "l2-core-v1.0.0",
                "metadata_only": True,
            },
        ))

    # The legacy sentinel (D-22): explicit allowed value for historical rows
    # whose genre/task evidence is insufficient for explicit mapping.
    registry.register(TaskTypeEntry(
        task_type_id=LEGACY_UNCLASSIFIED,
        namespace="l2",
        display_name="Legacy Unclassified",
        description=(
            "Explicit sentinel for task types that cannot be classified "
            "under the current L2 task-type taxonomy (D-22)."
        ),
        metadata={
            "role": "legacy_sentinel",
            "mapping_manifest": "l2-legacy-genre-mapping-v1.0.0",
            "taxonomy_version": "l2-task-type-taxonomy-v1.0.0",
            "metadata_only": True,
        },
    ))

    # academic namespace: mechanism only, zero content entries.
    # No registration needed; the namespace is valid but empty.

    return registry
