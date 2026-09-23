/**
 * TransitMap.js - Route map fallback component.
 */

export function renderTransitMap(route) {
  const originName = route && route.legs && route.legs[0] ? route.legs[0].from : 'Origin';
  const destName = route && route.legs && route.legs.length > 0 ? route.legs[route.legs.length - 1].to : 'Destination';

  return '<div class="sticky top-20 flex flex-col gap-3">'
    + '<div class="relative w-full h-[480px] bg-[#F4F6F3] border border-border-subtle rounded-lg overflow-hidden flex flex-col items-center justify-center text-center p-6 gap-3">'
    + '<div class="absolute top-3 left-3 right-3 z-10 flex items-center justify-between pointer-events-none">'
    + '<div class="bg-surface/95 border border-border-subtle rounded-md px-3 py-1.5 text-xs text-text-primary font-medium pointer-events-auto shadow-sm flex items-center gap-2">'
    + '<span class="w-2 h-2 rounded-full bg-primary"></span>'
    + '<span>Route Map: ' + escHtml(originName) + ' → ' + escHtml(destName) + '</span>'
    + '</div>'
    + '<div class="bg-surface/90 border border-border-subtle rounded-md px-2 py-1 text-[10px] text-slate-sec pointer-events-auto">STATIC TIMETABLE</div>'
    + '</div>'
    + '<span class="material-symbols-outlined text-4xl text-muted-slate mt-6">map</span>'
    + '<div class="text-sm font-semibold text-charcoal">Map visualization unavailable for this route</div>'
    + '<div class="text-xs text-slate-sec max-w-xs">The journey timeline and route cards above remain fully functional.</div>'
    + '</div>'
    + '</div>';
}

function escHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export function initLeafletMap(route) {
  // Leaflet map disabled per user request
}
