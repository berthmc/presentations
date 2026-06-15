/** Turn API/HTML error bodies into short user-facing messages. */
export function parseApiError(status: number, body: string, fallback = "Request failed"): string {
  const trimmed = body.trim();
  if (!trimmed) {
    return `${fallback} (${status})`;
  }

  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      const payload = JSON.parse(trimmed) as { detail?: unknown; message?: unknown };
      if (typeof payload.detail === "string") {
        return payload.detail;
      }
      if (Array.isArray(payload.detail)) {
        return payload.detail
          .map((item) => (typeof item === "object" && item && "msg" in item ? String(item.msg) : String(item)))
          .join("; ");
      }
      if (typeof payload.message === "string") {
        return payload.message;
      }
    } catch {
      // Fall through to plain-text handling.
    }
  }

  if (/<html/i.test(trimmed)) {
    if (status === 413) {
      return "File is too large for upload. Corporate .pptx templates may exceed the default limit; retry after the server limit is raised.";
    }
    const titleMatch = trimmed.match(/<title>([^<]+)<\/title>/i);
    if (titleMatch?.[1]) {
      return titleMatch[1].trim();
    }
    return `${fallback} (${status})`;
  }

  return trimmed.length > 240 ? `${trimmed.slice(0, 240)}…` : trimmed;
}
