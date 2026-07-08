import { MTOSummary } from "@/lib/types";

interface SummaryCardsProps {
  summary: MTOSummary;
}

export default function SummaryCards({ summary }: SummaryCardsProps) {
  const cards = [
    { label: "Total Pipe Length", value: `${summary.total_pipe_length_m.toFixed(2)} m` },
    { label: "Fittings", value: summary.fittings },
    { label: "Flanges", value: summary.flanges },
    { label: "Valves", value: summary.valves },
    { label: "Gaskets", value: summary.gaskets },
    { label: "Bolt Sets", value: summary.bolt_sets },
    { label: "Supports", value: summary.supports },
    { label: "Instr. Conn.", value: summary.instrumentation_connections },
    { label: "Field Welds", value: summary.field_welds },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-9 gap-3">
      {cards.map((card) => (
        <div key={card.label} className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wide">{card.label}</p>
          <p className="text-xl font-semibold text-slate-900 mt-1">{card.value}</p>
        </div>
      ))}
    </div>
  );
}
