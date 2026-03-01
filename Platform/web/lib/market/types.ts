export type NormalizedQuote = {
  symbol: string;
  name?: string;
  price: number;
  change: number;
  changePercent: number;
  open?: number;
  high?: number;
  low?: number;
  prevClose?: number;
  asOf: string; // ISO string
  source: string; // e.g. "FINNHUB"
  isDelayed: boolean; // true if your free tier is delayed
};

export type SearchResult = {
  symbol: string;
  name: string;
  exchange?: string;
  type?: string;
  logoUrl?: string;
};
