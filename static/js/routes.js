/**
 * routes.js - Route Planning and Rendering Logic for TransitAI
 * Integrates map visuals, timelines, form submissions, and coordinate management.
 * v2.1 — Merged with Gemini Canvas mockup polish (header search chip,
 *        recommended ribbon, mode-composition bar). All existing IDs,
 *        function names, and API calls are unchanged.
 */

// Global state
let currentRoutes = null;
let currentPreference = 'fastest';
let dbLocations = {}; // Cache of locations from database
let transitMap = null;

/**
 * Switch between 'structured' (form) and 'ai' (natural language) search tabs.
 * @param {string} mode - 'structured' | 'ai'
 */
function switchSearchMode(mode) {
    const structuredContainer = document.getElementById('structured-search-container');
    const aiContainer = document.getElementById('ai-search-container');
    const btnStructured = document.getElementById('tab-btn-structured');
    const btnAI = document.getElementById('tab-btn-ai');

    if (!structuredContainer || !aiContainer) return;

    if (mode === 'structured') {
        structuredContainer.classList.remove('hidden');
        aiContainer.classList.add('hidden');
        btnStructured.classList.add('active');
        btnStructured.setAttribute('aria-selected', 'true');
        btnAI.classList.remove('active');
        btnAI.setAttribute('aria-selected', 'false');
    } else {
        aiContainer.classList.remove('hidden');
        structuredContainer.classList.add('hidden');
        btnAI.classList.add('active');
        btnAI.setAttribute('aria-selected', 'true');
        btnStructured.classList.remove('active');
        btnStructured.setAttribute('aria-selected', 'false');
    }
}

// Fallback coordinate mapping for all 40 Kerala supported hubs (mock compatibility)
const FALLBACK_COORDINATES = {
    "Aluva Railway Station": { latitude: 10.1081, longitude: 76.3563 },
    "Aluva Metro Station": { latitude: 10.1095, longitude: 76.3570 },
    "Aluva Bus Stand": { latitude: 10.1090, longitude: 76.3558 },
    "Kalamassery Metro Station": { latitude: 10.0520, longitude: 76.3210 },
    "Kalamassery Bus Stop": { latitude: 10.0515, longitude: 76.3205 },
    "Pathadipalam Metro Station": { latitude: 10.0385, longitude: 76.3130 },
    "Edappally Metro Station": { latitude: 10.0245, longitude: 76.3078 },
    "Edappally Bus Stop": { latitude: 10.0240, longitude: 76.3070 },
    "Palarivattom Metro Station": { latitude: 10.0076, longitude: 76.3005 },
    "Kaloor Metro Station": { latitude: 9.9912, longitude: 76.2905 },
    "Kaloor Bus Stop": { latitude: 9.9908, longitude: 76.2900 },
    "Ernakulam Town Railway Station": { latitude: 9.9922, longitude: 76.2870 },
    "Town Hall Metro Station": { latitude: 9.9918, longitude: 76.2885 },
    "North Bus Stop": { latitude: 9.9910, longitude: 76.2865 },
    "Ernakulam Junction Railway Station": { latitude: 9.9678, longitude: 76.2860 },
    "Ernakulam South Metro Station": { latitude: 9.9682, longitude: 76.2875 },
    "South Bus Stop": { latitude: 9.9670, longitude: 76.2855 },
    "Elamkulam Metro Station": { latitude: 9.9654, longitude: 76.3050 },
    "Vytila Metro Station": { latitude: 9.9690, longitude: 76.3200 },
    "Vytila Mobility Hub": { latitude: 9.9685, longitude: 76.3210 },
    "Tripunithura Railway Station": { latitude: 9.9520, longitude: 76.3500 },
    "Tripunithura Metro Station": { latitude: 9.9535, longitude: 76.3512 },
    "Tripunithura Bus Stand": { latitude: 9.9515, longitude: 76.3490 },
    "Angamaly Railway Station": { latitude: 10.1970, longitude: 76.3862 },
    "Angamaly Bus Stand": { latitude: 10.1975, longitude: 76.3870 },
    "Trivandrum Central Railway Station": { latitude: 8.4875, longitude: 76.9515 },
    "Trivandrum Central Bus Station": { latitude: 8.4880, longitude: 76.9520 },
    "Thrissur Railway Station": { latitude: 10.5186, longitude: 76.2163 },
    "Thrissur Bus Stand": { latitude: 10.5210, longitude: 76.2150 },
    "Kozhikode Railway Station": { latitude: 11.2483, longitude: 75.7865 },
    "Kozhikode Bus Stand": { latitude: 11.2490, longitude: 75.7875 },
    "Palakkad Junction Railway Station": { latitude: 10.7937, longitude: 76.6432 },
    "Palakkad Bus Stand": { latitude: 10.7830, longitude: 76.6550 },
    "Kollam Junction Railway Station": { latitude: 8.8872, longitude: 76.5960 },
    "Kollam Bus Stand": { latitude: 8.8900, longitude: 76.5910 },
    "Kottayam Railway Station": { latitude: 9.5898, longitude: 76.5388 },
    "Kottayam Bus Stand": { latitude: 9.5870, longitude: 76.5300 },
    "Kannur Railway Station": { latitude: 11.8745, longitude: 75.3704 },
    "Kannur Bus Stand": { latitude: 11.8750, longitude: 75.3710 },
    "Shoranur Junction Railway Station": { latitude: 10.7588, longitude: 76.2720 }
};

// Initialize page components
document.addEventListener('DOMContentLoaded', () => {
    setDefaultDateTime();
    loadLocationsList();

    // Initialize map
    transitMap = new TransitMap('map');
});

// Set default date to today and time to now
function setDefaultDateTime() {
    const now = new Date();

    // YYYY-MM-DD
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    document.getElementById('date-input').value = `${year}-${month}-${day}`;

    // HH:MM
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    document.getElementById('time-input').value = `${hours}:${minutes}`;
}

// Fetch locations list from API to populate datalist suggestions and cache coordinates
async function loadLocationsList() {
    try {
        const response = await fetch('/api/locations');
        const locations = await response.json();

        const datalist = document.getElementById('location-list');
        datalist.innerHTML = '';

        locations.forEach(loc => {
            // Cache coordinates from database
            dbLocations[loc.name] = {
                latitude: loc.latitude,
                longitude: loc.longitude
            };

            const option = document.createElement('option');
            option.value = loc.name;
            datalist.appendChild(option);
        });
    } catch (e) {
        console.error('Failed to load locations list', e);
    }
}

/**
 * Gets coordinate for location using DB values with fallback mapping
 */
function getLocationCoords(locationName) {
    // 1. Check if we have database coordinates
    if (dbLocations[locationName] && dbLocations[locationName].latitude && dbLocations[locationName].longitude) {
        return dbLocations[locationName];
    }
    // 2. Check if we have fallback coordinates
    if (FALLBACK_COORDINATES[locationName]) {
        return FALLBACK_COORDINATES[locationName];
    }

    // 3. Fallback partial matching
    const keys = Object.keys(FALLBACK_COORDINATES);
    for (const key of keys) {
        if (key.toLowerCase().includes(locationName.toLowerCase()) || locationName.toLowerCase().includes(key.toLowerCase())) {
            return FALLBACK_COORDINATES[key];
        }
    }

    // Default fallback to center of Kochi if nothing matches
    return { latitude: 9.9816, longitude: 76.2999 };
}

// Set preference selection (Fastest, Cheapest, Fewest Transfers)
function setPreference(pref) {
    currentPreference = pref;

    // Map option key → { card id, radio input id }
    const optionMap = {
        'fastest': { card: 'pref-fastest-card', radio: 'pref-fastest' },
        'cheapest': { card: 'pref-cheapest-card', radio: 'pref-cheapest' },
        'fewest_transfers': { card: 'pref-transfers-card', radio: 'pref-transfers' }
    };

    Object.entries(optionMap).forEach(([key, ids]) => {
        const cardEl = document.getElementById(ids.card);
        const radioEl = document.getElementById(ids.radio);
        if (!cardEl) return;

        if (key === pref) {
            cardEl.classList.add('active');
            if (radioEl) radioEl.checked = true;
        } else {
            cardEl.classList.remove('active');
            if (radioEl) radioEl.checked = false;
        }
    });

    // Keep the "Recommended" ribbon on route cards in sync with preference
    updateRecommendedRibbon();
}

// Populate AI text area from examples tags
function useExample(el) {
    document.getElementById('ai-query-input').value = el.textContent;
}

// Show/Hide Panels helper
function showPanel(panelId) {
    document.getElementById(panelId).classList.remove('hidden');
}

function hidePanel(panelId) {
    document.getElementById(panelId).classList.add('hidden');
}

/**
 * Scrolls to and focuses the search console — used by the header's
 * "Edit Search" chip (merged from the mockup's condensed header pattern).
 */
function focusSearchForm() {
    const sidebar = document.getElementById('search-sidebar');
    if (sidebar) sidebar.scrollIntoView({ behavior: 'smooth', block: 'start' });
    const sourceInput = document.getElementById('source-input');
    if (sourceInput) sourceInput.focus();
}

/**
 * Shows/updates the compact header search-context chip once results exist.
 */
function updateHeaderChip(source, destination, time) {
    const chip = document.getElementById('header-search-chip');
    if (!chip) return;
    document.getElementById('chip-source').textContent = source;
    document.getElementById('chip-dest').textContent = destination;
    document.getElementById('chip-time').innerHTML = `<i class="fa-regular fa-clock"></i> ${time}`;
    chip.classList.remove('hidden');
}

// Submit structured search form
async function handleFormSubmit(event) {
    event.preventDefault();

    const source = document.getElementById('source-input').value.trim();
    const destination = document.getElementById('dest-input').value.trim();
    const departureTime = document.getElementById('time-input').value;

    if (!source || !destination) return;

    hidePanel('welcome-panel');
    hidePanel('results-panel');
    hidePanel('error-panel');
    showPanel('loading-panel');

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source: source,
                destination: destination,
                departure_time: departureTime
            })
        });

        const data = await response.json();

        if (data.error) {
            showError('Search Error', data.error);
            return;
        }

        currentRoutes = data;
        displayResults(source, destination, departureTime, null);

    } catch (e) {
        showError('Connection Error', 'Failed to connect to the backend routing engine. Make sure the server is running.');
    }
}

// Submit Natural Language AI Query
async function handleAISubmit() {
    const query = document.getElementById('ai-query-input').value.trim();
    if (!query) return;

    hidePanel('welcome-panel');
    hidePanel('results-panel');
    hidePanel('error-panel');
    showPanel('loading-panel');

    try {
        const response = await fetch('/api/ai-search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });

        const data = await response.json();

        if (data.error) {
            showError('AI Extraction Error', data.error);
            if (data.parsed_params) {
                syncSidebarFields(data.parsed_params);
            }
            return;
        }

        currentRoutes = data.routes;
        syncSidebarFields(data.parsed_params);

        displayResults(
            data.parsed_params.source,
            data.parsed_params.destination,
            data.parsed_params.departure_time,
            data.parsed_params
        );

    } catch (e) {
        showError('AI Connection Error', 'Failed to connect to the AI query processing engine.');
    }
}

// Helper to fill sidebar form fields from NLP parsed details
function syncSidebarFields(params) {
    if (params.source) document.getElementById('source-input').value = params.source;
    if (params.destination) document.getElementById('dest-input').value = params.destination;
    if (params.departure_time) document.getElementById('time-input').value = params.departure_time;
    if (params.preference) setPreference(params.preference);
}

// Helper to display search errors
function showError(title, desc) {
    hidePanel('loading-panel');
    hidePanel('results-panel');

    document.getElementById('error-title').textContent = title;
    document.getElementById('error-desc').textContent = desc;
    showPanel('error-panel');
}

// Render search results on UI
function displayResults(source, destination, time, aiParsedParams) {
    hidePanel('loading-panel');
    hidePanel('error-panel');

    // Update summary header
    document.getElementById('route-direction').innerHTML = `
        ${source} <i class="fa-solid fa-arrow-right-long" style="color: var(--color-primary); margin: 0 0.25rem;"></i> ${destination}
    `;
    document.getElementById('summary-time').textContent = time;

    // Update the compact header search-context chip (merged from mockup)
    updateHeaderChip(source, destination, time);

    const budgetBadge = document.getElementById('summary-budget-badge');
    if (aiParsedParams && aiParsedParams.budget) {
        document.getElementById('summary-budget').textContent = aiParsedParams.budget;
        budgetBadge.classList.remove('hidden');
    } else {
        budgetBadge.classList.add('hidden');
    }

    const aiNotice = document.getElementById('ai-notice');
    if (aiParsedParams) {
        let note = `AI Parsed Context: Preference=${aiParsedParams.preference}`;
        if (aiParsedParams.budget) note += `, Budget=₹${aiParsedParams.budget}`;
        document.getElementById('ai-notice-text').textContent = note;
        aiNotice.classList.remove('hidden');
    } else {
        aiNotice.classList.add('hidden');
    }

    // Populate route cards
    populateRouteCard('fastest', getRouteData('fastest'));
    populateRouteCard('cheapest', getRouteData('cheapest'));
    populateRouteCard('fewest_transfers', getRouteData('fewest_transfers'));

    let defaultOption = currentPreference;
    selectRouteOption(defaultOption);
    updateRecommendedRibbon();
    showPanel('results-panel');
}

// Helper to handle decoupled routes structure (array or dictionary)
function getRouteData(optionKey) {
    if (!currentRoutes) return null;
    if (Array.isArray(currentRoutes)) {
        return currentRoutes.find(r => r.type === optionKey);
    } else if (currentRoutes.routes && Array.isArray(currentRoutes.routes)) {
        return currentRoutes.routes.find(r => r.type === optionKey);
    } else if (currentRoutes[optionKey]) {
        return currentRoutes[optionKey];
    }
    return null;
}

// Helper to render card details
function populateRouteCard(cardKey, route) {
    if (!route) {
        // Hide card if route option is not returned
        document.getElementById(`card-${cardKey}`).style.display = 'none';
        return;
    }
    document.getElementById(`card-${cardKey}`).style.display = 'flex';
    document.getElementById(`${cardKey}-cost`).textContent = `₹${route.total_cost || route.cost || 0}`;

    const totalMin = route.total_duration || route.duration || 0;
    if (totalMin >= 60) {
        const h = Math.floor(totalMin / 60);
        const m = totalMin % 60;
        document.getElementById(`${cardKey}-dur`).innerHTML = `${h} <span>h</span> ${m} <span>m</span>`;
    } else {
        document.getElementById(`${cardKey}-dur`).innerHTML = `${totalMin} <span>mins</span>`;
    }

    const tCount = route.transfers !== undefined ? route.transfers : 0;
    const tText = tCount === 1 ? '1 Transfer' : `${tCount} Transfers`;
    document.getElementById(`${cardKey}-transfers`).textContent = tText;

    const modesDiv = document.getElementById(`${cardKey}-modes`);
    modesDiv.innerHTML = '';

    const modes = [];
    route.segments.forEach(seg => {
        if (!modes.includes(seg.mode)) {
            modes.push(seg.mode);
        }
    });

    modes.forEach(mode => {
        const iconClass = getModeIcon(mode);
        const iconDiv = document.createElement('div');
        iconDiv.className = `mode-mini-icon ${mode}`;
        iconDiv.innerHTML = `<i class="${iconClass}"></i>`;
        modesDiv.appendChild(iconDiv);
    });

    // Mode-composition bar (merged from mockup's progress bar concept,
    // but computed from REAL per-segment durations, not fabricated data).
    renderModeCompositionBar(cardKey, route);
}

/**
 * Renders a slim horizontal bar showing the proportion of total journey
 * duration spent in each transport mode, based on real segment data.
 */
function renderModeCompositionBar(cardKey, route) {
    const bar = document.getElementById(`${cardKey}-composition`);
    if (!bar) return;
    bar.innerHTML = '';

    const totalDuration = route.segments.reduce((sum, seg) => sum + (seg.duration || 0), 0);
    if (totalDuration <= 0) return;

    route.segments.forEach(seg => {
        const pct = ((seg.duration || 0) / totalDuration) * 100;
        if (pct <= 0) return;
        const segDiv = document.createElement('div');
        segDiv.className = `mode-composition-segment ${seg.mode}`;
        segDiv.style.width = `${pct}%`;
        segDiv.title = `${seg.mode}: ${seg.duration} mins`;
        bar.appendChild(segDiv);
    });
}

/**
 * Shows a "Recommended" ribbon on whichever route card matches the
 * currently active preference (merged from mockup's "★ BEST OVERALL" tag).
 */
function updateRecommendedRibbon() {
    const options = ['fastest', 'cheapest', 'fewest_transfers'];
    options.forEach(opt => {
        const ribbon = document.getElementById(`${opt}-ribbon`);
        if (!ribbon) return;
        if (opt === currentPreference) {
            ribbon.classList.remove('hidden');
        } else {
            ribbon.classList.add('hidden');
        }
    });
}

function getModeIcon(mode) {
    switch (mode) {
        case 'metro': return 'fa-solid fa-subway';
        case 'train': return 'fa-solid fa-train';
        case 'bus': return 'fa-solid fa-bus';
        case 'walk': return 'fa-solid fa-person-walking';
        default: return 'fa-solid fa-route';
    }
}

// Handle route selection click
function selectRouteOption(optionKey) {
    const options = ['fastest', 'cheapest', 'fewest_transfers'];
    options.forEach(opt => {
        const card = document.getElementById(`card-${opt}`);
        if (opt === optionKey) {
            card.classList.add('active');
        } else {
            card.classList.remove('active');
        }
    });

    const titleText = optionKey === 'fastest' ? 'Fastest Route' :
        optionKey === 'cheapest' ? 'Cheapest Route' : 'Fewest Transfers';
    document.getElementById('details-route-type').textContent = titleText;

    const route = getRouteData(optionKey);
    if (!route) return;
    document.getElementById('details-segment-count').textContent = route.segments.length;

    renderTimeline(route);

    // Map Render Trigger
    renderRouteOnMap(route);
}

// Render route segments on Leaflet Map
function renderRouteOnMap(route) {
    if (!transitMap) return;

    // Resolve coordinates map for all route locations
    const coordinatesMap = {};
    route.segments.forEach(seg => {
        coordinatesMap[seg.source_name] = getLocationCoords(seg.source_name);
        coordinatesMap[seg.destination_name] = getLocationCoords(seg.destination_name);
    });

    transitMap.renderRoute(route, coordinatesMap);
}

// Render vertical timeline of segments
function renderTimeline(route) {
    const timeline = document.getElementById('route-timeline');
    timeline.innerHTML = '';

    if (!route.segments || route.segments.length === 0) return;

    const segments = route.segments;

    for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        const isOrigin = (i === 0);
        const stepClass = isOrigin ? 'timeline-step origin' : 'timeline-step';

        let depTime = "";
        let arrTime = "";
        const timeMatch = seg.route_name.match(/\(Dep:\s*(\d{2}:\d{2}),\s*Arr:\s*(\d{2}:\d{2})\)/);
        if (timeMatch) {
            depTime = timeMatch[1];
            arrTime = timeMatch[2];
        }

        const sourceStep = document.createElement('div');
        sourceStep.className = stepClass;
        sourceStep.innerHTML = `
            <div class="timeline-node"></div>
            <div class="timeline-content">
                <div class="timeline-header">
                    <span class="station-name">${seg.source_name}</span>
                    <span class="step-time">${depTime ? `<i class="fa-regular fa-clock"></i> ${depTime}` : ''}</span>
                </div>
            </div>
        `;
        timeline.appendChild(sourceStep);

        const travelLink = document.createElement('div');
        travelLink.className = 'timeline-step travel-link';

        const cleanRouteName = seg.route_name.split(' (Dep:')[0];
        const modeIcon = getModeIcon(seg.mode);

        travelLink.innerHTML = `
            <div class="travel-segment-card">
                <div class="segment-mode-icon ${seg.mode}">
                    <i class="${modeIcon}"></i>
                </div>
                <div class="segment-info">
                    <div class="segment-route-name">${cleanRouteName}</div>
                    <div class="segment-details-row">
                        <div class="segment-detail-item">
                            <i class="fa-regular fa-clock"></i>
                            <span>${seg.duration} mins</span>
                        </div>
                        ${seg.mode !== 'walk' ? `
                        <div class="segment-detail-item">
                            <i class="fa-solid fa-indian-rupee-sign"></i>
                            <span>₹${seg.cost}</span>
                        </div>
                        ` : ''}
                    </div>
                    ${seg.mode !== 'walk' ? `
                    <div class="segment-provider">
                        Provider: ${seg.provider}
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
        timeline.appendChild(travelLink);

        if (i === segments.length - 1) {
            const destStep = document.createElement('div');
            destStep.className = 'timeline-step destination';
            destStep.innerHTML = `
                <div class="timeline-node"></div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <span class="station-name">${seg.destination_name}</span>
                        <span class="step-time">${arrTime ? `<i class="fa-regular fa-clock"></i> ${arrTime}` : ''}</span>
                    </div>
                </div>
            `;
            timeline.appendChild(destStep);
        }
    }
}

/**
 * -------------------------------------------------------------
 * MOCK TEST SUITE DATA AND RUNNERS (For Requirement #10 / #6)
 * -------------------------------------------------------------
 */

const MOCK_ROUTES = {
    "Aluva_Kaloor": {
        "fastest": {
            "type": "fastest",
            "cost": 30,
            "duration": 18,
            "transfers": 0,
            "segments": [
                {
                    "source_name": "Aluva Metro Station",
                    "destination_name": "Kaloor Metro Station",
                    "mode": "metro",
                    "route_name": "Kochi Metro Line 1 (Dep: 08:30, Arr: 08:48)",
                    "duration": 18,
                    "cost": 30,
                    "provider": "KMRL"
                }
            ]
        },
        "cheapest": {
            "type": "cheapest",
            "cost": 15,
            "duration": 35,
            "transfers": 0,
            "segments": [
                {
                    "source_name": "Aluva Bus Stand",
                    "destination_name": "Kaloor Bus Stop",
                    "mode": "bus",
                    "route_name": "KSRTC Aluva-Kochi Ordinary (Dep: 08:35, Arr: 09:10)",
                    "duration": 35,
                    "cost": 15,
                    "provider": "KSRTC"
                }
            ]
        },
        "fewest_transfers": {
            "type": "fewest_transfers",
            "cost": 30,
            "duration": 18,
            "transfers": 0,
            "segments": [
                {
                    "source_name": "Aluva Metro Station",
                    "destination_name": "Kaloor Metro Station",
                    "mode": "metro",
                    "route_name": "Kochi Metro Line 1 (Dep: 08:30, Arr: 08:48)",
                    "duration": 18,
                    "cost": 30,
                    "provider": "KMRL"
                }
            ]
        }
    },
    "Aluva_Thrissur": {
        "fastest": {
            "type": "fastest",
            "cost": 45,
            "duration": 48,
            "transfers": 0,
            "segments": [
                {
                    "source_name": "Aluva Railway Station",
                    "destination_name": "Thrissur Railway Station",
                    "mode": "train",
                    "route_name": "Venad Express (16302) (Dep: 10:15, Arr: 11:03)",
                    "duration": 48,
                    "cost": 45,
                    "provider": "Indian Railways"
                }
            ]
        },
        "cheapest": {
            "type": "cheapest",
            "cost": 35,
            "duration": 65,
            "transfers": 0,
            "segments": [
                {
                    "source_name": "Aluva Bus Stand",
                    "destination_name": "Thrissur Bus Stand",
                    "mode": "bus",
                    "route_name": "KSRTC Kochi-Thrissur Ordinary (Dep: 10:20, Arr: 11:25)",
                    "duration": 65,
                    "cost": 35,
                    "provider": "KSRTC"
                }
            ]
        },
        "fewest_transfers": {
            "type": "fewest_transfers",
            "cost": 45,
            "duration": 48,
            "transfers": 0,
            "segments": [
                {
                    "source_name": "Aluva Railway Station",
                    "destination_name": "Thrissur Railway Station",
                    "mode": "train",
                    "route_name": "Venad Express (16302) (Dep: 10:15, Arr: 11:03)",
                    "duration": 48,
                    "cost": 45,
                    "provider": "Indian Railways"
                }
            ]
        }
    },
    "Kochi_Trivandrum": {
        "fastest": {
            "type": "fastest",
            "cost": 160,
            "duration": 215,
            "transfers": 1,
            "segments": [
                {
                    "source_name": "Town Hall Metro Station",
                    "destination_name": "Ernakulam Town Railway Station",
                    "mode": "walk",
                    "route_name": "Walking Transfer (Dep: 07:50, Arr: 07:53)",
                    "duration": 3,
                    "cost": 0,
                    "provider": "Walk"
                },
                {
                    "source_name": "Ernakulam Town Railway Station",
                    "destination_name": "Trivandrum Central Railway Station",
                    "mode": "train",
                    "route_name": "Jan Shatabdi Express (12075) (Dep: 08:05, Arr: 11:37)",
                    "duration": 212,
                    "cost": 160,
                    "provider": "Indian Railways"
                }
            ]
        },
        "cheapest": {
            "type": "cheapest",
            "cost": 120,
            "duration": 280,
            "transfers": 0,
            "segments": [
                {
                    "source_name": "Ernakulam Junction Railway Station",
                    "destination_name": "Trivandrum Central Railway Station",
                    "mode": "train",
                    "route_name": "Parasuram Express (16649) (Dep: 14:00, Arr: 18:40)",
                    "duration": 280,
                    "cost": 120,
                    "provider": "Indian Railways"
                }
            ]
        },
        "fewest_transfers": {
            "type": "fewest_transfers",
            "cost": 120,
            "duration": 280,
            "transfers": 0,
            "segments": [
                {
                    "source_name": "Ernakulam Junction Railway Station",
                    "destination_name": "Trivandrum Central Railway Station",
                    "mode": "train",
                    "route_name": "Parasuram Express (16649) (Dep: 14:00, Arr: 18:40)",
                    "duration": 280,
                    "cost": 120,
                    "provider": "Indian Railways"
                }
            ]
        }
    }
};

/**
 * Loads mock visual test route
 * @param {string} testKey - Key of test case (Aluva_Kaloor, Aluva_Thrissur, Kochi_Trivandrum)
 */
function loadMockTestRoute(testKey) {
    hidePanel('welcome-panel');
    hidePanel('error-panel');
    hidePanel('loading-panel');

    currentRoutes = MOCK_ROUTES[testKey];

    let source = "Aluva";
    let dest = "Kaloor";
    if (testKey === "Aluva_Thrissur") {
        source = "Aluva";
        dest = "Thrissur";
    } else if (testKey === "Kochi_Trivandrum") {
        source = "Kochi";
        dest = "Thiruvananthapuram";
    }

    // Fill sidebar inputs
    document.getElementById('source-input').value = source;
    document.getElementById('dest-input').value = dest;

    displayResults(source, dest, "08:30", { preference: "fastest" });
}