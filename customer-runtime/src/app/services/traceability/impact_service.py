"""BFS impact analysis service — SPEC-TRACEABILITY-001.

# @MX:ANCHOR: [AUTO] analyze_impact — approval gate dependency + scan router
# @MX:REASON: [AUTO] Called by impact endpoint; BFS must be cycle-safe for arbitrary graphs
"""
from collections import deque
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.impact_analysis import ImpactAnalysis
from app.models.traceability_edge import TraceabilityEdge


def _bfs_downstream(
    start_node_id: str,
    adjacency: dict[str, list[str]],
    visited: set[str],
) -> list[str]:
    """BFS traversal from start_node_id through adjacency map.

    Cycle-safe: each node visited at most once via visited set.
    Returns list of downstream node_ids (excludes start_node_id itself).
    """
    result: list[str] = []
    queue: deque[str] = deque()

    # Seed with direct neighbors, not start node itself
    visited.add(start_node_id)
    for neighbor in adjacency.get(start_node_id, []):
        if neighbor not in visited:
            visited.add(neighbor)
            queue.append(neighbor)
            result.append(neighbor)

    while queue:
        current = queue.popleft()
        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
                result.append(neighbor)

    return result


async def analyze_impact(
    trigger_node_id: str,
    change_summary: str,
    db: AsyncSession,
) -> ImpactAnalysis:
    """Perform BFS impact analysis from trigger_node_id.

    Loads all edges, builds adjacency map, traverses downstream nodes.
    Persists and returns ImpactAnalysis record.
    """
    # Load all edges
    edges = list((await db.execute(select(TraceabilityEdge))).scalars().all())

    # Build adjacency map: source -> [targets]
    adjacency: dict[str, list[str]] = {}
    edge_type_map: dict[tuple[str, str], str] = {}
    for edge in edges:
        adjacency.setdefault(edge.source_node_id, []).append(edge.target_node_id)
        edge_type_map[(edge.source_node_id, edge.target_node_id)] = edge.edge_type

    # BFS from trigger node
    visited: set[str] = set()
    downstream = _bfs_downstream(trigger_node_id, adjacency, visited)

    affected_nodes: list[dict[str, Any]] = [
        {
            "node_id": node_id,
            "reason": f"downstream of {trigger_node_id}",
        }
        for node_id in downstream
    ]

    analysis = ImpactAnalysis(
        trigger_node_id=trigger_node_id,
        trigger_change_summary=change_summary,
        affected_nodes=affected_nodes,
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)
    return analysis
