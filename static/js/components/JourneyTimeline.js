/**
 * JourneyTimeline.js - Detailed timeline renderer for TransitAI Expo Demo.
 *
 * Consumes selectedRoute.legs from the normalized API response.
 * Missing values are shown as "—" — never as fake zeros or fabricated data.
 * Status displayed as SCHEDULED | ESTIMATED | UNAVAILABLE only.
 */

import { renderStatusBadge } from './StatusBadge.js';

const MODE_COLORS = {
  metro: { bg: 'bg-primary text-on-primary',         line: 'border-primary',     dot: 'bg-primary'     },
  train: { bg: 'bg-accent-rail text-on-primary',     line: 'border-accent-rail', dot: 'bg-accent-rail' },
  bus:   { bg: 'bg-amber-600 text-white',             line: 'border-amber-600',   dot: 'bg-amber-600'   },
  walk:  { bg: 'bg-slate-400 text-white',             line: 'border-slate-400',   dot: 'bg-slate-400'   },
};

function modeColors(mode) {
  return MODE_COLORS[mode] || MODE_COLORS.walk;
}

function val(v, suffix = '') {
  if (v === null || v === undefined || v === '') return '—';
  return `${v}${suffix}`;
}

function fmtFare(fare) {
  if (!fare || fare.amount === null || fare.amount === undefined) return 'Unavailable';
  const sym = fare.currency === 'INR' ? '₹' : (fare.currency || '') + ' ';
  return `${sym}${fare.amount}`;
}

function renderWalkLeg(leg, idx) {
  return `
    <div class="relative pl-8 pb-6 border-l-2 border-dashed border-border-strong ml-2">
      <span class="absolute -left-[5px] top-1 w-2.5 h-2.5 rounded-full bg-border-strong"></span>
      <div class="bg-amber-50/70 border border-amber-200 rounded-md px-3 py-2 text-xs flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-amber-800 text-[18px]">directions_walk</span>
          <div>
            <span class="font-semibold text-amber-900">Pedestrian Transfer</span>
            <span class="text-[11px] text-amber-800 ml-1">
              ${val(leg.from)} → ${val(leg.to)}
            </span>
          </div>
        </div>
        <div class="text-right">
          <span class="font-bold text-amber-900">${val(leg.duration_minutes, ' min')}</span>
          <span class="text-[11px] text-amber-800 block">Transfer</span>
        </div>
      </div>
    </div>
  `;
}

function renderTransitLeg(leg, idx) {
  const { bg, line, dot } = modeColors(leg.mode);
  const modeLabel = (leg.mode || 'transit').toUpperCase();

  return `
    <div class="relative pl-8 pb-6 border-l-2 ${line} ml-2">
      <span class="absolute -left-[7px] top-0 w-3 h-3 rounded-full ${dot} border-2 border-surface"></span>

      <!-- Header row: mode, from→to, provider, status -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="px-2 py-0.5 text-[11px] font-bold uppercase rounded ${bg}">${modeLabel}</span>
          <span class="text-xs font-semibold text-text-primary">${val(leg.from)} → ${val(leg.to)}</span>
          ${leg.provider ? `<span class="text-xs text-text-muted">(${escHtml(leg.provider)})</span>` : ''}
        </div>
        <div class="flex items-center gap-1.5">
          ${renderStatusBadge(leg.status)}
          ${leg.source ? `<span class="text-[10px] text-text-faint">${escHtml(leg.source)}</span>` : ''}
        </div>
      </div>

      <!-- Timing & fare card -->
      <div class="bg-surface-muted border border-border-subtle rounded-md p-3 text-xs flex flex-col gap-2">
        <!-- Departure -->
        <div class="flex items-center justify-between text-text-primary">
          <div class="flex items-center gap-3">
            <span class="font-bold">${val(leg.departure)}</span>
            <span class="text-text-muted">${val(leg.from)}</span>
          </div>
        </div>

        <!-- Duration + Fare -->
        <div class="flex items-center justify-between py-1 border-y border-border-subtle/80 text-text-muted text-[11px]">
          <span>Duration: <strong>${val(leg.duration_minutes, ' min')}</strong></span>
          <span>Fare: <strong>${fmtFare(leg.fare)}</strong></span>
        </div>

        <!-- Arrival -->
        <div class="flex items-center justify-between text-text-primary">
          <div class="flex items-center gap-3">
            <span class="font-bold">${val(leg.arrival)}</span>
            <span class="text-text-muted">${val(leg.to)}</span>
          </div>
        </div>
      </div>
    </div>
  `;
}

export function renderJourneyTimeline(route) {
  if (!route || !Array.isArray(route.legs) || route.legs.length === 0) {
    return `
      <div class="p-4 text-center text-xs text-slate-sec">
        No leg details available for this route.
      </div>
    `;
  }

  const legsHtml = route.legs.map((leg, idx) =>
    leg.mode === 'walk' ? renderWalkLeg(leg, idx) : renderTransitLeg(leg, idx)
  ).join('');

  const origin = route.legs[0]?.from || '—';
  const dest   = route.legs[route.legs.length - 1]?.to || '—';
  const durStr = route.duration_minutes !== null && route.duration_minutes !== undefined
    ? `${route.duration_minutes}m`
    : '—';
  const fareStr = route.fare?.amount !== null && route.fare?.amount !== undefined
    ? `₹${route.fare.amount}`
    : 'Unavailable';

  return `
    <div class="w-full bg-surface border border-border-subtle rounded-lg p-5">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-border-subtle mb-4">
        <div class="flex items-center gap-2.5">
          <div class="flex items-center gap-2 text-text-primary font-display font-semibold text-base">
            <span>${escHtml(origin)}</span>
            <span class="material-symbols-outlined text-text-faint text-[16px]">arrow_forward</span>
            <span>${escHtml(dest)}</span>
          </div>
          <span class="text-[11px] text-text-muted">• ${durStr}</span>
        </div>
        <div class="text-right flex items-center gap-2">
          <span class="text-[11px] text-text-muted">Total Fare</span>
          <span class="text-xs font-bold text-text-primary">${fareStr}</span>
        </div>
      </div>

      <!-- Leg list -->
      <div class="flex flex-col">
        ${legsHtml}

        <!-- Final destination -->
        <div class="mt-3 flex items-center gap-2 text-xs text-text-primary font-medium">
          <span class="material-symbols-outlined text-primary text-[18px]">location_on</span>
          <span>Arrive: ${escHtml(dest)}</span>
        </div>
      </div>
    </div>
  `;
}

function escHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
