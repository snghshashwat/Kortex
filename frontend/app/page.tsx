"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import GraphViewer from "./components/GraphViewer";
import styles from "./page.module.css";

export default function Home() {
  const [draftToken, setDraftToken] = useState<string>("");
  const [accessToken, setAccessToken] = useState<string>("");
  const [telegramUserId, setTelegramUserId] = useState<number | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("kortex_access_token");
    if (savedToken) {
      setAccessToken(savedToken);
      setDraftToken(savedToken);
    }
  }, []);

  useEffect(() => {
    const validateToken = async () => {
      if (!accessToken) {
        setTelegramUserId(null);
        return;
      }

      try {
        const apiBase =
          process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
        const response = await axios.get(`${apiBase}/auth/me`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        setTelegramUserId(response.data.telegram_user_id);
        setAuthError(null);
        window.localStorage.setItem("kortex_access_token", accessToken);
      } catch (error: any) {
        setTelegramUserId(null);
        setAuthError(
          error?.response?.data?.detail || "Token is invalid or expired.",
        );
      }
    };

    validateToken();
  }, [accessToken]);

  const handleUnlock = () => {
    const trimmedToken = draftToken.trim();
    if (trimmedToken) {
      setAccessToken(trimmedToken);
    }
  };

  const handleLogout = () => {
    window.localStorage.removeItem("kortex_access_token");
    setAccessToken("");
    setDraftToken("");
    setTelegramUserId(null);
    setAuthError(null);
  };

  return (
    <main className={styles.container}>
      <header className={styles.header}>
        <h1>🧠 Kortex Context Graph</h1>
        <p>Visualize your second brain's semantic knowledge, privately</p>
      </header>

      {!accessToken ? (
        <div className={styles.inputSection}>
          <div className={styles.card}>
            <h2>Unlock Your Private Graph</h2>
            <p className={styles.hint}>
              In Telegram, send <strong>/link</strong> to Kortex. Copy the
              access token it returns, then paste it here.
              <br />
              The same token is required for graph, search, reminders, and note
              access.
            </p>
            <div className={styles.inputGroup}>
              <input
                type="password"
                placeholder="Paste your access token"
                value={draftToken}
                onChange={(e) => setDraftToken(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleUnlock()}
              />
              <button onClick={handleUnlock}>Unlock</button>
            </div>
            {authError && <p className={styles.error}>{authError}</p>}
          </div>
        </div>
      ) : (
        <div className={styles.graphSection}>
          <div className={styles.controls}>
            <button onClick={handleLogout}>Log out</button>
            <span className={styles.userId}>
              {telegramUserId
                ? `Telegram user: ${telegramUserId}`
                : "Verifying token..."}
            </span>
          </div>
          <GraphViewer token={accessToken} />
        </div>
      )}
    </main>
  );
}
