// Token pricing per million tokens (USD)
const PRICE = {
  input: 0.15,
  cache_read: 0.04,
  output: 0.60,
};

export function calcCost(tokens) {
  return (
    (tokens.input || 0) * PRICE.input / 1_000_000 +
    (tokens.cache_read || 0) * PRICE.cache_read / 1_000_000 +
    (tokens.output || 0) * PRICE.output / 1_000_000
  );
}

export function formatUSD(amount) {
  if (amount < 0.001) return `$${(amount * 1000).toFixed(3)}m`;
  return `$${amount.toFixed(4)}`;
}

export function formatSeconds(ts) {
  const h = Math.floor(ts / 3600);
  const m = Math.floor((ts % 3600) / 60);
  const s = Math.floor(ts % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}
