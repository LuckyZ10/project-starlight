const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request(path: string, opts: RequestInit = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('starlight-token') : null;
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(opts.headers as Record<string, string>) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

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
  const res = await fetch(`${API_BASE}/api/learning/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ cartridge_id: cartridgeId, node_id: nodeId, message, history }),
  });
  if (!res.ok || !res.body) throw new Error('Chat stream failed');
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE events are separated by blank lines (\n\n)
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';
    for (const event of events) {
      for (const line of event.split('\n')) {
        if (line.startsWith('data: ')) {
          const payload = line.slice(6);
          if (payload === '[DONE]') return;
          try {
            const data = JSON.parse(payload);
            if (data.text) yield data.text;
          } catch {}
        }
      }
    }
  }
  // Process remaining buffer
  if (buffer.trim()) {
    for (const line of buffer.split('\n')) {
      if (line.startsWith('data: ')) {
        const payload = line.slice(6);
        if (payload === '[DONE]') return;
        try {
          const data = JSON.parse(payload);
          if (data.text) yield data.text;
        } catch {}
      }
    }
  }
}
