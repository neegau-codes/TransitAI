/**
 * StatusBadge.js - Data-driven status badge for TransitAI Expo Demo.
 *
 * Visible statuses:
 *   SCHEDULED  — from published timetable data
 *   ESTIMATED  — calculated by TransitAI
 *   UNAVAILABLE — value cannot be obtained
 *
 * LIVE is accepted from legacy backend payloads but is NOT advertised
 * as realtime. No animate-pulse or live indicators are used.
 */

export function renderStatusBadge(rawStatus) {
  const norm = String(rawStatus || 'UNAVAILABLE').toUpperCase();

  if (norm === 'SCHEDULED') {
    return `
      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200" title="Published timetable data">
        <span class="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
        SCHEDULED
      </span>
    `;
  }

  if (norm === 'ESTIMATED') {
    return `
      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200" title="Calculated by TransitAI">
        <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
        ESTIMATED
      </span>
    `;
  }

  // LIVE from backend → render as UNAVAILABLE to avoid false realtime claim
  // UNAVAILABLE or anything else
  return `
    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-800 border border-rose-200" title="Value unavailable">
      <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
      UNAVAILABLE
    </span>
  `;
}
