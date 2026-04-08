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
  const [calendarConnected, setCalendarConnected] = useState(false);
  const [calendarEmail, setCalendarEmail] = useState<string | null>(null);
  const [calendarNotice, setCalendarNotice] = useState<string | null>(null);
  const [calendarActionError, setCalendarActionError] = useState<string | null>(
    null,
  );
  const [calendarBusy, setCalendarBusy] = useState(false);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("kortex_access_token");
    if (savedToken) {
      setAccessToken(savedToken);
      setDraftToken(savedToken);
    }

    const params = new URLSearchParams(window.location.search);
    const connected = params.get("google_calendar");
    const error = params.get("google_calendar_error");

    if (connected === "connected") {
      setCalendarNotice("Google Calendar connected.");
    }

    if (error) {
      setCalendarActionError(error);
    }

    if (connected || error) {
      window.history.replaceState({}, "", window.location.pathname);
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

        const calendarResponse = await axios.get(
          `${apiBase}/google/calendar/status`,
          {
            headers: { Authorization: `Bearer ${accessToken}` },
          },
        );
        setCalendarConnected(Boolean(calendarResponse.data.connected));
        setCalendarEmail(calendarResponse.data.email || null);
      } catch (error: any) {
        setTelegramUserId(null);
        setCalendarConnected(false);
        setCalendarEmail(null);
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
    setCalendarConnected(false);
    setCalendarEmail(null);
    setCalendarNotice(null);
    setCalendarActionError(null);
  };

  const handleConnectGoogleCalendar = async () => {
    try {
      setCalendarBusy(true);
      setCalendarActionError(null);
      const apiBase =
        process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      const response = await axios.post(
        `${apiBase}/google/calendar/connect`,
        {},
        { headers: { Authorization: `Bearer ${accessToken}` } },
      );
      window.location.href = response.data.authorization_url;
    } catch (error: any) {
      setCalendarActionError(
        error?.response?.data?.detail ||
          "Could not start Google Calendar connection.",
      );
      setCalendarBusy(false);
    }
  };

  const handleDisconnectGoogleCalendar = async () => {
    try {
      setCalendarBusy(true);
      setCalendarActionError(null);
      const apiBase =
        process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      await axios.post(
        `${apiBase}/google/calendar/disconnect`,
        {},
        { headers: { Authorization: `Bearer ${accessToken}` } },
      );
      setCalendarConnected(false);
      setCalendarEmail(null);
      setCalendarNotice("Google Calendar disconnected.");
    } catch (error: any) {
      setCalendarActionError(
        error?.response?.data?.detail ||
          "Could not disconnect Google Calendar.",
      );
    } finally {
      setCalendarBusy(false);
    }
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
          <div className={styles.calendarCard}>
            <div>
              <h2>Google Calendar</h2>
              <p className={styles.hint}>
                {calendarConnected
                  ? `Connected${calendarEmail ? ` as ${calendarEmail}` : ""}. Reminders will be mirrored to your primary calendar.`
                  : "Connect your personal Google Calendar to mirror reminders automatically."}
              </p>
            </div>
            <div className={styles.calendarActions}>
              {calendarConnected ? (
                <button
                  onClick={handleDisconnectGoogleCalendar}
                  disabled={calendarBusy}
                >
                  {calendarBusy ? "Disconnecting..." : "Disconnect"}
                </button>
              ) : (
                <button
                  onClick={handleConnectGoogleCalendar}
                  disabled={calendarBusy}
                >
                  {calendarBusy ? "Connecting..." : "Connect Google Calendar"}
                </button>
              )}
            </div>
          </div>
          {calendarNotice && <p className={styles.success}>{calendarNotice}</p>}
          {calendarActionError && (
            <p className={styles.error}>{calendarActionError}</p>
          )}
          <GraphViewer token={accessToken} />
        </div>
      )}
    </main>
  );
}
