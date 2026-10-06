export type Metric = {
  label: string;
  value: number | string;
  trend?: string;
};

export type DatasetStatus = {
  detected: boolean;
  dataset_path?: string | null;
  file_name?: string;
  validation?: { valid?: boolean; error?: string; missing_columns?: string[] };
  message?: string;
};

export type OverviewPayload = {
  metrics?: {
    total_events?: number;
    unique_users?: number;
    unique_products?: number;
    views?: number;
    cart_additions?: number;
    purchases?: number;
  };
  event_distribution?: Array<{ event_type: string; count: number }>;
  category_activity?: Array<{ category_id: string; count: number }>;
  funnel?: { steps: string[]; values: number[] };
};

export type ProductItem = {
  product_id: string;
  latest_event_time?: string;
  avg_price?: number;
  event_count?: number;
};

export type RecommendationItem = {
  product_id: string;
  score: number;
  reason_codes?: string[];
};
