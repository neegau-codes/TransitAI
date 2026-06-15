// Global variables to store current search results
let currentRoutes = null;
let currentPreference = 'fastest';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    setDefaultTime();
    loadLocations();
});

// Set default time to current local time (HH:MM)
function setDefaultTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    document.getElementById('time-input').value = `${hours}:${minutes}`;
}

// Fetch locations list from API to populate datalist suggestions
async function loadLocations() {
    try {
        const response = await fetch('/api/locations');
        const locations = await response.json();
        
        const datalist = document.getElementById('location-list');
        datalist.innerHTML = '';
        
        // Add to datalist
        locations.forEach(loc => {
            const option = document.createElement('option');
            option.value = loc.name;
            datalist.appendChild(option);
        });
    } catch (e) {
        console.error('Failed to load locations list', e);
    }
}

// Set preference selection (Fastest, Cheapest, Fewest Transfers)
function setPreference(pref) {
    currentPreference = pref;
    
    // Update active visual state in sidebar selector
    const cards = {
        'fastest': 'pref-fastest-card',
        'cheapest': 'pref-cheapest-card',
        'fewest_transfers': 'pref-transfers-card'
    };
    
    Object.keys(cards).forEach(key => {
        const el = document.getElementById(cards[key]);
        if (key === pref) {
            el.classList.add('active');
            document.getElementById(`pref-${key}`).checked = true;
        } else {
            el.classList.remove('active');
            document.getElementById(`pref-${key}`).checked = false;
        }
    });
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

// Submit structured search form
async function handleFormSubmit(event) {
    event.preventDefault();
    
    const source = document.getElementById('source-input').value.strip ? document.getElementById('source-input').value.strip() : document.getElementById('source-input').value.trim();
    const destination = document.getElementById('dest-input').value.strip ? document.getElementById('dest-input').value.strip() : document.getElementById('dest-input').value.trim();
    const departureTime = document.getElementById('time-input').value;
    
    if (!source || !destination) return;
    
    // Show loading, reset panels
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
    
    // Show loading, reset panels
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
            // If we successfully extracted some parts, sync them anyway so user can complete it
            if (data.parsed_params) {
                syncSidebarFields(data.parsed_params);
            }
            return;
        }
        
        currentRoutes = data.routes;
        
        // Sync Sidebar UI inputs with parsed variables
        syncSidebarFields(data.parsed_params);
        
        // Render results and highlight AI parsed badge details
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
    
    // Display budget constraint badge if specified
    const budgetBadge = document.getElementById('summary-budget-badge');
    if (aiParsedParams && aiParsedParams.budget) {
        document.getElementById('summary-budget').textContent = aiParsedParams.budget;
        budgetBadge.classList.remove('hidden');
    } else {
        budgetBadge.classList.add('hidden');
    }
    
    // Display AI notice badge
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
    populateRouteCard('fastest', currentRoutes.fastest);
    populateRouteCard('cheapest', currentRoutes.cheapest);
    populateRouteCard('fewest_transfers', currentRoutes.fewest_transfers);
    
    // Switch to active card based on preference
    let defaultOption = currentPreference;
    if (defaultOption === 'fewest_transfers') defaultOption = 'fewest_transfers';
    
    selectRouteOption(defaultOption);
    showPanel('results-panel');
}

// Helper to render card details
function populateRouteCard(cardKey, route) {
    document.getElementById(`${cardKey}-cost`).textContent = `₹${route.total_cost}`;
    
    // Calculate display duration (hours + mins)
    const totalMin = route.total_duration;
    if (totalMin >= 60) {
        const h = Math.floor(totalMin / 60);
        const m = totalMin % 60;
        document.getElementById(`${cardKey}-dur`).innerHTML = `${h} <span>h</span> ${m} <span>m</span>`;
    } else {
        document.getElementById(`${cardKey}-dur`).innerHTML = `${totalMin} <span>mins</span>`;
    }
    
    // Transfer count
    const tCount = route.transfers;
    const tText = tCount === 1 ? '1 Transfer' : `${tCount} Transfers`;
    document.getElementById(`${cardKey}-transfers`).textContent = tText;
    
    // Render modes mini icons
    const modesDiv = document.getElementById(`${cardKey}-modes`);
    modesDiv.innerHTML = '';
    
    // Get unique modes in order (skipping walks if we have other modes)
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
}

// Get mode-specific FontAwesome class
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
    // Set active class on cards
    const options = ['fastest', 'cheapest', 'fewest_transfers'];
    options.forEach(opt => {
        const card = document.getElementById(`card-${opt}`);
        if (opt === optionKey) {
            card.classList.add('active');
        } else {
            card.classList.remove('active');
        }
    });
    
    // Update timeline panel titles
    const titleText = optionKey === 'fastest' ? 'Fastest Route' :
                     optionKey === 'cheapest' ? 'Cheapest Route' : 'Fewest Transfers';
    document.getElementById('details-route-type').textContent = titleText;
    
    const route = currentRoutes[optionKey];
    document.getElementById('details-segment-count').textContent = route.segments.length;
    
    renderTimeline(route);
}

// Render vertical timeline of segments
function renderTimeline(route) {
    const timeline = document.getElementById('route-timeline');
    timeline.innerHTML = '';
    
    if (!route.segments || route.segments.length === 0) return;
    
    const segments = route.segments;
    
    // Step-by-step rendering
    for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        
        // 1. Render Source Station Node of this segment
        const isOrigin = (i === 0);
        const stepClass = isOrigin ? 'timeline-step origin' : 'timeline-step';
        
        // Parse time: E.g., route_name can contain "(Dep: 08:30, Arr: 08:48)"
        // Let's parse departure and arrival times from segment details if possible
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
        
        // 2. Render Travel Link (connecting segment card)
        const travelLink = document.createElement('div');
        travelLink.className = 'timeline-step travel-link';
        
        // Clean route name (remove Dep/Arr time details)
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
        
        // 3. If it is the last segment, render the final Destination Station Node
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
