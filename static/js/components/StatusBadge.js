/**
 * StatusBadge.js - Data-driven status badge component for TransitAI.
 * Valid statuses: LIVE | SCHEDULED | ESTIMATED | UNAVAILABLE
 */

export function renderStatusBadge(status) {
  const norm = (status || "SCHEDULED").toUpperCase();
  
  if (norm === "LIVE") {
    return `
      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse"></span>
        LIVE
      </span>
    `;
  }
  
  if (norm === "ESTIMATED") {
    return `
      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
        <span class="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
        ESTIMATED
      </span>
    `;
  }

  if (norm === "UNAVAILABLE") {
    return `
      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-800 border border-rose-200">
        <span class="w-1.5 h-1.5 rounded-full bg-rose-600"></span>
        UNAVAILABLE
      </span>
    `;
  }

  // Fallback / default: SCHEDULED
  return `
    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
      <span class="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
      SCHEDULED
    </span>
  `;
}
