const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TIMEOUT_MS = 30000;
const MAX_RETRIES = 2;
const RETRY_DELAY = 1000;

class ApiError extends Error {
  status: number;
  type?: string;
  constructor(message: string, status: number, type?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.type = type;
  }
}

function delay(ms: number) { return new Promise(r => setTimeout(r, ms)); }

async function request(path: string, opts: RequestInit = {}, retries = MAX_RETRIES): Promise<any> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('starlight-token') : null;
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(opts.headers as Record<string, string>) };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}${path}`, { ...opts, headers, signal: controller.signal });
    clearTimeout(timer);

    if (!res.ok) {
      let errDetail = res.statusText;
      let errType: string | undefined;
      try {
        const errBody = await res.json();
        errDetail = errBody.detail || errDetail;
        errType = errBody.type;
      } catch {}

      // Retry on 5xx or network errors (but not 4xx client errors)
      if (res.status >= 500 && retries > 0) {
        await delay(RETRY_DELAY);
        return request(path, opts, retries - 1);
      }

      throw new ApiError(errDetail, res.status, errType);
    }

    // Handle 204 No Content
    if (res.status === 204) return null;
    return res.json();
  } catch (err: any) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      throw new ApiError('Request timed out. Please check your connection and try again.', 408);
    }
    if (err instanceof ApiError) throw err;
    // Network error — retry
    if (retries > 0) {
      await delay(RETRY_DELAY);
      return request(path, opts, retries - 1);
    }
    throw new ApiError(err.message || 'Network error. Please check your connection.', 0);
  }
}

export { ApiError };

export const api = {
  register: (email: string, password: string) =>
    request('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  getMe: () => request('/api/auth/me'),
  listCartridges: () => request('/api/cartridges'),
  getCartridge: (id: string) => request(`/api/cartridges/${id}`),
  getNodeContent: (cid: string, nid: string) => request(`/api/cartridges/${cid}/nodes/${nid}`),
  submitAnswer: (data: { cartridge_id: string; node_id: string; question_type: string; user_answer: string; correct_answer: string; correct: boolean }) =>
    request('/api/learning/answer', { method: 'POST', body: JSON.stringify(data) }),
  completeNode: (cartridge_id: string, node_id: string, score: number) =>
    request('/api/learning/complete', { method: 'POST', body: JSON.stringify({ cartridge_id, node_id, score }) }),
  getProgress: (cartridge_id: string) => request(`/api/learning/progress/${cartridge_id}`),
  getStats: () => request('/api/learning/stats'),
};

export async function* chatStream(
  cartridgeId: string,
  nodeId: string,
  message: string,
  history: { role: string; content: string }[] = [],
) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('starlight-token') : '';
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 60000); // 60s for streaming

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/learning/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ cartridge_id: cartridgeId, node_id: nodeId, message, history }),
      signal: controller.signal,
    });
  } catch (err: any) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      throw new ApiError('Chat request timed out. Please try again.', 408);
    }
    throw new ApiError('Cannot connect to server. Please check your connection.', 0);
  }

  if (!res.ok) {
    clearTimeout(timer);
    let detail = res.statusText;
    try { const b = await res.json(); detail = b.detail || detail; } catch {}
    throw new ApiError(detail, res.status);
  }
  if (!res.body) throw new ApiError('No response body received.', 0);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';
      for (const event of events) {
        for (const line of event.split('\n')) {
          if (line.startsWith('data: ')) {
            const payload = line.slice(6);
            if (payload === '[DONE]') { clearTimeout(timer); return; }
            try {
              const data = JSON.parse(payload);
              if (data.error) throw new ApiError(data.text || 'AI error', 502);
              if (data.text) yield data.text;
            } catch (e) {
              if (e instanceof ApiError) throw e;
              // Skip malformed SSE data
            }
          }
        }
      }
    }
    // Process remaining buffer
    if (buffer.trim()) {
      for (const line of buffer.split('\n')) {
        if (line.startsWith('data: ')) {
          const payload = line.slice(6);
          if (payload === '[DONE]') { clearTimeout(timer); return; }
          try {
            const data = JSON.parse(payload);
            if (data.error) throw new ApiError(data.text || 'AI error', 502);
            if (data.text) yield data.text;
          } catch (e) {
            if (e instanceof ApiError) throw e;
          }
        }
      }
    }
  } finally {
    clearTimeout(timer);
    reader.releaseLock();
  }
}
