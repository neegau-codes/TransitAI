/**
 * StateViews.js - Reusable UI state view generators for TransitAI
 */

export function renderLoadingState(message = "Searching multi-modal transit routes...") {
  return `
    <div class="w-full bg-surface border border-border-subtle rounded-lg p-8 flex flex-col items-center justify-center text-center gap-3">
      <div class="w-10 h-10 border-3 border-deep-teal/20 border-t-deep-teal rounded-full animate-spin"></div>
      <div class="text-sm font-semibold text-charcoal">${message}</div>
      <div class="text-xs text-slate-sec">Connecting live Kochi Metro, Indian Railways & KSRTC data...</div>
    </div>
  `;
}

export function renderEmptyState(message = "No routes found") {
  return `
    <div class="w-full bg-surface border border-border-subtle rounded-lg p-8 flex flex-col items-center justify-center text-center gap-3">
      <span class="material-symbols-outlined text-4xl text-muted-slate">no_transfer</span>
      <div class="text-sm font-bold text-charcoal">${message}</div>
      <div class="text-xs text-slate-sec max-w-sm">No available transit routes match your selected origins or departure times. Try selecting a different date or nearby station hub.</div>
    </div>
  `;
}

export function renderErrorState(title = "Unable to load routes", detail = "Please try again.") {
  return `
    <div class="w-full bg-surface border border-rose-200 rounded-lg p-6 bg-rose-50/50 flex items-start gap-4">
      <span class="material-symbols-outlined text-rose-600 text-2xl shrink-0 mt-0.5">error_outline</span>
      <div class="flex flex-col gap-1">
        <div class="text-sm font-bold text-rose-900">${title}</div>
        <div class="text-xs text-rose-700">${detail}</div>
      </div>
    </div>
  `;
}

export function renderUnsupportedLocationAlert() {
  return `
    <div class="p-3.5 rounded border border-[#F1C8C8] bg-[#FDF5F5] text-xs flex items-start gap-2.5">
      <span class="material-symbols-outlined text-[#B82C2C] text-[20px] shrink-0 mt-0.5">error_outline</span>
      <div class="flex flex-col">
        <span class="font-bold text-[#8A1C1C]">Location not supported yet</span>
        <span class="text-charcoal mt-0.5">We couldn't connect this location to available transit data. Please choose a supported railway station, metro node, or bus hub.</span>
      </div>
    </div>
  `;
}
