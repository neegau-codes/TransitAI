/**
 * TransitMap.js - Transit Map container component for TransitAI
 */

export function renderTransitMap(route) {
  const originName = route?.legs?.[0]?.from || "Origin";
  const destName = route?.legs?.[route.legs.length - 1]?.to || "Destination";

  return `
    <div class="sticky top-20 flex flex-col gap-3">
      <div class="relative w-full h-[580px] bg-[#F4F6F3] border border-border-subtle rounded-lg overflow-hidden flex flex-col" id="map-canvas-container">
        <!-- Header Info Bar -->
        <div class="absolute top-3 left-3 right-3 z-10 flex items-center justify-between pointer-events-none">
          <div class="bg-surface/95 border border-border-subtle rounded-md px-3 py-1.5 text-xs text-text-primary font-medium pointer-events-auto shadow-sm flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-primary"></span>
            <span>Corridor Map: ${originName} → ${destName}</span>
          </div>
          <div class="flex items-center bg-surface border border-border-subtle rounded-md shadow-sm overflow-hidden pointer-events-auto">
            <button class="w-8 h-8 flex items-center justify-center hover:bg-surface-muted text-text-muted border-r border-border-subtle" title="Zoom In" type="button">
              <span class="material-symbols-outlined text-[18px]">add</span>
            </button>
            <button class="w-8 h-8 flex items-center justify-center hover:bg-surface-muted text-text-muted border-r border-border-subtle" title="Zoom Out" type="button">
              <span class="material-symbols-outlined text-[18px]">remove</span>
            </button>
            <button class="w-8 h-8 flex items-center justify-center hover:bg-surface-muted text-text-muted" title="Recenter Route" type="button">
              <span class="material-symbols-outlined text-[18px]">crop_free</span>
            </button>
          </div>
        </div>

        <!-- Map cartographic view -->
        <svg class="w-full h-full" fill="none" viewBox="0 0 640 560" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern height="32" id="cartoGrid" patternUnits="userSpaceOnUse" width="32">
              <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#E5E9E4" stroke-width="0.75"></path>
            </pattern>
          </defs>
          <rect fill="#F5F7F4" height="100%" width="100%"></rect>
          <rect fill="url(#cartoGrid)" height="100%" width="100%"></rect>

          <!-- Waterway path (Periyar River) -->
          <path d="M-10 180 C 120 170, 180 200, 220 230 C 260 260, 290 320, 240 420 C 210 480, 180 520, 140 570" fill="none" stroke="#D7E4E2" stroke-linecap="round" stroke-width="18"></path>
          <text fill="#9FB5B1" font-size="10" font-weight="600" letter-spacing="2" x="250" y="380">KERALA TRANSIT CORRIDOR</text>

          <!-- Route indicator nodes -->
          <g transform="translate(180, 220)">
            <circle cx="0" cy="0" fill="#FFFFFF" r="8" stroke="#087F73" stroke-width="3"></circle>
            <circle cx="0" cy="0" fill="#087F73" r="3.5"></circle>
            <rect fill="#FFFFFF" height="26" rx="4" stroke="#CBD0CB" stroke-width="1" width="140" x="14" y="-13"></rect>
            <text fill="#1A201E" font-family="Inter" font-size="10" font-weight="700" x="22" y="3">${originName.toUpperCase()}</text>
          </g>

          <g transform="translate(460, 120)">
            <circle cx="0" cy="0" fill="#FFFFFF" r="10" stroke="#005696" stroke-width="3.5"></circle>
            <circle cx="0" cy="0" fill="#005696" r="4.5"></circle>
            <rect fill="#FFFFFF" height="26" rx="4" stroke="#005696" stroke-width="1.5" width="160" x="-170" y="-13"></rect>
            <text fill="#005696" font-family="Inter" font-size="10" font-weight="700" x="-162" y="3">${destName.toUpperCase()}</text>
          </g>
        </svg>
      </div>
    </div>
  `;
}
