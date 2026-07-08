import { MTOItem } from "@/lib/types";

interface ReviewQueueProps {
  items: MTOItem[];
  needsReview: number[];
}

export default function ReviewQueue({ items, needsReview }: ReviewQueueProps) {
  const flagged = items.filter((item) => needsReview.includes(item.item_no));

  if (flagged.length === 0) return null;

  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-4">
      <h3 className="font-semibold text-amber-900">Needs Review ({flagged.length})</h3>
      <p className="text-sm text-amber-800 mt-1 mb-3">
        These items had low extraction confidence or disagreed with the drawing's own BOM table.
        Verify them manually before using this MTO for procurement.
      </p>
      <ul className="space-y-2">
        {flagged.map((item) => (
          <li key={item.item_no} className="text-sm text-amber-900">
            <span className="font-medium">
              #{item.item_no} {item.category} — {item.description}
            </span>
            {item.remarks && <span className="block text-amber-700 text-xs mt-0.5">{item.remarks}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
