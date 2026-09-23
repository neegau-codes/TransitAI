/**
 * RouteSummaryCard.js - Recommendation route summary cards for TransitAI Expo Demo.
 *
 * Displays whatever recommendation labels the backend provides:
 *   BEST | FASTEST | CHEAPEST | LEAST WALKING
 * Never fabricates a winner — only renders what the API returns.
 * Missing values are shown as "—", never as zero.
 */

import { renderStatusBadge } from './StatusBadge.js';

const LABEL_ICONS = {
  BEST:          'star',
  FASTEST:       'bolt',
  CHEAPEST:      'payments',
  'LEAST WALKING': 'directions_walk',
};

function labelIcon(label) {
  const u = (label || '').toUpperCase();
  for (const [key, icon] of Object.entries(LABEL_ICONS)) {
    if (u.includes(key)) return icon;
  }
  return 'alt_route';
}

/** Format duration: null → '—', 0 → '0 min', 90 → '1h 30 min' */
function fmtDuration(mins) {
  if (mins === null || mins === undefined) return '—';
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}h ${m} min` : `${m} min`;
}

/** Format fare: null/undefined → 'Unavailable', 0 → '₹0' */
function fmtFare(amount, currency = 'INR') {
  if (amount === null || amount === undefined) return 'Unavailable';
  const sym = currency === 'INR' ? '₹' : currency + ' ';
  return `${sym}${amount}`;
}

/** Format transfers: null → 'Unavailable', 0 → 'Direct', n → 'n Transfer(s)' */
function fmtTransfers(transfers) {
  if (transfers === null || transfers === undefined) return 'Unavailable';
  return transfers === 0 ? 'Direct' : `${transfers} Transfer${transfers > 1 ? 's' : ''}`;
}

/** Format walking: null → 'Unavailable', 0 → '0 min walking' */
function fmtWalking(mins) {
  if (mins === null || mins === undefined) return 'Unavailable';
  return `${mins} min walking`;
}

export function renderRouteSummaryCards(routes, selectedRouteId, _onSelectRoute) {
  if (!Array.isArray(routes) || routes.length === 0) return '';

  return `
    <section class="w-full grid grid-cols-1 md:grid-cols-${Math.min(routes.length, 4)} gap-3.5" id="route-summary-cards-container">
      ${routes.map((route, idx) => {
        const isSelected = route.route_id
          ? route.route_id === selectedRouteId
          : idx === 0 && !selectedRouteId;
        const cardBorder = isSelected
          ? 'border-2 border-primary bg-surface'
          : 'border border-border-subtle bg-surface hover:border-border-strong';
        const labelText  = route.label || route.category || `Option ${idx + 1}`;
        const icon       = labelIcon(labelText);
        const provider   = route.provider
          || (route.legs && route.legs.map(l => l.provider).filter(Boolean).join(' + '))
          || null;

        return `
          <div class="route-summary-card ${cardBorder} rounded-lg p-3.5 cursor-pointer transition-all"
               data-route-id="${escAttr(route.route_id || String(idx))}">

            <!-- Label row -->
            <div class="flex items-center justify-between mb-2">
              <span class="text-[11px] font-bold uppercase tracking-wider ${isSelected ? 'text-primary' : 'text-text-muted'} flex items-center gap-1">
                <span class="material-symbols-outlined text-[14px]">${icon}</span>
                ${escHtml(labelText)}${isSelected ? ' ✓' : ''}
              </span>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-surface-muted text-text-muted border border-border-subtle">
                ${fmtTransfers(route.transfers)}
              </span>
            </div>

            <!-- Duration + Fare -->
            <div class="flex items-baseline justify-between">
              <div>
                <div class="text-2xl font-bold font-display text-text-primary tracking-tight">
                  ${fmtDuration(route.duration_minutes)}
                </div>
                <div class="text-xs text-text-muted mt-0.5">
                  ${escHtml(route.explanation || fmtWalking(route.walking_minutes))}
                </div>
              </div>
              <div class="text-right">
                <div class="text-base font-bold text-text-primary">${fmtFare(route.fare?.amount, route.fare?.currency)}</div>
                <div class="text-[11px] text-text-faint">Fare</div>
              </div>
            </div>

            <!-- Provider + Status row -->
            <div class="mt-3 pt-2.5 border-t border-border-subtle text-[11px] text-text-muted flex items-center justify-between">
              <span>${escHtml(provider || 'Unavailable')}</span>
              ${renderStatusBadge(route.status)}
            </div>
          </div>
        `;
      }).join('')}
    </section>
  `;
}

function escHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function escAttr(str) {
  return String(str || '').replace(/"/g, '&quot;');
}
