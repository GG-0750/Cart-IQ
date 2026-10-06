import { useEffect, useState } from 'react';
import { BarChart3, BarChart as BarChartIcon, BriefcaseBusiness, CircleDollarSign, LayoutGrid, PackageSearch, Search, Settings, ShoppingBasket, ShoppingCart, Sparkles, TrendingUp, Wallet, ArrowUpRight, ArrowDownRight, Gauge, ListFilter } from 'lucide-react';
import { NavLink, Route, Routes } from 'react-router-dom';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from './services/api';
import type { OverviewPayload } from './types';

const navItems = [
  { label: 'Overview', path: '/', icon: LayoutGrid },
  { label: 'Smart Recommendations', path: '/recommendations', icon: Sparkles },
  { label: 'Browsing Insights', path: '/insights', icon: PackageSearch },
  { label: 'Price Watch', path: '/price-watch', icon: CircleDollarSign },
  { label: 'Budget Planner', path: '/budget', icon: Wallet },
  { label: 'Smart Bundles', path: '/bundles', icon: ShoppingBasket },
  { label: 'Purchase Insights', path: '/purchase-insights', icon: TrendingUp },
  { label: 'Data Explorer', path: '/explorer', icon: BarChart3 },
  { label: 'Settings', path: '/settings', icon: Settings },
];

function App() {
  const [status, setStatus] = useState<any>(null);
  const [overview, setOverview] = useState<OverviewPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [selectedProductDetail, setSelectedProductDetail] = useState<any>(null);

  useEffect(() => {
    Promise.all([api.datasetStatus(), api.overview()])
      .then(([dataset, overviewData]) => {
        setStatus(dataset);
        setOverview(overviewData);
      })
      .catch((err) => setError(err.message || 'Backend unavailable.'))
      .finally(() => setLoading(false));
  }, []);

  async function openProductDetail(productId: string) {
    setSelectedProductId(productId);
    setSelectedProductDetail(null);
    try {
      const detail = await api.productDetails(productId);
      setSelectedProductDetail(detail);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'Could not load product details.');
    }
  }

  async function handleSearch(event?: React.FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const trimmedQuery = searchQuery.trim();
    if (!trimmedQuery) {
      setSearchResults([]);
      setSelectedProductId(null);
      setSelectedProductDetail(null);
      setSearchError(null);
      return;
    }
    setSearchLoading(true);
    setSearchError(null);
    try {
      const data = await api.searchProducts(trimmedQuery, 8);
      const nextResults = data.products ?? [];
      setSearchResults(nextResults);
      if (nextResults[0]?.product_id) {
        await openProductDetail(nextResults[0].product_id);
      }
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'Product search failed.');
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">C</div>
          <div>
            <div className="brand-name">CartIQ</div>
            <div className="brand-subtitle">Big Data Commerce</div>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map(({ label, path, icon: Icon }) => (
            <NavLink key={path} to={path} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <form className="search-wrap" onSubmit={handleSearch}>
            <Search size={16} />
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search products, brands, categories"
              aria-label="Search products by ID, brand, or category"
            />
            <button type="submit" className="search-button" disabled={searchLoading}>Search</button>
          </form>
          <div className="topbar-meta">
            <span className="page-title">Analytics workspace</span>
            <span className="status-pill success">{status?.detected ? 'Real Data' : 'Dataset unavailable'}</span>
            <span className="status-pill muted">{loading ? 'Initializing' : 'Ready'}</span>
          </div>
        </header>

        {error ? (<div className="alert">{error}</div>) : null}
        {searchError ? (<div className="alert">{searchError}</div>) : null}
        {searchLoading ? (<div className="panel empty-state">Searching the processed dataset…</div>) : null}
        {!searchLoading && searchResults.length > 0 ? (
          <div className="panel">
            <h3>Product search results</h3>
            <div className="list-card">
              {searchResults.map((item) => (
                <button key={item.product_id} type="button" className="search-result-row" onClick={() => openProductDetail(item.product_id)}>
                  <div>
                    <strong>{item.product_id}</strong>
                    <span>{item.brand ?? 'Brand not recorded'} · {item.category_code ?? item.category_id ?? 'Category not recorded'}</span>
                  </div>
                  <div className="pill-group">
                    <span className="score-pill">{item.latest_observed_price == null ? 'No price' : `$${Number(item.latest_observed_price).toFixed(2)}`}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : null}
        {!searchLoading && !searchError && searchResults.length === 0 && searchQuery.trim() && !selectedProductDetail ? (
          <div className="panel empty-state">No products matched the current search in the loaded processed dataset.</div>
        ) : null}
        {selectedProductDetail ? (
          <div className="panel">
            <h3>Product details · {selectedProductId}</h3>
            <div className="list-card">
              {(selectedProductDetail.events ?? []).slice(0, 5).map((event: any, idx: number) => (
                <div key={`${event.event_time}-${idx}`} className="list-row">
                  <span>{event.event_type}</span>
                  <strong>{event.price == null ? 'No price recorded' : `$${Number(event.price).toFixed(2)}`}</strong>
                  <span>{event.event_time}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {loading ? (
          <div className="panel empty-state">Loading real dataset state…</div>
        ) : (
          <Routes>
            <Route path="/" element={<OverviewPage overview={overview} status={status} />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            <Route path="/insights" element={<InsightsPage />} />
            <Route path="/price-watch" element={<PriceWatchPage />} />
            <Route path="/budget" element={<BudgetPage />} />
            <Route path="/bundles" element={<BundlesPage />} />
            <Route path="/purchase-insights" element={<PurchaseInsightsPage />} />
            <Route path="/explorer" element={<ExplorerPage />} />
            <Route path="/settings" element={<SettingsPage status={status} />} />
          </Routes>
        )}
      </main>
    </div>
  );
}

function OverviewPage({ overview, status }: { overview: OverviewPayload | null; status: any }) {
  const metrics = [
    { label: 'Total events', value: overview?.metrics?.total_events ?? 0 },
    { label: 'Unique users', value: overview?.metrics?.unique_users ?? 0 },
    { label: 'Unique products', value: overview?.metrics?.unique_products ?? 0 },
    { label: 'Views', value: overview?.metrics?.views ?? 0 },
  ];

  return (
    <div className="page-grid">
      <section className="panel hero-panel">
        <div>
          <p className="eyebrow">Dataset status</p>
          <h1>CartIQ Overview</h1>
        </div>
        <div className="dataset-info">
          <span>{status?.file_name || 'Dataset pending'}</span>
          <span>{status?.detected ? 'Real data loaded' : 'No dataset detected'}</span>
        </div>
      </section>

      <div className="metrics-grid">
        {metrics.map((metric) => (
          <div key={metric.label} className="panel metric-card">
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </div>
        ))}
      </div>

      <div className="chart-grid">
        <div className="panel chart-card">
          <h3>Event distribution</h3>
          <Chart data={overview?.event_distribution ?? []} xKey="event_type" yKey="count" />
        </div>
        <div className="panel chart-card">
          <h3>Category activity</h3>
          <Chart data={overview?.category_activity ?? []} xKey="category_id" yKey="count" />
        </div>
      </div>

      <div className="panel">
        <h3>Conversion funnel</h3>
        <div className="funnel-steps">
          {(overview?.funnel?.steps ?? []).map((step, idx) => (
            <div key={step} className="funnel-step">
              <span>{step}</span>
              <strong>{overview?.funnel?.values?.[idx] ?? 0}</strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RecommendationsPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [query, setQuery] = useState('');
  const [selectedUser, setSelectedUser] = useState('');
  const [items, setItems] = useState<any[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.users()
      .then((data) => {
        const nextUsers = data.users ?? [];
        setUsers(nextUsers);
        setSelectedUser(nextUsers[0]?.user_id ?? '');
      })
      .catch((err) => setError(err.message || 'Could not load dataset users.'))
      .finally(() => setLoadingUsers(false));
  }, []);

  useEffect(() => {
    if (!selectedUser) {
      setItems([]);
      return;
    }
    setLoadingRecommendations(true);
    setError(null);
    api.recommendations(selectedUser)
      .then((data) => setItems(data.recommendations ?? []))
      .catch((err) => {
        setItems([]);
        setError(err.message || 'Could not load recommendations for this user.');
      })
      .finally(() => setLoadingRecommendations(false));
  }, [selectedUser]);

  async function searchUsers(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoadingUsers(true);
    setError(null);
    try {
      const data = await api.users(query, 25);
      const nextUsers = data.users ?? [];
      setUsers(nextUsers);
      setSelectedUser(nextUsers[0]?.user_id ?? '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not search dataset users.');
    } finally {
      setLoadingUsers(false);
    }
  }

  return (
    <div className="panel">
      <h2>Smart Recommendations</h2>
      <form className="recommendation-controls" onSubmit={searchUsers}>
        <label>
          Find a dataset user
          <span className="inline-control">
            <input aria-label="Search dataset user IDs" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search user ID" />
            <button type="submit" disabled={loadingUsers}>Search</button>
          </span>
        </label>
        <label>
          Selected user
          <select aria-label="Selected dataset user" value={selectedUser} onChange={(event) => setSelectedUser(event.target.value)} disabled={loadingUsers || users.length === 0}>
            {users.map((user) => <option key={user.user_id} value={user.user_id}>{user.user_id} · {user.event_count} events</option>)}
          </select>
        </label>
      </form>
      {error ? <div className="alert" role="alert">{error}</div> : null}
      <div className="list-card">
        {loadingUsers || loadingRecommendations ? <p className="empty-copy" role="status">Loading recommendations from observed behavior…</p> : null}
        {!loadingUsers && !loadingRecommendations && users.length === 0 ? <p className="empty-copy">No users were found in the processed dataset.</p> : null}
        {!loadingUsers && !loadingRecommendations && users.length > 0 && items.length === 0 ? <p className="empty-copy">No unseen products matched this user’s observed categories.</p> : null}
        {items.map((item) => (
          <div key={item.product_id} className="list-row">
            <div>
              <strong>{item.product_id}</strong>
              <span>{item.explanation}</span>
              <span>Reasons: {(item.reason_codes || []).join(', ')}</span>
              <span>Evidence: {item.evidence?.product_event_count ?? 0} observed product events; category {item.evidence?.category_id ?? 'not available'}</span>
              <span>Latest observed price: {item.observed_price == null ? 'not available' : Number(item.observed_price).toFixed(2)} · {item.timestamp}</span>
            </div>
            <div className="pill-group">
              <span className="score-pill">score {item.score}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function InsightsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [details, setDetails] = useState<Record<string, any>>({});
  const [alternatives, setAlternatives] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.browsingInsights()
      .then((data) => setItems(data.items ?? []))
      .catch((err) => setError(err.message || 'Could not load browsing insights.'))
      .finally(() => setLoading(false));
  }, []);

  async function loadDetails(productId: string) {
    setError(null);
    try {
      const result = await api.productDetails(productId);
      setDetails((current) => ({ ...current, [productId]: result }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load product details.');
    }
  }

  async function addToWatchlist(productId: string) {
    setError(null);
    try {
      await api.addToWatchlist(productId);
      setMessage(`Added ${productId} to the watchlist.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update the watchlist.');
    }
  }

  async function compareAlternatives(productId: string) {
    setError(null);
    try {
      const result = await api.compareAlternatives(productId);
      setAlternatives((current) => ({ ...current, [productId]: result }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load alternatives.');
    }
  }

  async function addToPlan(item: any) {
    if (item.latest_observed_price == null) return;
    setError(null);
    try {
      await api.addToShoppingPlan(item.product_id, Number(item.latest_observed_price));
      setMessage(`Added ${item.product_id} to the shopping plan at its latest observed price.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update the shopping plan.');
    }
  }

  return (
    <div className="panel">
      <h2>Browsing insights</h2>
      <p className="empty-copy">Repeated views without a recorded purchase in the loaded observation window. This is an interest heuristic, not proof of abandonment.</p>
      <p className="empty-copy">Interest score: views + 2 × cart additions + 0.5 × cart removals.</p>
      {error ? <div className="alert" role="alert">{error}</div> : null}
      {message ? <p role="status">{message}</p> : null}
      {loading ? <p className="empty-copy" role="status">Loading processed event insights…</p> : null}
      {!loading && items.length === 0 ? <p className="empty-copy">No repeated-view products without a purchase were found in the loaded data.</p> : null}
      <div className="list-card">
        {items.map((item) => (
          <article className="insight-row" key={item.product_id}>
            <div className="insight-summary">
              <strong>{item.product_id}</strong>
              <span>{item.category ?? 'Category not recorded'} · {item.brand ?? 'Brand not recorded'}</span>
              <span>{item.views} views · {item.cart_additions} cart additions · {item.cart_removals} cart removals · {item.purchases} purchases</span>
              <span>Latest observed price: {item.latest_observed_price == null ? 'not recorded' : Number(item.latest_observed_price).toFixed(2)} · {item.latest_event_time}</span>
              <span>{item.interest_score_formula} = {item.interest_score}</span>
            </div>
            <div className="insight-actions">
              <button type="button" onClick={() => loadDetails(item.product_id)}>View Details</button>
              <button type="button" onClick={() => addToWatchlist(item.product_id)}>Watchlist</button>
              <button type="button" onClick={() => compareAlternatives(item.product_id)}>Compare Alternatives</button>
              <button type="button" onClick={() => addToPlan(item)} disabled={item.latest_observed_price == null}>Add to Shopping Plan</button>
            </div>
            {details[item.product_id] ? (
              <div className="insight-action-result">
                <strong>Observed product events ({details[item.product_id].events?.length ?? 0})</strong>
                {details[item.product_id].events?.slice(0, 3).map((event: any, index: number) => <span key={`${event.event_time}-${index}`}>{event.event_type} · {event.event_time} · {event.price ?? 'price not recorded'}</span>)}
              </div>
            ) : null}
            {alternatives[item.product_id] ? (
              <div className="insight-action-result">
                <strong>Observed alternatives</strong>
                <span>Selected latest observed price: {alternatives[item.product_id].selected_product?.latest_observed_price ?? 'not recorded'}</span>
                {alternatives[item.product_id].alternatives?.length === 0 ? <span>No same-category lower observed prices matched the loaded data and budget.</span> : alternatives[item.product_id].alternatives?.slice(0, 3).map((alternative: any) => (
                  <span key={alternative.product_id}>
                    {alternative.product_id} · {Number(alternative.latest_observed_price).toFixed(2)} · {Number(alternative.price_difference).toFixed(2)} lower ({Number(alternative.percentage_cheaper).toFixed(2)}%) · {alternative.similarity_explanation}
                  </span>
                ))}
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}

function PriceWatchPage() {
  const [products, setProducts] = useState<any[]>([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.products(25)
      .then((data) => {
        const nextProducts = data.products ?? [];
        setProducts(nextProducts);
        if (!selectedProduct && nextProducts.length > 0) {
          setSelectedProduct(nextProducts[0].product_id);
        }
      })
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, [selectedProduct]);

  useEffect(() => {
    if (!selectedProduct) {
      setHistory([]);
      return;
    }
    setLoading(true);
    setError(null);
    api.priceHistory(selectedProduct)
      .then((data) => setHistory(data.history ?? []))
      .catch((err) => {
        setHistory([]);
        setError(err instanceof Error ? err.message : 'Could not load the selected product history.');
      })
      .finally(() => setLoading(false));
  }, [selectedProduct]);

  const priceValues = history.map((item) => Number(item.price ?? 0));
  const summary = priceValues.length
    ? { min: Math.min(...priceValues), max: Math.max(...priceValues), avg: priceValues.reduce((sum, value) => sum + value, 0) / priceValues.length }
    : null;

  return (
    <div className="panel">
      <h2>Price Watch</h2>
      <div className="recommendation-controls" style={{ marginTop: 16 }}>
        <label>
          Product
          <select aria-label="Selected product for price history" value={selectedProduct} onChange={(event) => setSelectedProduct(event.target.value)} disabled={products.length === 0}>
            {products.map((product) => (
              <option key={product.product_id} value={product.product_id}>{product.product_id}</option>
            ))}
          </select>
        </label>
      </div>
      {error ? <div className="alert" role="alert">{error}</div> : null}
      {loading ? <p className="empty-copy" role="status">Loading observed price history…</p> : null}
      {!loading && history.length === 0 ? <p className="empty-copy">No price observations were found for this product in the processed data.</p> : null}
      {summary ? (
        <div className="stat-grid" style={{ marginBottom: 18 }}>
          <div><label>Latest price</label><strong>{Number(history[history.length - 1]?.price ?? 0).toFixed(2)}</strong></div>
          <div><label>Average</label><strong>{summary.avg.toFixed(2)}</strong></div>
          <div><label>Min</label><strong>{summary.min.toFixed(2)}</strong></div>
          <div><label>Max</label><strong>{summary.max.toFixed(2)}</strong></div>
        </div>
      ) : null}
      {history.length > 0 ? (
        <Chart data={history.map((item) => ({ event_time: item.event_time, price: Number(item.price ?? 0) }))} xKey="event_time" yKey="price" />
      ) : null}
    </div>
  );
}

function BudgetPage() {
  const [budget, setBudget] = useState<any>({ total_budget: 0.0, target_price: null, preferred_category: 'Any', minimum_price: null, maximum_price: null });
  const [shoppingPlan, setShoppingPlan] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([api.budget(), api.shoppingPlan()])
      .then(([budgetData, planData]) => {
        setBudget({
          total_budget: budgetData.total_budget ?? 0.0,
          target_price: budgetData.target_price ?? null,
          preferred_category: budgetData.preferred_category ?? 'Any',
          minimum_price: budgetData.minimum_price ?? null,
          maximum_price: budgetData.maximum_price ?? null,
        });
        setShoppingPlan(planData.items ?? []);
      })
      .catch(() => {
        setBudget({ total_budget: 0.0, target_price: null, preferred_category: 'Any', minimum_price: null, maximum_price: null });
        setShoppingPlan([]);
      });
  }, []);

  const plannedCost = shoppingPlan.reduce((sum, item) => sum + Number(item.observed_price ?? 0) * Number(item.quantity ?? 1), 0);
  const remainingBudget = Number(budget.total_budget ?? 0) - plannedCost;

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const payload = {
        total_budget: Number(budget.total_budget ?? 0),
        target_price: budget.target_price === '' || budget.target_price == null ? null : Number(budget.target_price),
        preferred_category: budget.preferred_category && budget.preferred_category !== 'Any' ? budget.preferred_category : null,
        minimum_price: budget.minimum_price === '' || budget.minimum_price == null ? null : Number(budget.minimum_price),
        maximum_price: budget.maximum_price === '' || budget.maximum_price == null ? null : Number(budget.maximum_price),
      };
      await api.setBudget(payload);
      setMessage('Budget preferences saved.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the budget settings.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="panel">
      <h2>Budget Planner</h2>
      {error ? <div className="alert" role="alert">{error}</div> : null}
      {message ? <p role="status">{message}</p> : null}
      <div className="stat-grid" style={{ marginBottom: 20 }}>
        <div><label>Total budget</label><strong>{Number(budget.total_budget ?? 0).toFixed(2)}</strong></div>
        <div><label>Planned spend</label><strong>{plannedCost.toFixed(2)}</strong></div>
        <div><label>Remaining</label><strong>{remainingBudget.toFixed(2)}</strong></div>
        <div><label>Target price</label><strong>{budget.target_price == null ? 'Not set' : Number(budget.target_price).toFixed(2)}</strong></div>
      </div>

      <form className="recommendation-controls" onSubmit={handleSave}>
        <label>
          Total budget
          <input
            type="number"
            value={budget.total_budget ?? 0}
            onChange={(event) => setBudget((current: any) => ({ ...current, total_budget: Number(event.target.value) }))}
            min="0"
            step="0.01"
          />
        </label>
        <label>
          Target price
          <input
            type="number"
            value={budget.target_price ?? ''}
            onChange={(event) => setBudget((current: any) => ({ ...current, target_price: event.target.value === '' ? null : Number(event.target.value) }))}
            min="0"
            step="0.01"
          />
        </label>
        <label>
          Preferred category
          <input
            value={budget.preferred_category === 'Any' || !budget.preferred_category ? '' : budget.preferred_category}
            onChange={(event) => setBudget((current: any) => ({ ...current, preferred_category: event.target.value || 'Any' }))}
            placeholder="e.g. electronics"
          />
        </label>
        <label>
          Minimum price
          <input
            type="number"
            value={budget.minimum_price ?? ''}
            onChange={(event) => setBudget((current: any) => ({ ...current, minimum_price: event.target.value === '' ? null : Number(event.target.value) }))}
            min="0"
            step="0.01"
          />
        </label>
        <label>
          Maximum price
          <input
            type="number"
            value={budget.maximum_price ?? ''}
            onChange={(event) => setBudget((current: any) => ({ ...current, maximum_price: event.target.value === '' ? null : Number(event.target.value) }))}
            min="0"
            step="0.01"
          />
        </label>
        <div style={{ display: 'flex', alignItems: 'end' }}>
          <button type="submit" disabled={saving}>Save budget</button>
        </div>
      </form>
      <div className="list-card" style={{ marginTop: 20 }}>
        {shoppingPlan.length === 0 ? <p className="empty-copy">No planned purchases yet.</p> : shoppingPlan.map((item, index) => (
          <div key={`${item.product_id}-${index}`} className="list-row">
            <div>
              <strong>{item.product_id}</strong>
              <span>{item.quantity} × {Number(item.observed_price ?? 0).toFixed(2)}</span>
            </div>
            <strong>{(Number(item.observed_price ?? 0) * Number(item.quantity ?? 1)).toFixed(2)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function BundlesPage() {
  const [bundles, setBundles] = useState<any[]>([]);
  useEffect(() => {
    api.bundleRecommendations().then((d) => setBundles(d.bundles ?? [])).catch(() => setBundles([]));
  }, []);

  return (<div className="panel"><h2>Smart bundles</h2><div className="list-card">{bundles.length === 0 ? <p className="empty-copy">No co-purchase bundles were found in the loaded sample.</p> : bundles.slice(0, 5).map((bundle, idx) => <div className="list-row" key={`${bundle.main_product}-${idx}`}><span>{bundle.main_product} + {bundle.related_product}</span><strong>{bundle.support}</strong></div>)}</div></div>);
}

function PurchaseInsightsPage() {
  const [insights, setInsights] = useState<any[]>([]);
  useEffect(() => {
    api.purchaseInsights().then((d) => setInsights(d.sessions ?? [])).catch(() => setInsights([]));
  }, []);

  return (
    <div className="panel">
      <h2>Purchase insights</h2>
      <div className="list-card">
        {insights.length === 0 ? <p className="empty-copy">Purchase behavior is unavailable until the real sample is processed.</p> : insights.slice(0, 8).map((item, idx) => (
          <div key={`${item.user_id}-${idx}`} className="list-row"><span>{item.user_id}</span><strong>{item.event_type}</strong><span>{item.count}</span></div>
        ))}
      </div>
    </div>
  );
}

function ExplorerPage() {
  const [products, setProducts] = useState<any[]>([]);
  useEffect(() => {
    api.products(10).then((d) => setProducts(d.products ?? [])).catch(() => setProducts([]));
  }, []);

  return (
    <div className="panel">
      <h2>Data Explorer</h2>
      <table className="data-table">
        <thead>
          <tr><th>Product</th><th>Avg price</th><th>Events</th></tr>
        </thead>
        <tbody>
          {products.map((item) => (
            <tr key={item.product_id}><td>{item.product_id}</td><td>{Number(item.avg_price ?? 0).toFixed(2)}</td><td>{item.event_count ?? 0}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SettingsPage({ status }: { status: any }) {
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [shoppingPlan, setShoppingPlan] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([api.watchlist(), api.shoppingPlan()])
      .then(([watchlistData, planData]) => {
        setWatchlist(watchlistData.items ?? []);
        setShoppingPlan(planData.items ?? []);
      })
      .catch(() => {
        setWatchlist([]);
        setShoppingPlan([]);
      });
  }, []);

  return (
    <div className="panel">
      <h2>Settings</h2>
      <div className="settings-grid">
        <div><label>Dataset path</label><strong>{status?.dataset_path || 'Not detected'}</strong></div>
        <div><label>Real data status</label><strong>{status?.detected ? 'Yes' : 'No'}</strong></div>
        <div><label>Watchlist</label><strong>{watchlist.length === 0 ? 'No products saved' : watchlist.join(', ')}</strong></div>
        <div><label>Shopping plan</label><strong>{shoppingPlan.length === 0 ? 'No planned items' : shoppingPlan.map((item) => `${item.product_id} (${item.quantity ?? 1})`).join(', ')}</strong></div>
      </div>
    </div>
  );
}

function Chart({ data, xKey, yKey }: { data: any[]; xKey: string; yKey: string }) {
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data}>
          <CartesianGrid stroke="#E9E2D7" vertical={false} />
          <XAxis dataKey={xKey} tick={{ fontSize: 10 }} angle={-12} textAnchor="end" />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Bar dataKey={yKey} fill="#B96F52" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default App;
