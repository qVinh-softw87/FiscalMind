export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Helper to retrieve token
export function getAccessToken(): string | null {
  return localStorage.getItem('fm_access_token');
}

export function setAccessToken(token: string) {
  localStorage.setItem('fm_access_token', token);
}

export function clearAccessToken() {
  localStorage.removeItem('fm_access_token');
}

// Custom fetch wrapper with token injection and unauthorized interception
async function apiRequest(endpoint: string, options: RequestInit = {}): Promise<any> {
  const token = getAccessToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearAccessToken();
    window.location.reload(); // Force re-render/login screen
    throw new Error('Phiên làm việc hết hạn. Vui lòng đăng nhập lại.');
  }

  if (!response.ok) {
    let errorMsg = 'Đã xảy ra lỗi hệ thống.';
    try {
      const errData = await response.json();
      errorMsg = errData.detail || errData.message || errorMsg;
    } catch (_) {}
    throw new Error(errorMsg);
  }

  // Handle empty responses
  if (response.status === 204) return null;

  return response.json();
}

export const api = {
  // ── Authentication ─────────────────────────────────────────────────────────
  async login(payload: any) {
    const data = await apiRequest('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (data && data.access_token) {
      setAccessToken(data.access_token);
    }
    return data;
  },

  async register(payload: any) {
    return apiRequest('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async logout() {
    try {
      await apiRequest('/auth/logout', { method: 'POST' });
    } catch (e) {
      console.error('Logout failed on backend:', e);
    } finally {
      clearAccessToken();
    }
  },

  // ── Dashboard ──────────────────────────────────────────────────────────────
  async getDashboardSummary() {
    return apiRequest('/dashboard/summary');
  },

  // ── Documents ──────────────────────────────────────────────────────────────
  async uploadDocument(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    const token = getAccessToken();
    const headers = new Headers();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const response = await fetch(`${API_URL}/documents/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (response.status === 401) {
      clearAccessToken();
      window.location.reload();
      throw new Error('Phiên làm việc hết hạn.');
    }

    if (!response.ok) {
      let errorMsg = 'Upload file thất bại.';
      try {
        const errData = await response.json();
        errorMsg = errData.detail || errData.message || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }

    return response.json();
  },

  async getDocumentStatus(id: string) {
    return apiRequest(`/documents/${id}/status`);
  },

  async listDocuments(params: { page?: number; page_size?: number; status?: string } = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());
    if (params.status) query.append('status', params.status);

    return apiRequest(`/documents?${query.toString()}`);
  },

  async deleteDocument(id: string) {
    return apiRequest(`/documents/${id}`, { method: 'DELETE' });
  },

  // ── AI Chat (SSE Stream) ───────────────────────────────────────────────────
  async listConversations() {
    return apiRequest('/chat/conversations');
  },

  async getConversationHistory(id: string) {
    return apiRequest(`/chat/conversations/${id}`);
  },

  async deleteConversation(id: string) {
    return apiRequest(`/chat/conversations/${id}`, { method: 'DELETE' });
  },

  async chatStream(
    payload: { message: string; conversation_id?: string; document_ids?: string[] },
    onChunk: (data: any) => void,
    onDone: (data: any) => void,
    onError: (err: any) => void
  ) {
    const token = getAccessToken();
    const headers = new Headers({
      'Content-Type': 'application/json',
    });
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      if (response.status === 401) {
        clearAccessToken();
        window.location.reload();
        return;
      }

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Không thể gửi câu hỏi đến AI.');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) {
        throw new Error('Stream reader không khả dụng.');
      }

      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const cleaned = line.replace(/^data:\s*/, '').trim();
          if (!cleaned) continue;

          try {
            const parsed = JSON.parse(cleaned);
            if (parsed.done) {
              onDone(parsed);
            } else {
              onChunk(parsed);
            }
          } catch (err) {
            console.error('Lỗi khi parse dòng SSE:', cleaned, err);
          }
        }
      }
    } catch (err: any) {
      onError(err);
    }
  },

  // ── Benchmarking ───────────────────────────────────────────────────────────
  async getDocumentBenchmark(docId: string) {
    return apiRequest(`/analysis/documents/${docId}/benchmark`);
  },

  async saveCustomBenchmark(payload: {
    sector: string;
    metric: string;
    healthy_boundary: number;
    warning_boundary: number;
    direction?: 'UP' | 'DOWN';
    owner_type?: 'USER' | 'ORGANIZATION';
  }) {
    return apiRequest('/analysis/benchmarks/custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  // ── Cross-Comparison ───────────────────────────────────────────────────────
  async compareDocuments(documentIds: string[]) {
    return apiRequest('/analysis/comparison', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_ids: documentIds }),
    });
  },
};
