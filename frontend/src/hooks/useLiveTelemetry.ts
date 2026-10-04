import {useEffect, useRef, useState} from "react";
import type {ChartPoint, Telemetry} from "../types/telemetry";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/api/v1/ws/live";

export function useLiveTelemetry() {
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [points, setPoints] = useState<ChartPoint[]>([]);
  const [connected, setConnected] = useState(false);
  const retryRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    let active = true;
    let socket: WebSocket | null = null;
    const connect = () => {
      if (!active) return;
      socket = new WebSocket(WS_URL);
      socket.onopen = () => setConnected(true);
      socket.onclose = () => { setConnected(false); retryRef.current = window.setTimeout(connect, 1500); };
      socket.onerror = () => socket?.close();
      socket.onmessage = (event) => {
        const value = JSON.parse(event.data) as Telemetry;
        setTelemetry(value);
        setPoints((current) => [...current.slice(-59), {time: value.timestamp_ms / 1000, hr: value.hr_bpm, gsr: value.gsr.raw, movement: value.movement.score, probability: value.prediction.probability}]);
      };
    };
    connect();
    return () => { active = false; socket?.close(); if (retryRef.current) window.clearTimeout(retryRef.current); };
  }, []);
  return {telemetry, points, connected};
}
