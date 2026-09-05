/** Minimal SSE client over fetch + ReadableStream, for POST endpoints —
 * the browser's built-in EventSource is GET-only, and /runs and /approve
 * are POST (they kick off real agent work, not just subscribe to it).
 *
 * sse-starlette (the server's SSE library) writes CRLF line endings and a
 * bare `: ping - <timestamp>` comment every ~15s to keep the Cloud Run
 * connection alive. Both bite if you naively split on "\n\n" and
 * JSON.parse every non-empty line:
 *   - CRLF: splitting only on "\n" leaves a trailing "\r" on the field
 *     value, which breaks JSON.parse on the following line.
 *   - keepalive comments: lines starting with ":" are protocol noise, not
 *     an event field — must be skipped, not parsed as "event:"/"data:".
 * A chunk can also end mid-UTF8-character or mid-line, so the decoder must
 * be streaming (TextDecoder({stream: true})) and partial lines held over
 * to the next chunk, not decoded/split as if each chunk were complete.
 */
export type SseEvent = { event: string; data: string };

export async function* postSse(url: string, body?: unknown): AsyncGenerator<SseEvent> {
  const resp = await fetch(url, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`SSE request failed: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sepIndex: number;
    while ((sepIndex = buffer.indexOf("\n\n")) !== -1 || (sepIndex = buffer.indexOf("\r\n\r\n")) !== -1) {
      const rawEvent = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + (buffer[sepIndex] === "\r" ? 4 : 2));

      let eventName = "message";
      let data = "";
      for (const rawLine of rawEvent.split(/\r\n|\n/)) {
        const line = rawLine.replace(/\r$/, "");
        if (!line || line.startsWith(":")) continue; // keepalive ping / blank
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) data += (data ? "\n" : "") + line.slice(5).trim();
      }
      if (data) yield { event: eventName, data };
    }
  }
}
