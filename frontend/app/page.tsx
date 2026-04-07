"use client";

import { useState } from "react";
import GraphViewer from "./components/GraphViewer";
import styles from "./page.module.css";

export default function Home() {
  const [userId, setUserId] = useState<string>("");
  const [showGraph, setShowGraph] = useState<boolean>(false);

  const handleViewGraph = () => {
    if (userId.trim()) {
      setShowGraph(true);
    }
  };

  return (
    <main className={styles.container}>
      <header className={styles.header}>
        <h1>🧠 Kortex Context Graph</h1>
        <p>Visualize your second brain's semantic knowledge</p>
      </header>

      {!showGraph ? (
        <div className={styles.inputSection}>
          <div className={styles.card}>
            <h2>Enter Your Telegram User ID</h2>
            <p className={styles.hint}>
              This is the numeric Telegram ID, not your username.
              <br />
              You can find it in Supabase: SELECT telegram_user_id FROM messages
              LIMIT 1;
            </p>
            <div className={styles.inputGroup}>
              <input
                type="number"
                placeholder="e.g., 1183743006"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleViewGraph()}
              />
              <button onClick={handleViewGraph}>View Graph</button>
            </div>
          </div>
        </div>
      ) : (
        <div className={styles.graphSection}>
          <div className={styles.controls}>
            <button onClick={() => setShowGraph(false)}>← Back</button>
            <span className={styles.userId}>User ID: {userId}</span>
          </div>
          <GraphViewer userId={parseInt(userId)} />
        </div>
      )}
    </main>
  );
}
