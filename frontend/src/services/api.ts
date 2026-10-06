const API_BASE = 'http://127.0.0.1:8001/api';

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function sendJson<T>(path: string, method: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => getJson<{ status: string; dataset_detected: boolean }>(`/health`),
  datasetStatus: () => getJson<any>(`/datasets/status`),
  overview: () => getJson<any>(`/overview`),
  products: (limit = 20, category?: string, query?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (category) params.set('category', category);
    if (query?.trim()) params.set('q', query.trim());
    return getJson<any>(`/products?${params.toString()}`);
  },
  searchProducts: (query: string, limit = 12) => getJson<any>(`/products/search?limit=${limit}&q=${encodeURIComponent(query.trim())}`),
  bundleRecommendations: () => getJson<any>(`/recommendations/bundles`),
  users: (query?: string, limit = 25) => getJson<any>(`/users?limit=${limit}${query?.trim() ? `&q=${encodeURIComponent(query.trim())}` : ''}`),
  recommendations: (userId: string) => getJson<any>(`/users/${encodeURIComponent(userId)}/recommendations`),
  browsingInsights: (limit = 50) => getJson<any>(`/analytics/browsing-insights?limit=${limit}`),
  productDetails: (productId: string) => getJson<any>(`/products/${encodeURIComponent(productId)}`),
  categories: () => getJson<any>(`/analytics/categories`),
  events: () => getJson<any>(`/analytics/events`),
  purchaseInsights: () => getJson<any>(`/analytics/purchase-insights`),
  priceHistory: (productId: string) => getJson<any>(`/products/${encodeURIComponent(productId)}/price-history`),
  alternatives: (productId: string) => getJson<any>(`/recommendations/alternatives?product_id=${encodeURIComponent(productId)}`),
  watchlist: () => getJson<any>(`/watchlist`),
  budget: () => getJson<any>(`/budget`),
  setBudget: (payload: {
    total_budget: number;
    target_price?: number | null;
    preferred_category?: string | null;
    minimum_price?: number | null;
    maximum_price?: number | null;
  }) => sendJson<any>(`/budget`, 'PUT', payload),
  shoppingPlan: () => getJson<any>(`/shopping-plan`),
  addToWatchlist: (productId: string) => sendJson<any>(`/watchlist?product_id=${encodeURIComponent(productId)}`, 'POST'),
  addToShoppingPlan: (productId: string, observedPrice: number, quantity = 1) => sendJson<any>(`/shopping-plan`, 'POST', { product_id: productId, observed_price: observedPrice, quantity }),
  compareAlternatives: (productId: string) => getJson<any>(`/recommendations/alternatives?product_id=${encodeURIComponent(productId)}`),
};
