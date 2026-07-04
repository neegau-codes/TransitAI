/**
 * TransitMap - Reusable Map Component for TransitAI
 * Integrates OpenStreetMap and Leaflet.js
 */

class TransitMap {
    constructor(elementId, center = [10.108, 76.356], zoom = 9) {
        this.map = L.map(elementId, {
            zoomControl: true,
            maxZoom: 18,
            minZoom: 6
        }).setView(center, zoom);

        // Load OpenStreetMap Dark Tiles (CartoDB Dark Matter is perfect for our dark UI!)
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(this.map);

        // Create groups to manage overlay redrawing
        this.routesGroup = L.featureGroup().addTo(this.map);
        this.markersGroup = L.featureGroup().addTo(this.map);

        // Define colors for each mode according to the requirements:
        // Metro = Blue, Train = Green, Bus = Orange, Walk = Gray
        this.modeColors = {
            'metro': '#2563eb', // Blue
            'train': '#10b981', // Green
            'bus': '#f97316',   // Orange
            'walk': '#6b7280'   // Gray
        };
    }

    /**
     * Resets current map visual state (removes all polylines and markers)
     */
    clearMap() {
        this.routesGroup.clearLayers();
        this.markersGroup.clearLayers();
    }

    /**
     * Renders a given route's paths and station nodes
     * @param {Object} route - The selected route option containing segments
     * @param {Object} coordinatesMap - Name-to-coordinates dictionary
     */
    renderRoute(route, coordinatesMap) {
        this.clearMap();

        if (!route || !route.segments || route.segments.length === 0) return;

        const segments = route.segments;
        const allPoints = [];

        // Loop segments to render lines and markers
        segments.forEach((seg, idx) => {
            const srcCoords = coordinatesMap[seg.source_name];
            const dstCoords = coordinatesMap[seg.destination_name];

            if (!srcCoords || !dstCoords) {
                console.warn(`Missing coordinates for segment: ${seg.source_name} -> ${seg.destination_name}`);
                return;
            }

            const p1 = [srcCoords.latitude, srcCoords.longitude];
            const p2 = [dstCoords.latitude, dstCoords.longitude];

            allPoints.push(p1);
            allPoints.push(p2);

            // 1. Draw segment line between locations
            const modeColor = this.modeColors[seg.mode] || '#8b5cf6';
            const polyline = L.polyline([p1, p2], {
                color: modeColor,
                weight: 5,
                opacity: 0.85,
                dashArray: seg.mode === 'walk' ? '5, 8' : null
            });
            polyline.addTo(this.routesGroup);

            // Clean route name (remove Dep/Arr time details)
            const cleanRouteName = seg.route_name.split(' (Dep:')[0];
            polyline.bindTooltip(`${cleanRouteName} (${seg.duration} mins)`, {
                sticky: true,
                direction: 'top'
            });

            // 2. Render source location marker
            const isFirst = (idx === 0);
            this.addStationMarker(seg.source_name, p1, isFirst ? 'origin' : 'intermediate', seg.mode);

            // 3. Render destination marker of last segment
            if (idx === segments.length - 1) {
                this.addStationMarker(seg.destination_name, p2, 'destination', seg.mode);
            }
        });

        // Fit map bounds to show the complete route
        if (allPoints.length > 0) {
            const bounds = L.latLngBounds(allPoints);
            this.map.fitBounds(bounds, {
                padding: [50, 50],
                maxZoom: 14
            });
        }
    }

    /**
     * Adds a customized styled station marker node to the map
     */
    addStationMarker(name, coords, type, mode) {
        let markerColor = '#6b7280';
        let markerRadius = 6;
        let markerWeight = 2;

        if (type === 'origin') {
            markerColor = '#3b82f6'; // Origin Node: Glowing Blue
            markerRadius = 9;
            markerWeight = 3;
        } else if (type === 'destination') {
            markerColor = '#d946ef'; // Destination Node: Glowing Magenta
            markerRadius = 9;
            markerWeight = 3;
        } else {
            // Intermediate station markers match their transit mode color
            markerColor = this.modeColors[mode] || '#6b7280';
            markerRadius = 6;
            markerWeight = 2;
        }

        const marker = L.circleMarker(coords, {
            radius: markerRadius,
            fillColor: '#ffffff',
            fillOpacity: 1.0,
            color: markerColor,
            weight: markerWeight,
            opacity: 1.0
        });

        // Popup Content
        const cleanName = name.replace(/Railway Station|Metro Station|Bus Stand|Bus Stop/g, '').trim();
        const popupContent = `
            <div class="popup-station-title">${cleanName}</div>
            <div class="popup-station-type">${type === 'origin' ? 'Origin Point' : type === 'destination' ? 'Destination Point' : 'Stop / Station'}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${name}</div>
        `;
        marker.bindPopup(popupContent);
        marker.addTo(this.markersGroup);
    }
}
