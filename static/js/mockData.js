/**
 * mockData.js - Development fallback mock transit data for TransitAI.
 * Uses realistic Kerala transit hubs (Aluva, Ernakulam, Thrissur).
 */

export const USE_MOCK_API = false; // Set to true only for offline development

export const MOCK_LOCATIONS = [
  { id: 1, name: "Aluva Railway Station", type: "rail", latitude: 10.1097, longitude: 76.3517 },
  { id: 2, name: "Aluva Metro Station", type: "metro", latitude: 10.1098, longitude: 76.3508 },
  { id: 3, name: "Ernakulam Town (North)", type: "rail", latitude: 9.9912, longitude: 76.2882 },
  { id: 4, name: "Ernakulam Junction (South)", type: "rail", latitude: 9.9702, longitude: 76.2871 },
  { id: 5, name: "Kaloor Metro Station", type: "metro", latitude: 9.9961, longitude: 76.2934 },
  { id: 6, name: "MG Road Metro Station", type: "metro", latitude: 9.9774, longitude: 76.2798 },
  { id: 7, name: "Thrissur Railway Station", type: "rail", latitude: 10.5177, longitude: 76.2137 },
  { id: 8, name: "Thrissur KSRTC Bus Stand", type: "bus", latitude: 10.5185, longitude: 76.2120 }
];

export const MOCK_SEARCH_RESPONSE = {
  intent: {
    origin: "Aluva",
    destination: "Thrissur",
    date: "2026-09-21",
    arrive_before: "17:00",
    depart_after: null,
    budget: null,
    preferred_modes: []
  },
  status: "OK",
  routes: [
    {
      route_id: "rt_aluva_thrissur_fastest",
      label: "Fastest",
      category: "Fastest",
      duration_minutes: 55,
      fare: {
        amount: 45,
        currency: "INR",
        status: "SCHEDULED"
      },
      transfers: 0,
      walking_minutes: 3,
      status: "LIVE",
      legs: [
        {
          mode: "train",
          provider: "Indian Railways",
          from: "Aluva Railway Station",
          to: "Thrissur Railway Station",
          departure: "08:15",
          arrival: "09:10",
          duration_minutes: 55,
          fare: { amount: 45, currency: "INR", status: "SCHEDULED" },
          status: "LIVE",
          source: "IRCTC Realtime API"
        }
      ]
    },
    {
      route_id: "rt_aluva_thrissur_cheapest",
      label: "Cheapest",
      category: "Cheapest",
      duration_minutes: 85,
      fare: {
        amount: 30,
        currency: "INR",
        status: "SCHEDULED"
      },
      transfers: 0,
      walking_minutes: 5,
      status: "SCHEDULED",
      legs: [
        {
          mode: "bus",
          provider: "KSRTC Swift",
          from: "Aluva Bus Stand",
          to: "Thrissur KSRTC Bus Stand",
          departure: "08:30",
          arrival: "09:55",
          duration_minutes: 85,
          fare: { amount: 30, currency: "INR", status: "SCHEDULED" },
          status: "SCHEDULED",
          source: "KSRTC Timetable"
        }
      ]
    },
    {
      route_id: "rt_aluva_thrissur_fewest",
      label: "Fewest Transfers",
      category: "Fewest Transfers",
      duration_minutes: 65,
      fare: {
        amount: 60,
        currency: "INR",
        status: "ESTIMATED"
      },
      transfers: 0,
      walking_minutes: 4,
      status: "ESTIMATED",
      legs: [
        {
          mode: "bus",
          provider: "KSRTC Fast Passenger",
          from: "Aluva Bypass",
          to: "Thrissur Sakthan Stand",
          departure: "08:45",
          arrival: "09:50",
          duration_minutes: 65,
          fare: { amount: 60, currency: "INR", status: "ESTIMATED" },
          status: "ESTIMATED",
          source: "KSRTC Telemetry"
        }
      ]
    }
  ]
};
