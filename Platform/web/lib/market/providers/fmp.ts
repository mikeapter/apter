function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing env var: ${name}`);
  return v;
}

// FMP Company Image endpoint:
// https://financialmodelingprep.com/image-stock/{symbol}.png
// Some plans require apikey query string; we include it for safety.
export function getCompanyLogoUrlFMP(symbol: string): string {
  const key = requireEnv("FMP_API_KEY");
  const upper = symbol.toUpperCase();
  const url = new URL(
    `https://financialmodelingprep.com/image-stock/${upper}.png`
  );
  url.searchParams.set("apikey", key);
  return url.toString();
}
