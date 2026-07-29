/** Chunk load error detection.

Every page is lazy-loaded, so a stale deployment or flaky network
surfaces as a failed dynamic import. These errors have recognizable
signatures across bundlers (webpack ChunkLoadError, Vite/Umi dynamic
import failures) — detecting them lets the ErrorBoundary show a
"reload to get the new version" recovery instead of a generic error.

Pattern source: ant-design-pro v6.0.1 (#11756).
*/

const CHUNK_MESSAGE_RE =
  /(?:loading|failed to load) (?:css )?chunk|Failed to fetch dynamically imported module|error loading dynamically imported module/i;

export function isChunkLoadError(error: Error): boolean {
  return error.name === "ChunkLoadError" || CHUNK_MESSAGE_RE.test(error.message);
}

export function isOffline(): boolean {
  return typeof navigator !== "undefined" && !navigator.onLine;
}
