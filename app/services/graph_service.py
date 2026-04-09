"""
Context graph service: visualize semantic relationships between notes.
Shows which notes are semantically similar to each other.
"""
import re

from app.db import get_db


_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "your",
    "about",
    "into",
    "have",
    "will",
    "just",
    "also",
    "are",
    "was",
    "were",
    "but",
    "you",
    "not",
}


def _embedding_similarity(embedding_1: list[float], embedding_2: list[float]) -> float:
    # Cosine similarity: dot(a, b) / (||a|| * ||b||)
    dot_product = sum(a * b for a, b in zip(embedding_1, embedding_2))
    norm_1 = sum(a ** 2 for a in embedding_1) ** 0.5
    norm_2 = sum(b ** 2 for b in embedding_2) ** 0.5

    if norm_1 == 0 or norm_2 == 0:
        return 0.0

    # Convert cosine (-1..1) to (0..1)
    return (dot_product / (norm_1 * norm_2) + 1) / 2


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {token for token in tokens if len(token) > 2 and token not in _STOPWORDS}


def _text_similarity(text_1: str, text_2: str) -> float:
    tokens_1 = _tokenize(text_1)
    tokens_2 = _tokenize(text_2)

    if not tokens_1 or not tokens_2:
        return 0.0

    overlap = len(tokens_1 & tokens_2)
    if overlap == 0:
        return 0.0

    # Blend overlap and Jaccard so short notes can still link.
    jaccard = overlap / len(tokens_1 | tokens_2)
    overlap_ratio = overlap / min(len(tokens_1), len(tokens_2))
    return max(jaccard, overlap_ratio * 0.85)


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
            SELECT m.id, m.message_text, m.cleaned_text, m.created_at, e.embedding
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
    note_texts = {}
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
        note_texts[msg_id] = row.get("cleaned_text") or row["message_text"]
        if row["embedding"]:
            embeddings[msg_id] = row["embedding"]

    if len(nodes) <= 1:
        return {
            "nodes": nodes,
            "edges": [],
            "stats": {"total_messages": len(nodes), "total_edges": 0},
        }

    # Compute similarity between all note pairs.
    message_ids = [node["id"] for node in nodes]
    for i, msg_id_1 in enumerate(message_ids):
        for msg_id_2 in message_ids[i + 1 :]:
            if msg_id_1 in embeddings and msg_id_2 in embeddings:
                similarity = _embedding_similarity(embeddings[msg_id_1], embeddings[msg_id_2])
            else:
                similarity = _text_similarity(note_texts[msg_id_1], note_texts[msg_id_2])

            # Skip completely unrelated pairs when using fallback.
            if similarity <= 0:
                continue

            scored_edges.append(
                {
                    "source": msg_id_1,
                    "target": msg_id_2,
                    "similarity": similarity,
                }
            )

    # Strategy: always ensure each node is connected to its top 2 neighbors,
    # plus any edges above the threshold. This ensures the graph always shows structure.
    
    # Last-resort fallback: if all similarities are zero, connect notes in time order.
    if not scored_edges:
        for i in range(len(message_ids) - 1):
            scored_edges.append(
                {
                    "source": message_ids[i],
                    "target": message_ids[i + 1],
                    "similarity": 0.1,
                }
            )

    # First, collect edges above threshold.
    threshold_edges = set()
    for edge in scored_edges:
        if edge["similarity"] >= similarity_threshold:
            # Normalize to always use sorted tuple (smaller id first) to avoid duplicates.
            key = (min(edge["source"], edge["target"]), max(edge["source"], edge["target"]))
            threshold_edges.add(key)
    
    # Group scored edges by source node to find top-2 neighbors per node.
    edges_by_source = {}
    for edge in scored_edges:
        src = edge["source"]
        tgt = edge["target"]
        edges_by_source.setdefault(src, []).append(edge)
        # Also index reverse direction so every note can pick top neighbors.
        edges_by_source.setdefault(tgt, []).append(
            {
                "source": tgt,
                "target": src,
                "similarity": edge["similarity"],
            }
        )
    
    # For each node, ensure it has at least 2 edges to its top neighbors.
    mandatory_edges = set()
    for src, edges_for_src in edges_by_source.items():
        # Sort by similarity descending, take top 2.
        top_2 = sorted(edges_for_src, key=lambda e: e["similarity"], reverse=True)[:2]
        for edge in top_2:
            key = (min(src, edge["target"]), max(src, edge["target"]))
            mandatory_edges.add(key)
    
    # Combine threshold edges and mandatory edges.
    final_edge_keys = threshold_edges | mandatory_edges
    
    # Convert back to edge format with similarity scores.
    edges_dict = {}
    for edge in scored_edges:
        key = (min(edge["source"], edge["target"]), max(edge["source"], edge["target"]))
        edges_dict[key] = edge
    
    edges = [
        {
            "source": edges_dict[key]["source"],
            "target": edges_dict[key]["target"],
            "similarity": round(edges_dict[key]["similarity"], 3),
        }
        for key in final_edge_keys
        if key in edges_dict
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
