import { MTOItem } from "@/lib/types";

interface MTOTableProps {
  items: MTOItem[];
}

function confidenceColor(confidence: number | null): string {
  if (confidence === null) return "bg-slate-100 text-slate-600";
  if (confidence >= 0.8) return "bg-green-100 text-green-800";
  if (confidence >= 0.6) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

function confidenceBarColor(confidence: number | null): string {
  if (confidence === null) return "bg-slate-300";
  if (confidence >= 0.8) return "bg-emerald-500";
  if (confidence >= 0.6) return "bg-amber-500";
  return "bg-rose-500";
}

function statusBadge(status: MTOItem["verification_status"]): { label: string; className: string } {
  switch (status) {
    case "match":
      return { label: "Matches BOM", className: "bg-green-100 text-green-800" };
    case "conflict":
      return { label: "Conflict", className: "bg-red-100 text-red-800" };
    case "no_bom_available":
      return { label: "No BOM to check", className: "bg-slate-100 text-slate-600" };
    default:
      return { label: "Unverified", className: "bg-slate-100 text-slate-600" };
  }
}

export default function MTOTable({ items }: MTOTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {["#", "Pg", "Category", "Description", "Size", "Sched/Class", "Material", "End", "Qty", "Unit", "Length (m)", "Confidence", "Verification", "Remarks"].map(
              (h) => (
                <th key={h} className="px-3 py-2 text-left font-medium text-slate-600 whitespace-nowrap">
                  {h}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {items.map((item) => {
            const badge = statusBadge(item.verification_status);
            return (
              <tr key={item.item_no} className={item.verification_status === "conflict" ? "bg-red-50/40" : ""}>
                <td className="px-3 py-2 text-slate-500">{item.item_no}</td>
                <td className="px-3 py-2 text-slate-500">{item.source_page ?? "—"}</td>
                <td className="px-3 py-2 font-medium text-slate-800">{item.category}</td>
                <td className="px-3 py-2 text-slate-700">
                  {item.description}
                  {item.derived_from && (
                    <span className="block text-xs text-slate-400 mt-0.5">Derived: {item.derived_from}</span>
                  )}
                </td>
                <td className="px-3 py-2 whitespace-nowrap">{item.size_nps ?? "—"}</td>
                <td className="px-3 py-2 whitespace-nowrap">{item.schedule_rating ?? "—"}</td>
                <td className="px-3 py-2 whitespace-nowrap">{item.material_spec ?? "—"}</td>
                <td className="px-3 py-2 whitespace-nowrap">{item.end_type ?? "—"}</td>
                <td className="px-3 py-2 whitespace-nowrap">{item.quantity}</td>
                <td className="px-3 py-2 whitespace-nowrap">{item.unit}</td>
                <td className="px-3 py-2 whitespace-nowrap">{item.length_m ?? "—"}</td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <div className="min-w-28">
                    <div className={`h-2 w-full rounded-full bg-slate-100 ${item.confidence === null ? "opacity-70" : ""}`}>
                      <div
                        className={`h-2 rounded-full ${confidenceBarColor(item.confidence)}`}
                        style={{ width: `${item.confidence !== null ? Math.round(item.confidence * 100) : 0}%` }}
                      />
                    </div>
                    <span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${confidenceColor(item.confidence)}`}>
                      {item.confidence !== null ? `${Math.round(item.confidence * 100)}%` : "N/A"}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}>
                    {badge.label}
                  </span>
                </td>
                <td className="px-3 py-2 text-slate-500 max-w-xs">{item.remarks ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
