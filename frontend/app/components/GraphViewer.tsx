"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import cytoscape from "cytoscape";
import axios from "axios";
import styles from "./GraphViewer.module.css";

interface GraphNode {
  id: string;
  label: string;
  created_at: string;
  degree: number;
}

interface GraphEdge {
  source: string;
  target: string;
  similarity: number;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: { total_messages: number; total_edges: number };
}

// Color palette inspired by Obsidian
const COLORS = {
  background: "#1e1e1e",
  node: "#7d7d7d",
  nodeHighlight: "#5d8eff",
  nodeSelected: "#ff7b5d",
  nodeOrphan: "#4a4a4a",
  edge: "#4a4a4a",
  edgeHighlight: "#5d8eff",
  text: "#d4d4d4",
  textSecondary: "#808080",
  accent: "#5d8eff",
};

// Topic colors for clustering
const TOPIC_COLORS = [
  "#5d8eff", // blue
  "#ff7b5d", // coral
  "#7ee787", // green
  "#ffd166", // yellow
  "#c77dff", // purple
  "#ff9e9e", // pink
  "#6ce0d7", // cyan
  "#ffb86c", // orange
];

export default function GraphViewer({ token }: { token: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [threshold, setThreshold] = useState(0.65);
  const [searchQuery, setSearchQuery] = useState("");
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    visible: boolean;
    x: number;
    y: number;
    title: string;
    created: string;
    links: number;
  }>({
    visible: false,
    x: 0,
    y: 0,
    title: "",
    created: "",
    links: 0,
  });
  const [physicsEnabled, setPhysicsEnabled] = useState(true);

  const apiBase =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  const formatDate = (iso: string) => {
    if (!iso) return "Unknown";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  // Simple clustering based on connected components and modularity
  const assignClusters = (nodes: GraphNode[], edges: GraphEdge[]) => {
    const adjacency = new Map<string, Set<string>>();

    nodes.forEach((n) => adjacency.set(n.id, new Set()));
    edges.forEach((e) => {
      adjacency.get(e.source)?.add(e.target);
      adjacency.get(e.target)?.add(e.source);
    });

    const clusters = new Map<string, number>();
    let currentCluster = 0;
    const visited = new Set<string>();

    // BFS to find connected components
    nodes.forEach((node) => {
      if (!visited.has(node.id)) {
        const queue = [node.id];
        visited.add(node.id);
        clusters.set(node.id, currentCluster);

        while (queue.length > 0) {
          const current = queue.shift()!;
          const neighbors = adjacency.get(current) || new Set();

          neighbors.forEach((neighbor) => {
            if (!visited.has(neighbor)) {
              visited.add(neighbor);
              clusters.set(neighbor, currentCluster);
              queue.push(neighbor);
            }
          });
        }
        currentCluster++;
      }
    });

    return clusters;
  };

  const filterAndLayout = useCallback(() => {
    const cy = cyRef.current;
    if (!cy || !graphData) return;

    // Filter edges based on threshold
    cy.batch(() => {
      cy.edges().forEach((edge: any) => {
        const similarity = edge.data("similarity");
        const isVisible = similarity >= threshold;
        edge.style("opacity", isVisible ? Math.max(0.3, similarity) : 0.05);
        edge.style(
          "line-opacity",
          isVisible ? Math.max(0.3, similarity) : 0.05,
        );
      });

      // Filter nodes based on search
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        cy.nodes().forEach((node: any) => {
          const label = (node.data("fullLabel") || "").toLowerCase();
          const isMatch = label.includes(query);
          node.style("opacity", isMatch ? 1 : 0.2);
          node.style("label", isMatch ? node.data("shortLabel") : "");
        });
      } else {
        cy.nodes().forEach((node: any) => {
          node.style("opacity", 1);
          node.style("label", node.data("shortLabel"));
        });
      }
    });
  }, [graphData, threshold, searchQuery]);

  useEffect(() => {
    filterAndLayout();
  }, [filterAndLayout]);

  useEffect(() => {
    const fetchAndRender = async () => {
      try {
        setLoading(true);
        setError(null);

        if (cyRef.current) {
          cyRef.current.destroy();
          cyRef.current = null;
        }

        const response = await axios.get<GraphData>(`${apiBase}/graph`, {
          params: { similarity_threshold: threshold, limit: 100 },
          headers: { Authorization: `Bearer ${token}` },
        });

        const data = response.data;
        setGraphData(data);

        const clusters = assignClusters(data.nodes, data.edges);

        // Build elements
        const elements = [
          ...data.nodes.map((node) => {
            const cluster = clusters.get(node.id) || 0;
            const isOrphan = node.degree === 0;

            return {
              data: {
                id: node.id,
                shortLabel:
                  node.label.length > 25
                    ? node.label.slice(0, 25) + "..."
                    : node.label,
                fullLabel: node.label,
                created_at: node.created_at,
                degree: node.degree,
                cluster,
                color: isOrphan
                  ? COLORS.nodeOrphan
                  : TOPIC_COLORS[cluster % TOPIC_COLORS.length],
                size: isOrphan ? 8 : 12 + Math.min(node.degree, 8) * 2,
              },
            };
          }),
          ...data.edges.map((edge) => ({
            data: {
              id: `e-${edge.source}-${edge.target}`,
              source: edge.source,
              target: edge.target,
              similarity: edge.similarity,
            },
          })),
        ];

        if (containerRef.current) {
          const cy = cytoscape({
            container: containerRef.current,
            elements,
            minZoom: 0.1,
            maxZoom: 3,
            wheelSensitivity: 0.3,
            style: [
              {
                selector: "node",
                style: {
                  "background-color": "data(color)",
                  width: "data(size)",
                  height: "data(size)",
                  label: "data(shortLabel)",
                  color: COLORS.text,
                  "font-size": "10px",
                  "text-valign": "bottom",
                  "text-halign": "center",
                  "text-margin-y": "4px",
                  "text-background-color": COLORS.background,
                  "text-background-opacity": 0.85,
                  "text-background-padding": "2px 4px",
                  "text-background-shape": "roundrectangle",
                  "border-width": 2,
                  "border-color": COLORS.background,
                  "transition-property":
                    "background-color, border-color, width, height, opacity",
                  "transition-duration": "200ms",
                } as any,
              },
              {
                selector: "node[degree = 0]",
                style: {
                  "background-color": COLORS.nodeOrphan,
                  "border-width": 1,
                  opacity: 0.6,
                },
              },
              {
                selector: "node:selected",
                style: {
                  "background-color": COLORS.nodeSelected,
                  "border-color": "#fff",
                  "border-width": 3,
                  "z-index": 999,
                },
              },
              {
                selector: "node.hover",
                style: {
                  "background-color": COLORS.nodeHighlight,
                  "border-color": "#fff",
                  "border-width": 2,
                  "z-index": 1000,
                },
              },
              {
                selector: "edge",
                style: {
                  "line-color": COLORS.edge,
                  width: "mapData(similarity, 0, 1, 1, 4)",
                  opacity: "mapData(similarity, 0, 1, 0.2, 0.8)",
                  "curve-style": "bezier",
                  "target-arrow-shape": "none",
                },
              },
              {
                selector: "edge:selected",
                style: {
                  "line-color": COLORS.nodeHighlight,
                  opacity: 1,
                  width: 4,
                },
              },
              {
                selector: ".highlighted",
                style: {
                  "background-color": COLORS.nodeHighlight,
                  "line-color": COLORS.edgeHighlight,
                  opacity: 1,
                },
              },
              {
                selector: ".dimmed",
                style: {
                  opacity: 0.15,
                },
              },
            ],
            layout: {
              name: "cose",
              animate: true,
              animationDuration: 800,
              nodeRepulsion: 8000,
              idealEdgeLength: 120,
              edgeElasticity: 200,
              nestingFactor: 0.8,
              gravity: 30,
              numIter: 1000,
              initialTemp: 200,
              coolingFactor: 0.95,
              minTemp: 1.0,
              fit: true,
              padding: 50,
              componentSpacing: 100,
              nodeOverlap: 20,
            } as any,
          });

          cyRef.current = cy;

          // Event handlers
          cy.on("tap", "node", (e: any) => {
            const node = e.target;
            const nodeData = data.nodes.find((n) => n.id === node.id());
            setSelectedNode(nodeData || null);

            // Highlight connected nodes
            cy.elements().removeClass("highlighted dimmed");
            const connected = node.neighborhood().add(node);
            cy.elements().not(connected).addClass("dimmed");
            connected.addClass("highlighted");
          });

          cy.on("tap", (e: any) => {
            if (e.target === cy) {
              setSelectedNode(null);
              cy.elements().removeClass("highlighted dimmed");
            }
          });

          cy.on("mouseover", "node", (e: any) => {
            const node = e.target;
            setHoveredNode(node.id());
            node.addClass("hover");

            const rendered = node.renderedPosition();
            setTooltip({
              visible: true,
              x: rendered.x + 14,
              y: rendered.y + 14,
              title: node.data("fullLabel") || "Untitled",
              created: formatDate(node.data("created_at")),
              links: Number(node.data("degree") || 0),
            });

            // Show larger label on hover
            const fullLabel = node.data("fullLabel");
            if (fullLabel && fullLabel.length > 25) {
              node.style(
                "label",
                fullLabel.length > 50
                  ? fullLabel.slice(0, 50) + "..."
                  : fullLabel,
              );
            }
          });

          cy.on("mouseout", "node", (e: any) => {
            const node = e.target;
            node.removeClass("hover");
            setHoveredNode(null);
            setTooltip((t) => ({ ...t, visible: false }));

            // Restore short label
            node.style("label", node.data("shortLabel"));
          });

          cy.on("pan zoom", () => {
            setTooltip((t) => ({ ...t, visible: false }));
          });

          // Pan to selected node from sidebar
          if (selectedNode) {
            const node = cy.getElementById(selectedNode.id);
            if (node.length > 0) {
              cy.animate({
                fit: { eles: node, padding: 100 },
                duration: 500,
              });
            }
          }
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
  }, [token, threshold, apiBase]);

  const handleZoomIn = () => {
    cyRef.current?.animate({
      zoom: { level: cyRef.current.zoom() * 1.2, position: { x: 0, y: 0 } },
      duration: 200,
    });
  };

  const handleZoomOut = () => {
    cyRef.current?.animate({
      zoom: { level: cyRef.current.zoom() / 1.2, position: { x: 0, y: 0 } },
      duration: 200,
    });
  };

  const handleFit = () => {
    cyRef.current?.fit(undefined, 50);
  };

  const handleCenterOnNode = (nodeId: string) => {
    const cy = cyRef.current;
    if (!cy) return;

    const node = cy.getElementById(nodeId);
    if (node.length > 0) {
      const nodeData = graphData?.nodes.find((n) => n.id === nodeId);
      setSelectedNode(nodeData || null);
      cy.animate({
        fit: { eles: node, padding: 150 },
        duration: 400,
      });

      // Select the node
      cy.elements().unselect();
      node.select();

      // Highlight neighbors
      cy.elements().removeClass("highlighted dimmed");
      const connected = node.neighborhood().add(node);
      cy.elements().not(connected).addClass("dimmed");
      connected.addClass("highlighted");
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.graphArea}>
        {/* Controls overlay */}
        <div className={styles.controlsOverlay}>
          <div className={styles.controlGroup}>
            <button
              onClick={handleZoomIn}
              title="Zoom in"
              className={styles.controlBtn}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
                <path d="M11 8v6M8 11h6" />
              </svg>
            </button>
            <button
              onClick={handleZoomOut}
              title="Zoom out"
              className={styles.controlBtn}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
                <path d="M8 11h6" />
              </svg>
            </button>
            <button
              onClick={handleFit}
              title="Fit to screen"
              className={styles.controlBtn}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Search overlay */}
        <div className={styles.searchOverlay}>
          <input
            type="text"
            placeholder="Search notes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className={styles.clearBtn}
            >
              ×
            </button>
          )}
        </div>

        {/* Graph container */}
        <div className={styles.container} ref={containerRef} />
        {tooltip.visible && (
          <div
            className={styles.nodeTooltip}
            style={{ left: tooltip.x, top: tooltip.y }}
          >
            <p className={styles.nodeTooltipTitle}>{tooltip.title}</p>
            <p>
              <strong>Created:</strong> {tooltip.created}
            </p>
            <p>
              <strong>Links:</strong> {tooltip.links}
            </p>
          </div>
        )}
      </div>

      {/* Sidebar */}
      <div className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <h2>Graph View</h2>
          <p className={styles.subtitle}>
            Visualize your knowledge connections
          </p>
        </div>

        {/* Stats */}
        {graphData?.stats && (
          <div className={styles.statsSection}>
            <div className={styles.statGrid}>
              <div className={styles.statItem}>
                <span className={styles.statValue}>
                  {graphData.stats.total_messages}
                </span>
                <span className={styles.statLabel}>Notes</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}>
                  {graphData.stats.total_edges}
                </span>
                <span className={styles.statLabel}>Links</span>
              </div>
            </div>
          </div>
        )}

        {/* Threshold control */}
        <div className={styles.section}>
          <h3>Link Strength</h3>
          <div className={styles.sliderContainer}>
            <input
              type="range"
              min="0.5"
              max="0.95"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              className={styles.slider}
            />
            <div className={styles.sliderLabels}>
              <span>More links</span>
              <span className={styles.thresholdValue}>
                {threshold.toFixed(2)}
              </span>
              <span>Stronger only</span>
            </div>
          </div>
        </div>

        {/* Selected node details */}
        {selectedNode ? (
          <div className={styles.nodeDetails}>
            <h3>Note Details</h3>
            <div className={styles.nodeContent}>
              <p className={styles.nodeText}>{selectedNode.label}</p>
              <div className={styles.nodeMeta}>
                <span className={styles.metaItem}>
                  <strong>Created:</strong>{" "}
                  {formatDate(selectedNode.created_at)}
                </span>
                <span className={styles.metaItem}>
                  <strong>Connections:</strong> {selectedNode.degree}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className={styles.section}>
            <h3>Recent Notes</h3>
            {loading ? (
              <p className={styles.loadingText}>Loading...</p>
            ) : error ? (
              <p className={styles.errorText}>{error}</p>
            ) : (
              <div className={styles.noteList}>
                {graphData?.nodes.slice(0, 10).map((node) => (
                  <button
                    key={node.id}
                    onClick={() => handleCenterOnNode(node.id)}
                    className={styles.noteItem}
                  >
                    <span className={styles.noteText}>
                      {node.label.length > 50
                        ? node.label.slice(0, 50) + "..."
                        : node.label}
                    </span>
                    <span className={styles.noteMeta}>
                      {node.degree} link{node.degree !== 1 ? "s" : ""}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Instructions */}
        <div className={styles.section}>
          <h3>How to Use</h3>
          <ul className={styles.helpList}>
            <li>
              <strong>Click</strong> a note to see its connections
            </li>
            <li>
              <strong>Drag</strong> to rearrange the graph
            </li>
            <li>
              <strong>Scroll</strong> to zoom in/out
            </li>
            <li>
              <strong>Search</strong> to find specific notes
            </li>
            <li>Colors indicate related clusters</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
