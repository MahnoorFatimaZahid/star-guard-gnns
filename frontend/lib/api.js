const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request(path, { method = 'GET', params, body } = {}) {
  const qs = params
    ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null))
    : '';
  const res = await fetch(`${API_URL}/api${path}${qs}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch (_) {}
    throw new Error(`API ${method} ${path} failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export const api = {
  getStats: () => request('/stats'),
  getUsers: (params) => request('/users', { params }),
  getUser: (id) => request(`/users/${id}`),
  getRepos: (params) => request('/repos', { params }),
  getRepo: (owner, repo) => request(`/repos/${owner}/${repo}`),
  getGraph: (params) => request('/graph', { params }),
  getAnalytics: (params) => request('/analytics', { params }),
  runAnalysis: (body) => request('/analysis/run', { method: 'POST', body }),
  getAnalysisStatus: (id) => request(`/analysis/${id}/status`),
  exportData: (body) => request('/export', { method: 'POST', body }),

  // Live GitHub scan. Inference only — these never train the model.
  runRealScan: (body) => request('/real-scan/run', { method: 'POST', body }),
  getRealScanStatus: (id) => request(`/real-scan/status/${id}`),
  getRealScanLatest: () => request('/real-scan/latest'),
  getRealScanConfig: () => request('/real-scan/config'),
};
