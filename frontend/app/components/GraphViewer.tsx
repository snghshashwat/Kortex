"use client";

import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import axios from "axios";
import styles from "./GraphViewer.module.css";

interface GraphData {
  nodes: Array<{
    id: string;
    label: string;
    created_at: string;
    degree: number;
  }>;
  edges: Array<{ source: string; target: string; similarity: number }>;
  stats: { total_messages: number; total_edges: number };
}

export default function GraphViewer({ token }: { token: string }) {
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
  const [topicCount, setTopicCount] = useState(0);
  const [tooltip, setTooltip] = useState<{
    visible: boolean;
    x: number;
    y: number;
    title: string;
    topic: string;
    createdAt: string;
    degree: number;
  }>({
    visible: false,
    x: 0,
    y: 0,
    title: "",
    topic: "",
    createdAt: "",
    degree: 0,
  });

  const deriveTopic = (text: string) => {
    const t = text.toLowerCase();
    if (/(startup|product|roadmap|idea|plan|build)/.test(t)) return "Product";
    if (/(fastapi|backend|api|auth|routing|database|pgvector)/.test(t))
      return "Engineering";
    if (
      /(semantic|similarity|embedding|cluster|graph|context|ai|memory)/.test(t)
    )
      return "AI / Knowledge";
    if (/(reminder|calendar|weekly|tomorrow|schedule)/.test(t))
      return "Reminders";
    return "General";
  };

  const formatDate = (iso: string) => {
    if (!iso) return "Unknown";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  };

  useEffect(() => {
    const fetchAndRender = async () => {
      try {
        setLoading(true);
        setError(null);

        if (cyRef.current) {
          cyRef.current.destroy();
          cyRef.current = null;
        }

        if (containerRef.current) {
          containerRef.current.innerHTML = "";
        }

        const apiBase =
          process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
        const response = await axios.get<GraphData>(`${apiBase}/graph`, {
          params: {
            similarity_threshold: threshold,
            limit: 50,
          },
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        const graphData = response.data;
        setStats(graphData.stats);

        const topicMap = new Map<string, string>();
        const topicNodes: Array<{ data: any }> = [];
        const taskNodes = graphData.nodes.map((node) => {
          const topic = deriveTopic(node.label);
          const topicId = `topic::${topic.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

          if (!topicMap.has(topicId)) {
            topicMap.set(topicId, topic);
            topicNodes.push({
              data: {
                id: topicId,
                label: topic,
                type: "topic",
              },
            });
          }

          return {
            data: {
              id: node.id,
              shortLabel: node.label,
              fullLabel: node.label,
              created_at: node.created_at,
              degree: node.degree,
              topic,
              type: "task",
              parent: topicId,
              base_size: 14 + Math.min(node.degree, 6) * 2,
            },
          };
        });

        setTopicCount(topicNodes.length);

        const semanticEdges = graphData.edges.map((edge) => ({
          data: {
            id: `sem::${edge.source}::${edge.target}`,
            source: edge.source,
            target: edge.target,
            similarity: edge.similarity,
            type: "semantic",
          },
        }));

        const elements = [...topicNodes, ...taskNodes, ...semanticEdges];

        // Initialize cytoscape
        if (containerRef.current) {
          const cy = cytoscape({
            container: containerRef.current,
            elements,
            style: [
              {
                selector: "node[type = 'topic']",
                style: {
                  shape: "round-rectangle",
                  "background-color": "#334155",
                  "background-opacity": 0.55,
                  label: "data(label)",
                  color: "#cbd5e1",
                  "font-size": "12px",
                  "font-weight": 600,
                  "text-halign": "center",
                  "text-valign": "top",
                  "text-margin-y": "-8px",
                  "border-color": "#475569",
                  "border-width": 1,
                  padding: "26px",
                },
              },
              {
                selector: "node[type = 'task']",
                style: {
                  "background-color": "#60a5fa",
                  width: "data(base_size)",
                  height: "data(base_size)",
                  label: "",
                  "border-width": 1,
                  "border-color": "#1e293b",
                },
              },
              {
                selector: "node[type = 'task'][degree = 0]",
                style: {
                  "background-color": "#64748b",
                },
              },
              {
                selector: "node[type = 'task']:selected",
                style: {
                  "background-color": "#f59e0b",
                  "border-width": 3,
                  "border-color": "#fef3c7",
                },
              },
              {
                selector: "edge[type = 'semantic']",
                style: {
                  "line-color": "#64748b",
                  "line-opacity": 0.9,
                  label: "",
                  "font-size": "8px",
                  color: "#cbd5e1",
                  width: "mapData(similarity, 0, 1, 1, 5)",
                  "curve-style": "bezier",
                } as any,
              },
              {
                selector: "edge:selected",
                style: {
                  "line-color": "#f59e0b",
                  width: "4px",
                  color: "#f59e0b",
                } as any,
              },
            ],
            layout: {
              name: "cose",
              directed: false,
              animate: true,
              animationDuration: 500,
              avoidOverlap: true,
              nodeRepulsion: 12000,
              idealEdgeLength: 140,
              edgeElasticity: 150,
              nodeSpacing: 20,
              fit: true,
              padding: 50,
            } as any,
          });

          cyRef.current = cy;

          const resizeTaskDotsByZoom = () => {
            const zoom = cy.zoom();
            const scale = Math.max(0.8, Math.min(2.2, zoom));
            cy.batch(() => {
              cy.nodes("[type = 'task']").forEach((n: any) => {
                const base = Number(n.data("base_size")) || 14;
                const size = Math.max(10, Math.min(56, base * scale));
                n.style("width", size);
                n.style("height", size);
              });
            });
          };

          resizeTaskDotsByZoom();
          cy.on("zoom", resizeTaskDotsByZoom);

          // Event listeners
          cy.on("tap", "node", (e: any) => {
            const node = e.target;
            if (node.data("type") === "task") {
              setSelectedNode(node.id());
            }
          });

          cy.on("tap", "edge", (e: any) => {
            setSelectedNode(e.target.source().id());
          });

          cy.on("mouseover", "node[type = 'task']", (e: any) => {
            const node = e.target;
            const pos = node.renderedPosition();
            setTooltip({
              visible: true,
              x: pos.x + 16,
              y: pos.y + 16,
              title: node.data("fullLabel") || "Untitled",
              topic: node.data("topic") || "General",
              createdAt: formatDate(node.data("created_at")),
              degree: Number(node.data("degree") || 0),
            });
          });

          cy.on("mouseout", "node[type = 'task']", () => {
            setTooltip((t) => ({ ...t, visible: false }));
          });

          cy.on("pan zoom", () => {
            setTooltip((t) => ({ ...t, visible: false }));
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

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [token, threshold]);

  const getNodeText = () => {
    if (!selectedNode) return null;
    const node = stats ? "(Hover over a node for details)" : null;
    return node;
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.containerWrap}>
        <div className={styles.container} ref={containerRef} />
        {tooltip.visible && (
          <div
            className={styles.tooltip}
            style={{ left: tooltip.x, top: tooltip.y }}
          >
            <p className={styles.tooltipTitle}>{tooltip.title}</p>
            <p>
              <strong>Topic:</strong> {tooltip.topic}
            </p>
            <p>
              <strong>Created:</strong> {tooltip.createdAt}
            </p>
            <p>
              <strong>Links:</strong> {tooltip.degree}
            </p>
          </div>
        )}
      </div>

      <div className={styles.sidebar}>
        <div className={styles.panel}>
          <h3>Graph Statistics</h3>
          {stats && (
            <div className={styles.stats}>
              <p>
                <strong>Total Notes:</strong> {stats.total_messages}
              </p>
              <p>
                <strong>Topics:</strong> {topicCount}
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
            <li>Topic containers group related tasks</li>
            <li>Task dots grow as you zoom in</li>
            <li>Hover a task dot for details</li>
            <li>Adjust threshold to filter semantic links</li>
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
