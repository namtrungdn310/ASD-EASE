import { useEffect, useState } from "react";
import { parseTelemetry } from "../utils/parseTelemetry";
import {
  getConnectionStatus,
  updateTelemetryStream,
} from "../utils/telemetryStream";
import type { TelemetryStream } from "../utils/telemetryStream";

const WS_URL =
  import.meta.env.VITE_WS_URL ??
  "ws://localhost:8000/api/v1/ws/live";

const RECONNECT_DELAY_MS = 1500;
const STATUS_CHECK_INTERVAL_MS = 500;

export function useLiveTelemetry(staleTimeoutMs = 5000) {
  const [streams, setStreams] = useState<
    Map<string, TelemetryStream>
  >(() => new Map());

  const [selectedDeviceId, setSelectedDeviceId] = useState<
    string | null
  >(null);

  const [backendConnected, setBackendConnected] = useState(false);

  const [connectionStartedAtMs, setConnectionStartedAtMs] =
    useState<number | null>(null);

  const [nowMs, setNowMs] = useState(() => performance.now());

  useEffect(() => {
    let active = true;
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;

    const scheduleReconnect = () => {
      if (!active || retryTimer !== undefined) {
        return;
      }

      retryTimer = window.setTimeout(() => {
        retryTimer = undefined;
        connect();
      }, RECONNECT_DELAY_MS);
    };

    const connect = () => {
      if (!active) {
        return;
      }

      let current: WebSocket;

      try {
        current = new WebSocket(WS_URL);
      } catch {
        setBackendConnected(false);
        scheduleReconnect();
        return;
      }

      socket = current;

      const isCurrentSocket = () =>
        active && socket === current;

      current.onopen = () => {
        if (!isCurrentSocket()) {
          return;
        }

        setConnectionStartedAtMs(performance.now());
        setBackendConnected(true);
      };

      current.onclose = () => {
        if (!isCurrentSocket()) {
          return;
        }

        socket = null;
        setBackendConnected(false);
        scheduleReconnect();
      };

      current.onerror = () => {
        if (isCurrentSocket()) {
          current.close();
        }
      };

      current.onmessage = (event) => {
        if (
          !isCurrentSocket() ||
          current.readyState !== WebSocket.OPEN ||
          typeof event.data !== "string"
        ) {
          return;
        }

        const telemetry = parseTelemetry(event.data);

        if (telemetry === null) {
          return;
        }

        const receivedAtMs = performance.now();

        setStreams((previous) => {
          const previousStream =
            previous.get(telemetry.device_id) ?? null;

          const nextStream = updateTelemetryStream(
            previousStream,
            telemetry,
            receivedAtMs
          );

          if (nextStream === previousStream) {
            return previous;
          }

          const next = new Map(previous);
          next.set(telemetry.device_id, nextStream);

          return next;
        });

        setNowMs(receivedAtMs);
      };
    };

    const statusTimer = window.setInterval(() => {
      setNowMs(performance.now());
    }, STATUS_CHECK_INTERVAL_MS);

    connect();

    return () => {
      active = false;

      window.clearInterval(statusTimer);

      if (retryTimer !== undefined) {
        window.clearTimeout(retryTimer);
      }

      if (socket !== null) {
        socket.onopen = null;
        socket.onclose = null;
        socket.onerror = null;
        socket.onmessage = null;
        socket.close();
        socket = null;
      }
    };
  }, []);

  const deviceIds = Array.from(streams.keys());

  const currentDeviceId =
    selectedDeviceId ?? deviceIds[0] ?? null;

  const stream =
    currentDeviceId === null
      ? null
      : streams.get(currentDeviceId) ?? null;

  const streamForCurrentConnection =
    stream !== null &&
    connectionStartedAtMs !== null &&
    stream.receivedAtMs >= connectionStartedAtMs
      ? stream
      : null;

  const connectionStatus = getConnectionStatus(
    backendConnected,
    streamForCurrentConnection,
    nowMs,
    staleTimeoutMs
  );

  return {
    telemetry: stream?.telemetry ?? null,
    points: stream?.points ?? [],
    connected: connectionStatus === "live",
    backendConnected,
    connectionStatus,
    deviceIds,
    selectedDeviceId: currentDeviceId,
    setSelectedDeviceId,
  };
}