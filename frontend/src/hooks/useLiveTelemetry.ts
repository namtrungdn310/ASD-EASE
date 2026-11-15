import { useEffect, useRef, useState } from "react";
import { parseTelemetry } from "../utils/parseTelemetry";
import { getConnectionStatus, updateTelemetryStream } from "../utils/telemetryStream";
import type { TelemetryStream } from "../utils/telemetryStream";
import { openLocalSession } from "../utils/localSession";
import { listDevices } from "../api/devices";
import { readDevicePreference, rememberDevice } from "../utils/devicePreference";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/api/v1/ws/live";
const RECONNECT_DELAY_MS = 1500;
const CONNECT_TIMEOUT_MS = 10000;
const HEARTBEAT_IDLE_MS = 10000;
const HEARTBEAT_TIMEOUT_MS = 5000;
const STATUS_CHECK_INTERVAL_MS = 500;
const DEVICE_WAIT_TIMEOUT_MS = 15000;

export function useLiveTelemetry(staleTimeoutMs = 5000) {
  const streamsRef = useRef(new Map<string, TelemetryStream>());
  const [streams, setStreams] = useState(streamsRef.current);
  const [preference] = useState(readDevicePreference);
  const [knownDeviceIds, setKnownDeviceIds] = useState(preference.ids);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(preference.selected);
  const [monitoringDeviceId, setMonitoringDeviceId] = useState<string | null>(null);
  const [connectionAttempt, setConnectionAttempt] = useState(0);
  const [connectionTimedOut, setConnectionTimedOut] = useState(false);
  const [backendConnected, setBackendConnected] = useState(false);
  const [freshDeviceIds, setFreshDeviceIds] = useState(new Set<string>());
  const [nowMs, setNowMs] = useState(() => performance.now());
  const attemptStartedAt = useRef<number | null>(null);

  useEffect(() => {
    let controller: AbortController | null = null;
    const refreshDevices = () => {
      controller?.abort();
      const current = new AbortController();
      controller = current;
      void listDevices(AbortSignal.any([current.signal, AbortSignal.timeout(8000)]))
      .then(rows => {
        if (current.signal.aborted) return;
        const ids = rows.map(row => row.device_id);
        setKnownDeviceIds(ids);
        setSelectedDeviceId(previous => previous && ids.includes(previous) ? previous : ids[0] ?? null);
      }).catch(() => { /* Danh mục lỗi không chặn Dashboard; thử lại định kỳ. */ });
    };
    refreshDevices();
    const timer = window.setInterval(refreshDevices, 15000);
    return () => { window.clearInterval(timer); controller?.abort(); };
  }, [backendConnected]);

  useEffect(() => {
    if (!monitoringDeviceId || monitoringDeviceId !== selectedDeviceId) {
      setBackendConnected(false);
      setFreshDeviceIds(new Set());
      return;
    }
    let active = true;
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let openingTimer: number | undefined;
    let authRequest: AbortController | null = null;
    let attemptId = 0;
    let attempted = false;
    let lastTransportAt = 0;
    let pingSentAt: number | null = null;
    let freshDevices = new Set<string>();

    const clearOpeningTimer = () => {
      if (openingTimer !== undefined) window.clearTimeout(openingTimer);
      openingTimer = undefined;
    };
    const retire = () => {
      attemptId++;
      authRequest?.abort();
      authRequest = null;
      clearOpeningTimer();
      pingSentAt = null;
      const previous = socket;
      socket = null;
      if (previous) {
        previous.onopen = previous.onmessage = previous.onerror = previous.onclose = null;
        try { previous.close(); } catch { /* Socket đã hỏng; vẫn phải cho phép thử lại. */ }
      }
      if (active) setBackendConnected(false);
    };
    const scheduleReconnect = () => {
      if (!active || retryTimer !== undefined) return;
      retryTimer = window.setTimeout(() => {
        retryTimer = undefined;
        void connect();
      }, RECONNECT_DELAY_MS);
    };
    const reconnectLater = () => { retire(); scheduleReconnect(); };

    const connect = async () => {
      if (!active || socket || authRequest) return;
      const id = ++attemptId;
      const renewSession = attempted && import.meta.env.DEV;
      attempted = true;
      if (renewSession) {
        const request = new AbortController();
        authRequest = request;
        try {
          await openLocalSession(request.signal);
        } catch {
          if (active && attemptId === id) { authRequest = null; scheduleReconnect(); }
          return;
        } finally {
          if (authRequest === request) authRequest = null;
        }
      }
      if (!active || attemptId !== id) return;
      let current: WebSocket;
      try { current = new WebSocket(WS_URL); }
      catch { setBackendConnected(false); scheduleReconnect(); return; }
      socket = current;
      const isCurrent = () => active && socket === current;
      openingTimer = window.setTimeout(() => {
        if (isCurrent()) reconnectLater();
      }, CONNECT_TIMEOUT_MS);
      current.onopen = () => {
        if (!isCurrent()) return;
        clearOpeningTimer();
        lastTransportAt = performance.now();
        pingSentAt = null;
        freshDevices = new Set();
        setFreshDeviceIds(new Set());
        setBackendConnected(true);
      };
      current.onclose = () => { if (isCurrent()) reconnectLater(); };
      current.onerror = () => { if (isCurrent()) reconnectLater(); };
      current.onmessage = event => {
        if (!isCurrent() || current.readyState !== WebSocket.OPEN || typeof event.data !== "string") return;
        const receivedAtMs = performance.now();
        lastTransportAt = receivedAtMs;
        pingSentAt = null;
        if (event.data === "pong") return; // Liveness không làm dữ liệu cảm biến mới trở lại.
        const telemetry = parseTelemetry(event.data);
        if (telemetry === null || telemetry.data_origin !== "DEVICE" || telemetry.device_id !== monitoringDeviceId) return;
        const previous = streamsRef.current.get(telemetry.device_id) ?? null;
        const next = updateTelemetryStream(previous, telemetry, receivedAtMs);
        if (next === previous) return;
        const updated = new Map(streamsRef.current);
        updated.set(telemetry.device_id, next);
        streamsRef.current = updated;
        setStreams(updated);
        if (!freshDevices.has(telemetry.device_id)) {
          freshDevices.add(telemetry.device_id);
          setFreshDeviceIds(new Set(freshDevices));
        }
        setConnectionTimedOut(false);
        setNowMs(receivedAtMs);
      };
    };

    const checkTransport = (now: number) => {
      if (!socket || socket.readyState !== WebSocket.OPEN) return;
      if (pingSentAt !== null) {
        if (now - pingSentAt >= HEARTBEAT_TIMEOUT_MS) reconnectLater();
      } else if (now - lastTransportAt >= HEARTBEAT_IDLE_MS) {
        try { socket.send("ping"); pingSentAt = now; }
        catch { reconnectLater(); }
      }
    };
    const resume = () => {
      if (!active || document.visibilityState === "hidden") return;
      const now = performance.now();
      setNowMs(now);
      if (authRequest || (socket?.readyState === WebSocket.OPEN && now - lastTransportAt < HEARTBEAT_IDLE_MS)) return;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
      retryTimer = undefined;
      retire();
      void connect();
    };
    const pageshow = (event: PageTransitionEvent) => { if (event.persisted) resume(); };
    const statusTimer = window.setInterval(() => {
      const now = performance.now();
      setNowMs(now);
      checkTransport(now);
    }, STATUS_CHECK_INTERVAL_MS);
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("online", resume);
    window.addEventListener("pageshow", pageshow);
    void connect();

    return () => {
      active = false;
      window.clearInterval(statusTimer);
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
      document.removeEventListener("visibilitychange", resume);
      window.removeEventListener("online", resume);
      window.removeEventListener("pageshow", pageshow);
      retire();
    };
  }, [monitoringDeviceId, selectedDeviceId, connectionAttempt]);

  useEffect(() => {
    if (!monitoringDeviceId || monitoringDeviceId !== selectedDeviceId || attemptStartedAt.current === null) return;
    const timer = window.setInterval(() => {
      const now = performance.now();
      setNowMs(now);
      if (now - attemptStartedAt.current! >= DEVICE_WAIT_TIMEOUT_MS && !freshDeviceIds.has(monitoringDeviceId)) {
        setConnectionTimedOut(true);
      }
    }, STATUS_CHECK_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [monitoringDeviceId, selectedDeviceId, connectionAttempt, freshDeviceIds]);

  const deviceIds = [...new Set([...knownDeviceIds, ...streams.keys()])];
  const currentDeviceId = selectedDeviceId ?? deviceIds[0] ?? null;
  const deviceListKey = deviceIds.join("\0");
  const hasSelectedStream = currentDeviceId !== null && streams.has(currentDeviceId);
  useEffect(() => {
    if (currentDeviceId && (selectedDeviceId || hasSelectedStream)) rememberDevice(currentDeviceId, deviceIds);
  }, [currentDeviceId, selectedDeviceId, hasSelectedStream, deviceListKey]);
  const stream = currentDeviceId === null ? null : streams.get(currentDeviceId) ?? null;
  const streamForCurrentConnection = currentDeviceId !== null && freshDeviceIds.has(currentDeviceId) ? stream : null;
  const monitoring = monitoringDeviceId === currentDeviceId && currentDeviceId !== null;
  const connectionStatus = monitoring
    ? getConnectionStatus(backendConnected, streamForCurrentConnection, nowMs, staleTimeoutMs)
    : "backend_disconnected";
  const chooseDevice = (deviceId: string | null) => {
    if (deviceId !== currentDeviceId) {
      attemptStartedAt.current = null;
      setConnectionTimedOut(false);
      setMonitoringDeviceId(null);
      setSelectedDeviceId(deviceId);
    }
  };
  const connectDevice = () => {
    if (!currentDeviceId) return;
    attemptStartedAt.current = performance.now();
    setConnectionTimedOut(false);
    setMonitoringDeviceId(currentDeviceId);
    setConnectionAttempt(value => value + 1);
  };
  const disconnectDevice = () => {
    attemptStartedAt.current = null;
    setConnectionTimedOut(false);
    setMonitoringDeviceId(null);
  };
  return {
    telemetry: stream?.telemetry ?? null, points: stream?.points ?? [],
    historySeconds: stream ? (stream.telemetry.timestamp_ms - stream.firstTimestampMs) / 1000 : 0,
    connected: connectionStatus === "live", backendConnected, connectionStatus,
    deviceIds, selectedDeviceId: currentDeviceId, setSelectedDeviceId: chooseDevice,
    monitoring, connectionTimedOut, connectDevice, disconnectDevice,
  };
}
