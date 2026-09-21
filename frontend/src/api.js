export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}
export async function request(path, token, body) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  const serialized = body ? JSON.stringify(body) : undefined;
  try {
    const response = await fetch(path, {
      method: body ? 'POST' : 'GET', cache: 'no-store', signal: controller.signal, keepalive: Boolean(body) && new TextEncoder().encode(serialized).length < 60000,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      ...(body ? { body: serialized } : {}),
    });
    const data = await response.json();
    if (!response.ok) throw new ApiError(data.error || '请求失败，请重试。', response.status);
    return data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('暂时无法连接，请稍后重试。', 0);
  } finally { clearTimeout(timeout); }
}
export async function getHealth() { return request('/api/health'); }
