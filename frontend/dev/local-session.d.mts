import type { Plugin } from "vite";
import type { IncomingMessage, ServerResponse } from "node:http";
export interface LocalSessionOptions { credentialsFile: string; backendUrl?: string; fetchImpl?: typeof fetch }
export function localSessionPlugin(options: LocalSessionOptions): Plugin;
export function localSessionMiddleware(options: LocalSessionOptions):
  (request: IncomingMessage, response: ServerResponse, next: () => void) => Promise<void>;
