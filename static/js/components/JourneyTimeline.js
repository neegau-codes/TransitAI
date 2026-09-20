/**
 * JourneyTimeline.js - Detailed timeline renderer for selected transit route
 */

import { renderStatusBadge } from './StatusBadge.js';

export function renderJourneyTimeline(route) {
  if (!route || !Array.isArray(route.legs) || route.legs.length === 0) {
    return `
      <div class="p-4 text-center text-xs text-slate-sec">
        No leg details available for this route.
      </div>
    `;
  }

  const legsHtml = route.legs.map((leg, idx) => {
    const isMetro = leg.mode === 'metro';
    const isTrain = leg.mode === 'train';
    const isBus = leg.mode === 'bus';
    const isWalk = leg.mode === 'walk';

    const modeColor = isMetro ? 'bg-primary text-on-primary' :
                      isTrain ? 'bg-accent-rail text-on-primary' :
                      isBus ? 'bg-amber-600 text-white' : 'bg-slate-600 text-white';

    const lineColor = isMetro ? 'border-primary' :
                      isTrain ? 'border-accent-rail' :
                      isBus ? 'border-amber-600' : 'border-slate-400';

    const dotColor = isMetro ? 'bg-primary' :
                     isTrain ? 'bg-accent-rail' :
                     isBus ? 'bg-amber-600' : 'bg-slate-400';

    if (isWalk) {
      return `
        <div class="relative pl-8 pb-6 border-l-2 border-dashed border-border-strong ml-2">
          <span class="absolute -left-[5px] top-1 w-2.5 h-2.5 rounded-full bg-border-strong"></span>
          <div class="bg-amber-50/70 border border-amber-200 rounded-md px-3 py-2 text-xs flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-amber-800 text-[18px]">directions_walk</span>
              <div>
                <span class="font-semibold text-amber-900">Pedestrian Transfer</span>
                <span class="text-[11px] text-amber-800 ml-1">From ${leg.from} to ${leg.to}</span>
              </div>
            </div>
            <div class="text-right">
              <span class="font-bold text-amber-900">${leg.duration_minutes} min</span>
              <span class="text-[11px] text-amber-800 block">Transfer buffer</span>
            </div>
          </div>
        </div>
      `;
    }

    return `
      <div class="relative pl-8 pb-6 border-l-2 ${lineColor} ml-2">
        <span class="absolute -left-[7px] top-0 w-3 h-3 rounded-full ${dotColor} border-2 border-surface"></span>
        
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="px-2 py-0.5 text-[11px] font-bold uppercase rounded ${modeColor}">
              ${leg.mode}
            </span>
            <span class="text-xs font-semibold text-text-primary">${leg.from} → ${leg.to}</span>
            <span class="text-xs text-text-muted">(${leg.provider})</span>
          </div>
          
          <div class="flex items-center gap-1.5">
            ${renderStatusBadge(leg.status)}
            ${leg.source ? `<span class="text-[10px] text-text-faint">Source: ${leg.source}</span>` : ''}
          </div>
        </div>

        <div class="bg-surface-muted border border-border-subtle rounded-md p-3 text-xs flex flex-col gap-2">
          <div class="flex items-center justify-between text-text-primary">
            <div class="flex items-center gap-3">
              <span class="font-bold">${leg.departure || '—'}</span>
              <span class="text-text-muted">${leg.from}</span>
            </div>
          </div>
          
          <div class="flex items-center justify-between py-1 border-y border-border-subtle/80 text-text-muted text-[11px]">
            <span>Duration: <strong>${leg.duration_minutes || '—'} min</strong></span>
            <span>Fare: <strong>₹${leg.fare?.amount ?? '0'}</strong></span>
          </div>
          
          <div class="flex items-center justify-between text-text-primary">
            <div class="flex items-center gap-3">
              <span class="font-bold">${leg.arrival || '—'}</span>
              <span class="text-text-muted">${leg.to}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');

  return `
    <div class="w-full bg-surface border border-border-subtle rounded-lg p-5">
      <div class="flex items-center justify-between pb-3 border-b border-border-subtle mb-4">
        <div class="flex items-center gap-2.5">
          <div class="flex items-center gap-2 text-text-primary font-display font-semibold text-base">
            <span>${route.legs[0]?.from || 'Origin'}</span>
            <span class="material-symbols-outlined text-text-faint text-[16px]">arrow_forward</span>
            <span>${route.legs[route.legs.length - 1]?.to || 'Destination'}</span>
          </div>
          <span class="text-[11px] text-text-muted">• ${route.duration_minutes}m</span>
        </div>
        <div class="text-right flex items-center gap-2">
          <span class="text-[11px] text-text-muted">Total Fare</span>
          <span class="text-xs font-bold text-text-primary">₹${route.fare?.amount ?? 0}</span>
        </div>
      </div>

      <div class="flex flex-col">
        ${legsHtml}
        
        <div class="mt-3 flex items-center gap-2 text-xs text-text-primary font-medium">
          <span class="material-symbols-outlined text-primary text-[18px]">location_on</span>
          <span>Final Destination Reached: ${route.legs[route.legs.length - 1]?.to}</span>
        </div>
      </div>
    </div>
  `;
}
