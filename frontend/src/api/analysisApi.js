import axios from "axios";

export async function fetchDeepAnalysis(symbol, market = "TW", forceRefresh = false) {
  const res = await axios.get(`/api/analysis/${symbol}`, {
    params: { market, force_refresh: forceRefresh },
    timeout: 60000,
  });
  return res.data;
}
