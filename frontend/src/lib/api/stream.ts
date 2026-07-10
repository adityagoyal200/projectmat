import type { MatchRecommendation, StudentRecommendationsResponse } from '@/types/api';

const explicitApiUrl = import.meta.env.VITE_API_URL as string | undefined;
// Mirror the axios client's base-URL logic so streaming and normal requests
// hit the same backend (see client.ts).
const API_BASE = explicitApiUrl ? `${explicitApiUrl.replace(/\/$/, '')}/api` : '/api';

export type MatchStreamEvent =
  | {
      type: 'meta';
      candidate_name: string;
      registration_number: string;
      achievements: string[];
      total: number;
      finalist_ids: number[];
      cached: boolean;
    }
  | { type: 'prelim'; recommendations: MatchRecommendation[] }
  | { type: 'update'; recommendation: MatchRecommendation }
  | { type: 'done'; cached: boolean; response: StudentRecommendationsResponse }
  | { type: 'error'; status: number; message: string; raw_response?: unknown };

/**
 * Consume a Server-Sent Events endpoint, invoking `onEvent` for each JSON
 * `data:` payload as it arrives. Resolves when the stream closes.
 */
export async function streamMatchEvents(
  path: string,
  onEvent: (event: MatchStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: 'text/event-stream' },
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`Streaming request failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    let boundary = buffer.indexOf('\n\n');
    while (boundary !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const data = frame
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).replace(/^ /, ''))
        .join('\n');
      if (data) {
        try {
          onEvent(JSON.parse(data) as MatchStreamEvent);
        } catch {
          // Ignore a malformed frame rather than aborting the whole stream.
        }
      }
      boundary = buffer.indexOf('\n\n');
    }
  }
}
