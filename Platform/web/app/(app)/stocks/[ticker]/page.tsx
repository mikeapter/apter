import { StockDetailView } from "../../../components/stock/StockDetailView";

export default function StockDetailPage({ params }: { params: { ticker: string } }) {
  return <StockDetailView ticker={params.ticker} />;
}
