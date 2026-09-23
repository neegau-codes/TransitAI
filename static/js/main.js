/**
 * main.js - Core application controller for TransitAI
 */

import { api } from './api.js';
import { renderRouteSummaryCards } from './components/RouteSummaryCard.js';
import { renderJourneyTimeline } from './components/JourneyTimeline.js';
import { renderTransitMap, initLeafletMap } from './components/TransitMap.js';
import {
  renderLoadingState,
  renderEmptyState,
  renderErrorState,
  renderUnsupportedLocationAlert
} from './components/StateViews.js';


let availableLocations = [];
let currentRoutes = [];
let selectedRouteId = null;
let currentOptimization = 'fastest';

document.addEventListener('DOMContentLoaded', async () => {
  initModeTabs();
  initOptimizationCards();
  initFormInteractions();
  await loadLocations();
});

// 1. Mode Tabs (Planner vs Ask AI)
function initModeTabs() {
  const plannerBtn = document.getElementById('tab-btn-planner');
  const askaiBtn = document.getElementById('tab-btn-askai');
  const plannerView = document.getElementById('view-planner');
  const askaiView = document.getElementById('view-askai');

  if (plannerBtn && askaiBtn && plannerView && askaiView) {
    plannerBtn.addEventListener('click', () => switchTab('planner'));
    askaiBtn.addEventListener('click', () => switchTab('askai'));
  }
}

function switchTab(mode) {
  const plannerBtn = document.getElementById('tab-btn-planner');
  const askaiBtn = document.getElementById('tab-btn-askai');
  const plannerView = document.getElementById('view-planner');
  const askaiView = document.getElementById('view-askai');

  if (mode === 'planner') {
    plannerView.classList.remove('hidden');
    plannerView.classList.add('flex');
    askaiView.classList.add('hidden');
    askaiView.classList.remove('flex');

    plannerBtn.className = 'px-4 py-1.5 rounded font-medium text-xs sm:text-sm transition-colors flex items-center gap-1.5 bg-deep-teal text-white shadow-xs';
    plannerBtn.setAttribute('aria-selected', 'true');
    askaiBtn.className = 'px-4 py-1.5 rounded font-medium text-xs sm:text-sm transition-colors flex items-center gap-1.5 text-slate-sec hover:text-charcoal';
    askaiBtn.setAttribute('aria-selected', 'false');
  } else {
    askaiView.classList.remove('hidden');
    askaiView.classList.add('flex');
    plannerView.classList.add('hidden');
    plannerView.classList.remove('flex');

    askaiBtn.className = 'px-4 py-1.5 rounded font-medium text-xs sm:text-sm transition-colors flex items-center gap-1.5 bg-deep-teal text-white shadow-xs';
    askaiBtn.setAttribute('aria-selected', 'true');
    plannerBtn.className = 'px-4 py-1.5 rounded font-medium text-xs sm:text-sm transition-colors flex items-center gap-1.5 text-slate-sec hover:text-charcoal';
    plannerBtn.setAttribute('aria-selected', 'false');
  }
}

// 2. Optimization Cards
function initOptimizationCards() {
  const opts = ['fastest', 'cheapest', 'transfers'];
  opts.forEach(opt => {
    const card = document.getElementById(`opt-${opt}`);
    if (card) {
      card.addEventListener('click', () => setOptimization(opt));
    }
  });
}

function setOptimization(selected) {
  currentOptimization = selected;
  const types = ['fastest', 'cheapest', 'transfers'];
  types.forEach(t => {
    const card = document.getElementById('opt-' + t);
    const icon = document.getElementById('icon-' + t);
    const label = card?.querySelector('span');

    if (t === selected) {
      if (card) {
        card.className = 'p-2.5 sm:p-3 rounded border border-deep-teal bg-pale-teal text-left flex flex-col justify-between transition-colors';
        card.setAttribute('aria-checked', 'true');
      }
      if (icon) icon.className = 'material-symbols-outlined text-deep-teal text-[16px] leading-none';
      if (label) label.className = 'text-[11px] font-bold tracking-wider text-deep-teal';
    } else {
      if (card) {
        card.className = 'p-2.5 sm:p-3 rounded border border-border-subtle bg-surface hover:bg-app-bg text-left flex flex-col justify-between transition-colors';
        card.setAttribute('aria-checked', 'false');
      }
      if (icon) icon.className = 'material-symbols-outlined text-transparent text-[16px] leading-none';
      if (label) label.className = 'text-[11px] font-bold tracking-wider text-slate-sec';
    }
  });
}

// 3. Form & Location Autocomplete
async function loadLocations() {
  try {
    const locations = await api.getLocations();
    availableLocations = locations;
    populateDatalist(locations);
  } catch (err) {
    console.warn("Failed loading locations", err);
  }
}

function populateDatalist(locations) {
  const datalist = document.getElementById('locations-datalist');
  if (!datalist) return;
  datalist.innerHTML = locations.map(loc => `<option value="${loc.name}">${loc.type ? `[${loc.type}]` : ''}</option>`).join('');
}

function initFormInteractions() {
  const originInput = document.getElementById('input-origin');
  const destInput = document.getElementById('input-destination');
  const dateInput = document.getElementById('input-date');
  const timeInput = document.getElementById('input-time');
  const swapBtn = document.getElementById('btn-swap-endpoints');
  const searchBtn = document.getElementById('btn-search-routes');
  const aiSubmitBtn = document.getElementById('btn-analyse-ai');
  const aiInput = document.getElementById('ai-query-input');
  const samplePromptBtn = document.getElementById('btn-sample-prompt');

  // Set default date and time to current system date and time
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');

  if (dateInput) dateInput.value = `${year}-${month}-${day}`;
  if (timeInput) timeInput.value = `${hours}:${minutes}`;

  if (swapBtn && originInput && destInput) {
    swapBtn.addEventListener('click', () => {
      const temp = originInput.value;
      originInput.value = destInput.value;
      destInput.value = temp;
      hideValidationAlert();
    });
  }

  if (searchBtn) {
    searchBtn.addEventListener('click', handlePlannerSearch);
  }

  if (aiSubmitBtn) {
    aiSubmitBtn.addEventListener('click', handleAISearch);
  }

  if (samplePromptBtn && aiInput) {
    samplePromptBtn.addEventListener('click', () => {
      aiInput.value = "naale 5 manikku munpe aluva ninn thrissur ethande";
    });
  }

  [originInput, destInput].forEach(inp => {
    if (inp) {
      inp.addEventListener('input', () => hideValidationAlert());
    }
  });
}

function hideValidationAlert() {
  const alertBox = document.getElementById('validation-alert');
  if (alertBox) alertBox.classList.add('hidden');
}

function showUnsupportedLocationError() {
  const alertBox = document.getElementById('validation-alert');
  if (alertBox) {
    alertBox.innerHTML = renderUnsupportedLocationAlert();
    alertBox.classList.remove('hidden');
  }
}

// 4. Planner Search Handler
async function handlePlannerSearch() {
  const originInput = document.getElementById('input-origin');
  const destInput = document.getElementById('input-destination');
  const dateInput = document.getElementById('input-date');
  const timeInput = document.getElementById('input-time');

  const now = new Date();
  const currentDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  const currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

  const origin = originInput?.value?.trim();
  const dest = destInput?.value?.trim();
  const date = dateInput?.value || currentDate;
  const time = timeInput?.value || currentTime;

  hideValidationAlert();

  if (!origin || !dest) {
    showUnsupportedLocationError();
    return;
  }

  showResultsContainer();
  renderState(renderLoadingState("Searching transit routes..."));

  try {
    const res = await api.getRoutes(origin, dest, date, time, currentOptimization.toUpperCase());
    
    if (!res || !res.routes || res.routes.length === 0) {
      renderState(renderEmptyState(`No routes found from ${origin} to ${dest}`));
      return;
    }

    currentRoutes = res.routes;
    selectedRouteId = currentRoutes[0].route_id;
    renderResultsView(res);
  } catch (err) {
    if (err.status === 422 || err.message?.includes("Location") || err.message?.includes("connect")) {
      showUnsupportedLocationError();
      renderState(renderErrorState("Location not supported yet", "We couldn't connect this location to available transit data. Please select another station hub."));
    } else {
      renderState(renderErrorState("Unable to load routes", err.message || "Please check backend connection and try again."));
    }
  }
}

// 5. Ask AI Search Handler
async function handleAISearch() {
  const aiInput = document.getElementById('ai-query-input');
  const query = aiInput?.value?.trim();

  if (!query) {
    alert("Please enter a travel query.");
    return;
  }

  showResultsContainer();
  renderState(renderLoadingState("Analyzing natural language travel query with AI..."));

  try {
    const res = await api.search(query);

    if (res.status === "UNSUPPORTED_LOCATION" || !res.routes || res.routes.length === 0) {
      if (res.intent?.origin) {
        renderState(renderEmptyState(`No transit routes available for ${res.intent.origin} → ${res.intent.destination}`));
      } else {
        showUnsupportedLocationError();
        renderState(renderErrorState("Location not supported yet", "We couldn't connect this location to available transit data. Please specify supported Kerala hubs (e.g. Aluva, Thrissur, Ernakulam)."));
      }
      return;
    }

    currentRoutes = res.routes;
    selectedRouteId = currentRoutes[0].route_id;
    renderResultsView(res);
  } catch (err) {
    renderState(renderErrorState("Unable to load routes", err.message || "Failed to process AI query."));
  }
}

// 6. Render Results Page
function showResultsContainer() {
  const resultsSection = document.getElementById('results-section');
  if (resultsSection) {
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth' });
  }
}

function renderState(htmlContent) {
  const contentBox = document.getElementById('results-content-area');
  if (contentBox) contentBox.innerHTML = htmlContent;
}

function renderResultsView(response) {
  const contentBox = document.getElementById('results-content-area');
  if (!contentBox) return;

  const routes = response.routes;
  const selectedRoute = routes.find(r => r.route_id === selectedRouteId) || routes[0];

  const summaryCardsHtml = renderRouteSummaryCards(routes, selectedRoute.route_id, (routeId) => {
    selectedRouteId = routeId;
    renderResultsView(response);
  });

  const timelineHtml = renderJourneyTimeline(selectedRoute);
  const mapHtml = renderTransitMap(selectedRoute);

  contentBox.innerHTML = `
    <div class="flex flex-col gap-5 w-full">
      <!-- 1. Top Summary Header -->
      <section class="w-full bg-surface border border-border-subtle rounded-lg p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2 font-display font-bold text-lg text-text-primary bg-surface-muted px-4 py-2 rounded-md border border-border-subtle">
            <span>${selectedRoute.legs[0]?.from || response.intent?.origin || 'Origin'}</span>
            <span class="material-symbols-outlined text-text-muted text-[18px]">arrow_forward</span>
            <span>${selectedRoute.legs[selectedRoute.legs.length - 1]?.to || response.intent?.destination || 'Destination'}</span>
          </div>
        </div>
        <div class="flex items-center gap-2 text-xs text-slate-sec">
          <span class="px-2.5 py-1 rounded bg-surface border border-border-subtle">
            Found ${routes.length} Multimodal Option${routes.length > 1 ? 's' : ''}
          </span>
        </div>
      </section>

      <!-- 2. Three Recommendation Cards -->
      ${summaryCardsHtml}

      <!-- 3. Timeline (Left) & Map (Right) -->
      <div class="w-full grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        <div class="lg:col-span-6 flex flex-col gap-4">
          ${timelineHtml}
        </div>
        <div class="lg:col-span-6">
          ${mapHtml}
        </div>
      </div>
    </div>
  `;

  // Attach card click handlers
  const cards = contentBox.querySelectorAll('.route-summary-card');
  cards.forEach(card => {
    card.addEventListener('click', () => {
      const rId = card.getAttribute('data-route-id');
      if (rId) {
        selectedRouteId = rId;
        renderResultsView(response);
      }
    });
  });

  // Initialize leaflet map
  initLeafletMap(selectedRoute);
}
