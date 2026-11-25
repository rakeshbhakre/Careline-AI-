export const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
export async function get(path, signal) {
  const response = await fetch(`${API}/api/${path}`, {signal});
  if (!response.ok) throw new Error(`Server returned ${response.status}`);
  return response.json();
}
