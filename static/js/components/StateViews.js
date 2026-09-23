/**
 * StateViews.js - Reusable UI state view generators for TransitAI Expo Demo.
 * All messages are truthful — no realtime or live transit claims.
 */

/** Shown while /api/search is in flight. */
export function renderLoadingState(message = 'Calculating optimal transit routes...') {
  return `
    <div class="w-full bg-surface border border-border-subtle rounded-lg p-8 flex flex-col items-center justify-center text-center gap-3">
      <div class="w-10 h-10 border-[3px] border-deep-teal/20 border-t-deep-teal rounded-full animate-spin"></div>
      <div class="text-sm font-semibold text-charcoal">${escHtml(message)}</div>
      <div class="text-xs text-slate-sec">Using scheduled transit data and TransitAI route estimates</div>
    </div>
  `;
}

/** Shown on page load before any search. */
export function renderInitialState() {
  return `
    <div class="w-full bg-surface border border-border-subtle rounded-lg p-8 flex flex-col items-center justify-center text-center gap-3">
      <span class="material-symbols-outlined text-4xl text-deep-teal">alt_route</span>
      <div class="text-sm font-semibold text-charcoal">Enter a journey to find transit routes.</div>
      <div class="text-xs text-slate-sec">Type your origin and destination above, then click Search Routes.</div>
    </div>
  `;
}

/** Shown when the API returns zero routes for a valid OD pair. */
export function renderEmptyState(message = 'No route found for this journey.') {
  return `
    <div class="w-full bg-surface border border-border-subtle rounded-lg p-8 flex flex-col items-center justify-center text-center gap-3">
      <span class="material-symbols-outlined text-4xl text-muted-slate">no_transfer</span>
      <div class="text-sm font-bold text-charcoal">${escHtml(message)}</div>
      <div class="text-xs text-slate-sec max-w-sm">Try another origin, destination, or travel time.</div>
    </div>
  `;
}

/** Generic error state — never exposes raw Python/Flask traces. */
export function renderErrorState(title = 'TransitAI backend is unavailable.', detail = 'Please try again.') {
  return `
    <div class="w-full bg-surface border border-rose-200 rounded-lg p-6 bg-rose-50/50 flex items-start gap-4">
      <span class="material-symbols-outlined text-rose-600 text-2xl shrink-0 mt-0.5">error_outline</span>
      <div class="flex flex-col gap-1">
        <div class="text-sm font-bold text-rose-900">${escHtml(title)}</div>
        <div class="text-xs text-rose-700">${escHtml(detail)}</div>
      </div>
    </div>
  `;
}

/** Inline alert for unsupported / unrecognised locations (HTTP 422). */
export function renderUnsupportedLocationAlert() {
  return `
    <div class="p-3.5 rounded border border-[#F1C8C8] bg-[#FDF5F5] text-xs flex items-start gap-2.5">
      <span class="material-symbols-outlined text-[#B82C2C] text-[20px] shrink-0 mt-0.5">error_outline</span>
      <div class="flex flex-col">
        <span class="font-bold text-[#8A1C1C]">We couldn't identify one of the locations.</span>
        <span class="text-charcoal mt-0.5">Try using a nearby station or supported place name (e.g. Aluva, Thrissur, Ernakulam Junction).</span>
      </div>
    </div>
  `;
}

/** Escape HTML to prevent XSS when inserting user or API text. */
function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
