/**
 * RouteSummaryCard.js - Top route summary recommendation cards component
 */

import { renderStatusBadge } from './StatusBadge.js';

export function renderRouteSummaryCards(routes, selectedRouteId, onSelectRoute) {
  if (!Array.isArray(routes) || routes.length === 0) return '';

  return `
    <section class="w-full grid grid-cols-1 md:grid-cols-3 gap-3.5" id="route-summary-cards-container">
      ${routes.map((route, idx) => {
        const isSelected = route.route_id === selectedRouteId || (idx === 0 && !selectedRouteId);
        const cardBorder = isSelected ? 'border-2 border-primary bg-surface' : 'border border-border-subtle bg-surface hover:border-border-strong';
        const labelText = route.label || route.category || `Option ${idx + 1}`;
        const isFastest = labelText.toUpperCase().includes('FASTEST');
        const isCheapest = labelText.toUpperCase().includes('CHEAPEST');

        const badgeIcon = isFastest ? 'bolt' : isCheapest ? 'payments' : 'alt_route';

        return `
          <div class="route-summary-card ${cardBorder} rounded-lg p-3.5 cursor-pointer transition-all" 
               data-route-id="${route.route_id}">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[11px] font-bold uppercase tracking-wider ${isSelected ? 'text-primary' : 'text-text-muted'} flex items-center gap-1">
                <span class="material-symbols-outlined text-[14px]">${badgeIcon}</span>
                ${labelText} ${isSelected ? '(Selected)' : ''}
              </span>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-surface-muted text-text-muted border border-border-subtle">
                ${route.transfers === 0 ? 'Direct' : `${route.transfers} Transfer${route.transfers > 1 ? 's' : ''}`}
              </span>
            </div>

            <div class="flex items-baseline justify-between">
              <div>
                <div class="text-2xl font-bold font-display text-text-primary tracking-tight">
                  ${Math.floor(route.duration_minutes / 60) > 0 ? `${Math.floor(route.duration_minutes / 60)}h ` : ''}${route.duration_minutes % 60} min
                </div>
                <div class="text-xs text-text-muted mt-0.5">${route.explanation || 'Optimized multi-modal route'}</div>
              </div>
              <div class="text-right">
                <div class="text-base font-bold text-text-primary">₹${route.fare?.amount ?? 0}</div>
                <div class="text-[11px] text-text-faint">Fare</div>
              </div>
            </div>

            <div class="mt-3 pt-2.5 border-t border-border-subtle text-[11px] text-text-muted flex items-center justify-between">
              <span>${route.legs ? route.legs.map(l => l.provider || l.mode).filter((v, i, a) => a.indexOf(v) === i).join(' + ') : 'Transit'}</span>
              ${renderStatusBadge(route.status)}
            </div>
          </div>
        `;
      }).join('')}
    </section>
  `;
}
