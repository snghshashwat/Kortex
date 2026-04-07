"""
Context graph service: visualize semantic relationships between notes.
Shows which notes are semantically similar to each other.
"""
from app.ai import embed_text
from app.db import get_db


def build_context_graph(user_id: int, similarity_threshold: float = 0.7, limit: int = 20) -> dict:
    """
    Build a knowledge graph showing semantic relationships between user's notes.
    
    Returns:
    {
        "nodes": [{"id": "msg_id", "label": "note text", "created_at": "..."}],
        "edges": [{"source": "msg_id_1", "target": "msg_id_2", "similarity": 0.85}],
        "stats": {"total_messages": 5, "total_edges": 3}
    }
    """
    with get_db() as (_, cur):
        # Fetch all messages for this user (limit to prevent huge graphs).
        cur.execute(
            """
            SELECT m.id, m.message_text, m.created_at, e.embedding
            FROM messages m
            LEFT JOIN embeddings e ON e.message_id = m.id
            WHERE m.telegram_user_id = %s
            ORDER BY m.created_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()

    nodes = []
    edges = []
    embeddings = {}
    scored_edges = []

    # Build nodes from messages.
    for row in rows:
        msg_id = str(row["id"])
        text = row["message_text"]
        nodes.append(
            {
                "id": msg_id,
                "label": text[:80] if len(text) > 80 else text,  # Truncate for display
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "degree": 0,
            }
        )
        if row["embedding"]:
            embeddings[msg_id] = row["embedding"]

    # If we don't have embeddings, just return nodes with no edges.
    if not embeddings:
        return {
            "nodes": nodes,
            "edges": [],
            "stats": {"total_messages": len(nodes), "total_edges": 0},
        }

    # Compute similarity between all pairs of embeddings.
    for i, (msg_id_1, embedding_1) in enumerate(embeddings.items()):
        for msg_id_2, embedding_2 in list(embeddings.items())[i + 1 :]:
            # Cosine similarity: dot(a, b) / (||a|| * ||b||)
            dot_product = sum(a * b for a, b in zip(embedding_1, embedding_2))
            norm_1 = sum(a ** 2 for a in embedding_1) ** 0.5
            norm_2 = sum(b ** 2 for b in embedding_2) ** 0.5
            
            if norm_1 == 0 or norm_2 == 0:
                similarity = 0
            else:
                similarity = dot_product / (norm_1 * norm_2)
            
            # Convert from cosine distance to 0-1 similarity.
            similarity = (similarity + 1) / 2

            scored_edges.append(
                {
                    "source": msg_id_1,
                    "target": msg_id_2,
                    "similarity": similarity,
                }
            )

    # Prefer edges above the chosen threshold, but keep a small fallback set
    # so the graph still shows structure when the notes are sparse or short.
    edges = [
        {
            "source": edge["source"],
            "target": edge["target"],
            "similarity": round(edge["similarity"], 3),
        }
        for edge in scored_edges
        if edge["similarity"] >= similarity_threshold
    ]

    if not edges and scored_edges:
        fallback_count = min(3, len(scored_edges))
        edges = [
            {
                "source": edge["source"],
                "target": edge["target"],
                "similarity": round(edge["similarity"], 3),
            }
            for edge in sorted(scored_edges, key=lambda item: item["similarity"], reverse=True)[:fallback_count]
        ]

    degree_counts = {node["id"]: 0 for node in nodes}
    for edge in edges:
        degree_counts[edge["source"]] += 1
        degree_counts[edge["target"]] += 1

    for node in nodes:
        node["degree"] = degree_counts[node["id"]]

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {"total_messages": len(nodes), "total_edges": len(edges)},
    }
