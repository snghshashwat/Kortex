"use client";

import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import axios from "axios";
import styles from "./GraphViewer.module.css";

interface GraphData {
  nodes: Array<{ id: string; label: string; created_at: string }>;
  edges: Array<{ source: string; target: string; similarity: number }>;
  stats: { total_messages: number; total_edges: number };
}

export default function GraphViewer({ userId }: { userId: number }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<{
    total_messages: number;
    total_edges: number;
  } | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0.7);

  useEffect(() => {
    const fetchAndRender = async () => {
      try {
        setLoading(true);
        setError(null);

        const apiBase =
          process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
        const response = await axios.get<GraphData>(`${apiBase}/graph`, {
          params: {
            user_id: userId,
            similarity_threshold: threshold,
            limit: 50,
          },
        });

        const graphData = response.data;
        setStats(graphData.stats);

        // Create cytoscape elements
        const elements = [
          ...graphData.nodes.map((node) => ({
            data: {
              id: node.id,
              label: node.label,
            },
          })),
          ...graphData.edges.map((edge) => ({
            data: {
              source: edge.source,
              target: edge.target,
              similarity: edge.similarity,
            },
          })),
        ];

        // Initialize cytoscape
        if (containerRef.current) {
          const cy = cytoscape({
            container: containerRef.current,
            elements,
            style: [
              {
                selector: "node",
                style: {
                  "background-color": "#667eea",
                  label: "data(label)",
                  "text-valign": "center",
                  "text-halign": "center",
                  "font-size": 10,
                  color: "#fff",
                  width: "mapData(degree, 0, 10, 30, 50)",
                  height: "mapData(degree, 0, 10, 30, 50)",
                  "text-wrap": "wrap",
                  "text-max-width": 100,
                  padding: 10,
                },
              },
              {
                selector: "node:selected",
                style: {
                  "background-color": "#764ba2",
                  "border-width": 3,
                  "border-color": "#fff",
                },
              },
              {
                selector: "edge",
                style: {
                  "line-color": "#555",
                  "target-arrow-color": "#555",
                  "target-arrow-shape": "triangle",
                  label: "data(similarity)",
                  "font-size": 8,
                  color: "#999",
                  "edge-text-rotation": "autorotate",
                  width: "mapData(similarity, 0, 1, 1, 3)",
                },
              },
              {
                selector: "edge:selected",
                style: {
                  "line-color": "#667eea",
                  "target-arrow-color": "#667eea",
                  width: 4,
                  color: "#667eea",
                },
              },
            ],
            layout: {
              name: "cose",
              directed: false,
              animate: true,
              animationDuration: 500,
              avoidOverlap: true,
              nodeSpacing: 10,
              fit: true,
              padding: 50,
            },
          });

          cyRef.current = cy;

          // Event listeners
          cy.on("tap", "node", (e: any) => {
            setSelectedNode(e.target.id());
          });

          cy.on("tap", "edge", (e: any) => {
            setSelectedNode(e.target.source().id());
          });

          cy.on("tap", (e: any) => {
            if (e.target === cy) {
              setSelectedNode(null);
            }
          });
        }

        setLoading(false);
      } catch (err: any) {
        setError(err.message || "Failed to load graph");
        setLoading(false);
      }
    };

    fetchAndRender();
  }, [userId, threshold]);

  const getNodeText = () => {
    if (!selectedNode) return null;
    const node = stats ? "(Hover over a node for details)" : null;
    return node;
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.container} ref={containerRef} />

      <div className={styles.sidebar}>
        <div className={styles.panel}>
          <h3>Graph Statistics</h3>
          {stats && (
            <div className={styles.stats}>
              <p>
                <strong>Total Notes:</strong> {stats.total_messages}
              </p>
              <p>
                <strong>Connections:</strong> {stats.total_edges}
              </p>
            </div>
          )}

          <h3>Similarity Threshold</h3>
          <div className={styles.thresholdControl}>
            <input
              type="range"
              min="0.5"
              max="0.95"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
            />
            <span>{threshold.toFixed(2)}</span>
          </div>
          <p className={styles.hint}>
            Higher threshold = fewer, stronger connections
          </p>

          <h3>How to use</h3>
          <ul className={styles.instructions}>
            <li>Click nodes to select them</li>
            <li>Hover over edges to see similarity scores</li>
            <li>Adjust threshold to filter weak connections</li>
            <li>Zoom and pan to explore clusters</li>
          </ul>

          {loading && <p className={styles.loading}>Loading...</p>}
          {error && <p className={styles.error}>Error: {error}</p>}

          {selectedNode && (
            <div className={styles.selectedPanel}>
              <h3>Selected Note</h3>
              <p className={styles.nodeId}>ID: {selectedNode}</p>
              <p className={styles.hint}>
                This note connects to related topics based on semantic
                similarity.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
