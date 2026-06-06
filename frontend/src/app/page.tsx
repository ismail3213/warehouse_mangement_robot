"use client";

import { useEffect, useState, useRef } from "react";
import { 
  Truck, 
  Cpu, 
  Warehouse, 
  History, 
  RefreshCw, 
  Activity, 
  Play, 
  CheckCircle, 
  AlertTriangle, 
  Battery, 
  MapPin, 
  Clock, 
  ShieldAlert, 
  Layers,
  ChevronRight,
  Compass,
  ArrowDownLeft,
  ArrowUpRight,
  Info,
  Sliders,
  Send
} from "lucide-react";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("overview");
  const [state, setState] = useState<any>({
    trucks: [],
    docks: [],
    robots: [],
    zones: [],
    missions: [],
    decision_logs: [],
    incidents: [],
    client_orders: [],
    model_stats: {}
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Client Order Form State
  const [clientName, setClientName] = useState("Auchan Retail");
  const [clientCargo, setClientCargo] = useState("Cold");
  const [clientDestination, setClientDestination] = useState("Route_1");
  const [clientQuantity, setClientQuantity] = useState(10);
  const [clientPriority, setClientPriority] = useState(3);

  // Supplier Single Dispatch Form State
  const [singleSupplier, setSingleSupplier] = useState("DHL Express");
  const [singleCargo, setSingleCargo] = useState("General");
  const [singleDistance, setSingleDistance] = useState(100);
  const [singleTraffic, setSingleTraffic] = useState(0);
  const [singleWeather, setSingleWeather] = useState(0);
  const [singleRisk, setSingleRisk] = useState(0);
  const [singlePriority, setSinglePriority] = useState(3);
  const [singleRoute, setSingleRoute] = useState("Route_2");

  // Supplier Batch Dispatch Form State
  const [supplierName, setSupplierName] = useState("Kuehne + Nagel");
  const [batchTrucks, setBatchTrucks] = useState<any[]>([
    {
      cargo_type: "Cold",
      distance: 90,
      traffic_level: 0,
      weather: 0,
      route_risk: 0,
      driver_fatigue: 0,
      priority: 4,
      origin: "West Port",
      operation_type: "DELIVERY",
      route_id: "Route_2"
    },
    {
      cargo_type: "General",
      distance: 140,
      traffic_level: 1,
      weather: 0,
      route_risk: 0,
      driver_fatigue: 0,
      priority: 2,
      origin: "North Hub",
      operation_type: "PICKUP",
      route_id: "Route_1"
    }
  ]);

  const [simulating, setSimulating] = useState(false);
  const [resetting, setResetting] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  const fetchData = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/state");
      if (!res.ok) throw new Error("Failed to fetch state from backend");
      const data = await res.json();
      setState(data);
      setError(null);
    } catch (err: any) {
      console.error(err);
      setError("Cannot connect to SWOS backend. Make sure the FastAPI server is running on http://localhost:8000");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    const connectWS = () => {
      const ws = new WebSocket("ws://localhost:8000/ws/events");
      socketRef.current = ws;

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.event === "STATE_UPDATE" || msg.event === "GPS_UPDATE") {
          fetchData();
        }
      };

      ws.onclose = () => {
        setTimeout(connectWS, 5000);
      };

      ws.onerror = (err) => {
        ws.close();
      };
    };

    connectWS();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  const handlePlaceClientOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimulating(true);
    try {
      const payload = {
        client_name: clientName,
        cargo_type: clientCargo,
        destination: clientDestination,
        quantity: clientQuantity,
        priority: clientPriority
      };
      
      const res = await fetch("http://localhost:8000/api/client/order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Client order placement failed");
      const result = await res.json();
      await fetchData();
      if (result.status === "PENDING") {
        alert("Client order placed successfully! It has been queued as all company trucks are currently busy.");
      } else {
        alert(`Client order placed! Matched to company truck at Dock ${result.dock_id}.`);
      }
    } catch (err: any) {
      alert("Error placing client order: " + err.message);
    } finally {
      setSimulating(false);
    }
  };

  const handleSingleSupplierDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimulating(true);
    try {
      const payload = {
        supplier: singleSupplier,
        cargo_type: singleCargo,
        distance: singleDistance,
        traffic_level: singleTraffic,
        weather: singleWeather,
        route_risk: singleRisk,
        driver_fatigue: 0,
        priority: singlePriority,
        origin: singleRoute === "Route_1" ? "North Hub" : singleRoute === "Route_2" ? "West Port" : singleRoute === "Route_3" ? "South Depot" : "East Warehouse",
        route_id: singleRoute
      };
      
      const res = await fetch("http://localhost:8000/api/supplier/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Supplier dispatch failed");
      await fetchData();
      alert("Supplier truck successfully dispatched! Estimated ETA calculated using XGBoost.");
    } catch (err: any) {
      alert("Error dispatching supplier truck: " + err.message);
    } finally {
      setSimulating(false);
    }
  };

  const handleDispatchBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimulating(true);
    try {
      const payload = {
        supplier: supplierName,
        trucks: batchTrucks.map(t => ({
          ...t,
          supplier: supplierName
        }))
      };
      
      const res = await fetch("http://localhost:8000/api/simulate/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Batch dispatch simulation failed");
      await fetchData();
      alert("Batch of trucks successfully dispatched! Observe their live movement on the radar.");
    } catch (err: any) {
      alert("Error dispatching batch: " + err.message);
    } finally {
      setSimulating(false);
    }
  };

  const handleToggleIncident = async (routeId: string, type: string, delay: number, currentlyActive: boolean) => {
    try {
      const res = await fetch("http://localhost:8000/api/incidents/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          route_id: routeId,
          incident_type: type,
          delay_minutes: delay,
          active: !currentlyActive
        })
      });
      if (!res.ok) throw new Error("Failed to toggle incident");
      await fetchData();
    } catch (err: any) {
      alert("Error toggling road incident: " + err.message);
    }
  };

  const handleCompleteMission = async (missionId: number) => {
    try {
      const res = await fetch(`http://localhost:8000/api/missions/${missionId}/complete`, {
        method: "POST"
      });
      if (!res.ok) throw new Error("Failed to complete mission");
      await fetchData();
    } catch (err: any) {
      alert("Error completing mission: " + err.message);
    }
  };

  const handleResetSimulation = async () => {
    if (!confirm("Are you sure you want to reset the simulation? All trucks, missions, and logs will be cleared.")) return;
    setResetting(true);
    try {
      const res = await fetch("http://localhost:8000/api/simulate/reset", {
        method: "POST"
      });
      if (!res.ok) throw new Error("Reset request failed");
      await fetchData();
    } catch (err: any) {
      alert("Error resetting simulation: " + err.message);
    } finally {
      setResetting(false);
    }
  };

  const addTruckToBatchForm = () => {
    const defaultRoutes = ["Route_1", "Route_2", "Route_3", "Route_4"];
    const routeOrigins: any = { "Route_1": "North Hub", "Route_2": "West Port", "Route_3": "South Depot", "Route_4": "East Warehouse" };
    const nextRoute = defaultRoutes[(batchTrucks.length) % 4];
    setBatchTrucks([
      ...batchTrucks,
      {
        cargo_type: "General",
        distance: 100,
        traffic_level: 0,
        weather: 0,
        route_risk: 0,
        driver_fatigue: 0,
        priority: 3,
        origin: routeOrigins[nextRoute],
        operation_type: "DELIVERY",
        route_id: nextRoute
      }
    ]);
  };

  const removeTruckFromBatchForm = (index: number) => {
    if (batchTrucks.length <= 1) return;
    setBatchTrucks(batchTrucks.filter((_, i) => i !== index));
  };

  const updateBatchTruckField = (index: number, field: string, value: any) => {
    const updated = [...batchTrucks];
    updated[index][field] = value;
    
    // Auto-update origin based on route
    if (field === "route_id") {
      const routeOrigins: any = { "Route_1": "North Hub", "Route_2": "West Port", "Route_3": "South Depot", "Route_4": "East Warehouse" };
      updated[index]["origin"] = routeOrigins[value];
    }
    setBatchTrucks(updated);
  };

  // Helper selectors
  const activeMissions = state.missions.filter((m: any) => m.status === "RUNNING");
  const inTransitTrucks = state.trucks.filter((t: any) => 
    (t.is_company_truck === false && t.status === "PENDING" && t.gps_progress < 1.0) ||
    (t.is_company_truck === true && (t.company_truck_status === "EN_ROUTE_TO_CLIENT" || t.company_truck_status === "EN_ROUTE_TO_WAREHOUSE") && t.gps_progress < 1.0)
  );
  const mapTrucks = state.trucks.filter((t: any) => 
    t.is_company_truck === true && 
    (t.company_truck_status === "EN_ROUTE_TO_CLIENT" || t.company_truck_status === "EN_ROUTE_TO_WAREHOUSE")
  );
  const arrivedTrucks = state.trucks.filter((t: any) => t.status === "ARRIVED" || t.status === "PROCESSING" || t.company_truck_status === "LOADING");
  const queuedTrucks = state.trucks.filter((t: any) => t.status === "QUEUED" || t.company_truck_status === "QUEUED");
  
  // Incident status check helper
  const isIncidentActive = (routeId: string, type: string) => {
    const inc = state.incidents.find((i: any) => i.route_id === routeId && i.incident_type === type);
    return inc ? inc.active : false;
  };

  // Coordinates helper for SVG GPS Map rendering (viewBox 400x400)
  // Center is Warehouse (200, 200)
  const getTruckCoordinates = (routeId: string, progress: number, status?: string, companyStatus?: string) => {
    const p = progress || 0.0;
    // Outbound company status: moving FROM Warehouse (progress 0) TO Hub (progress 1)
    const isOutbound = companyStatus === "EN_ROUTE_TO_CLIENT";
    const effP = isOutbound ? (1.0 - p) : p; // 0% progress outbound is at Warehouse (effP = 1), 100% is at Hub (effP = 0)
    
    switch (routeId) {
      case "Route_1": // North Hub (200, 40) -> Warehouse (200, 200)
        return { x: 200, y: 40 + (200 - 40) * effP };
      case "Route_2": // West Port (40, 200) -> Warehouse (200, 200)
        return { x: 40 + (200 - 40) * effP, y: 200 };
      case "Route_3": // South Depot (200, 360) -> Warehouse (200, 200)
        return { x: 200, y: 360 - (360 - 200) * effP };
      case "Route_4": // East Warehouse (360, 200) -> Warehouse (200, 200)
        return { x: 360 - (360 - 200) * effP, y: 200 };
      default:
        return { x: 200, y: 200 };
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/50 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Compass className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-indigo-400 bg-clip-text text-transparent">
                WareMind
              </h1>
              <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">
                Multi-Agent Logistics Center
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {error && (
              <div className="flex items-center space-x-2 bg-red-950/60 border border-red-800 rounded-lg px-3 py-1.5 text-xs">
                <span className="h-2.5 w-2.5 rounded-full bg-red-500 animate-pulse"></span>
                <span className="text-red-300 font-medium">Offline</span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Layout Container */}
      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col md:flex-row gap-6">
        {/* Navigation Sidebar */}
        <aside className="w-full md:w-64 flex flex-col space-y-1">
          <button
            onClick={() => setActiveTab("overview")}
            className={`flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${
              activeTab === "overview"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/15"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            <Activity className="h-5 w-5" />
            <span>Overview & Radar</span>
          </button>
          <button
            onClick={() => setActiveTab("dispatch")}
            className={`flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${
              activeTab === "dispatch"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/15"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            <Send className="h-5 w-5" />
            <span>Supplier Dispatch Portal</span>
          </button>
          <button
            onClick={() => setActiveTab("trucks")}
            className={`flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${
              activeTab === "trucks"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/15"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            <Truck className="h-5 w-5" />
            <span>Camions ({state.trucks.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("robots")}
            className={`flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${
              activeTab === "robots"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/15"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            <Cpu className="h-5 w-5" />
            <span>Robots ({state.robots.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("storage")}
            className={`flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${
              activeTab === "storage"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/15"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            <Warehouse className="h-5 w-5" />
            <span>Stockage & Quais</span>
          </button>
          <button
            onClick={() => setActiveTab("logs")}
            className={`flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${
              activeTab === "logs"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/15"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            <History className="h-5 w-5" />
            <span>Logs & Décisions IA</span>
          </button>

          {/* Incident Alert Panel in sidebar */}
          <div className="mt-8 p-4 bg-slate-900/40 rounded-2xl border border-slate-800/80">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              <span>Route Incidents</span>
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between items-center bg-slate-950/60 p-2 rounded border border-slate-800">
                <span className="text-slate-300">Route 1 (North)</span>
                <button 
                  onClick={() => handleToggleIncident("Route_1", "CONGESTION", 30, isIncidentActive("Route_1", "CONGESTION"))}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${
                    isIncidentActive("Route_1", "CONGESTION") 
                      ? "bg-red-500/20 text-red-400 border border-red-500/30" 
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                  }`}
                >
                  {isIncidentActive("Route_1", "CONGESTION") ? "Traffic +30m" : "Normal"}
                </button>
              </div>

              <div className="flex justify-between items-center bg-slate-950/60 p-2 rounded border border-slate-800">
                <span className="text-slate-300">Route 2 (West)</span>
                <button 
                  onClick={() => handleToggleIncident("Route_2", "ACCIDENT", 60, isIncidentActive("Route_2", "ACCIDENT"))}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${
                    isIncidentActive("Route_2", "ACCIDENT") 
                      ? "bg-red-500/20 text-red-400 border border-red-500/30" 
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                  }`}
                >
                  {isIncidentActive("Route_2", "ACCIDENT") ? "Accident +60m" : "Normal"}
                </button>
              </div>

              <div className="flex justify-between items-center bg-slate-950/60 p-2 rounded border border-slate-800">
                <span className="text-slate-300">Route 3 (South)</span>
                <button 
                  onClick={() => handleToggleIncident("Route_3", "STORM", 45, isIncidentActive("Route_3", "STORM"))}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${
                    isIncidentActive("Route_3", "STORM") 
                      ? "bg-red-500/20 text-red-400 border border-red-500/30" 
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                  }`}
                >
                  {isIncidentActive("Route_3", "STORM") ? "Storm +45m" : "Normal"}
                </button>
              </div>

              <div className="flex justify-between items-center bg-slate-950/60 p-2 rounded border border-slate-800">
                <span className="text-slate-300">Route 4 (East)</span>
                <button 
                  onClick={() => handleToggleIncident("Route_4", "CONGESTION", 20, isIncidentActive("Route_4", "CONGESTION"))}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${
                    isIncidentActive("Route_4", "CONGESTION") 
                      ? "bg-red-500/20 text-red-400 border border-red-500/30" 
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                  }`}
                >
                  {isIncidentActive("Route_4", "CONGESTION") ? "Traffic +20m" : "Normal"}
                </button>
              </div>
            </div>
          </div>
        </aside>

        {/* Content Area */}
        <main className="flex-1 bg-slate-900/20 rounded-3xl border border-slate-850/80 p-6 min-h-[500px]">
          {error && (
            <div className="mb-6 p-4 bg-red-950/20 border border-red-500/20 rounded-2xl flex items-start space-x-3 text-red-300">
              <ShieldAlert className="h-6 w-6 shrink-0 text-red-400" />
              <div>
                <h4 className="font-bold text-sm">Connection Refused</h4>
                <p className="text-xs text-red-400/90 mt-1">{error}</p>
              </div>
            </div>
          )}

          {loading ? (
            <div className="h-full flex items-center justify-center flex-col py-20 space-y-4">
              <div className="relative">
                <div className="h-12 w-12 rounded-full border-t-2 border-r-2 border-indigo-500 animate-spin"></div>
                <Compass className="h-6 w-6 text-indigo-400 absolute top-3 left-3 animate-pulse" />
              </div>
              <span className="text-sm text-slate-400">Synchronisation des flux radar...</span>
            </div>
          ) : (
            <>
              {/* Tab 1: Overview & GPS Map */}
              {activeTab === "overview" && (
                <div className="space-y-6">
                  {/* Stats Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between">
                      <div className="flex justify-between items-start">
                        <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">In Transit</span>
                        <div className="h-7 w-7 rounded-lg bg-sky-500/10 flex items-center justify-center text-sky-400">
                          <Compass className="h-4 w-4" />
                        </div>
                      </div>
                      <div className="mt-2">
                        <span className="text-2xl font-extrabold text-white">{inTransitTrucks.length}</span>
                        <span className="text-[10px] text-slate-400 block mt-0.5">Trucks moving on route</span>
                      </div>
                    </div>

                    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between">
                      <div className="flex justify-between items-start">
                        <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">Arrived Docks</span>
                        <div className="h-7 w-7 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                          <Warehouse className="h-4 w-4" />
                        </div>
                      </div>
                      <div className="mt-2">
                        <span className="text-2xl font-extrabold text-white">
                          {state.docks.filter((d: any) => d.status === "OCCUPIED").length}/{state.docks.length}
                        </span>
                        <span className="text-[10px] text-slate-400 block mt-0.5">Docks currently occupied</span>
                      </div>
                    </div>

                    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between">
                      <div className="flex justify-between items-start">
                        <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">Missions</span>
                        <div className="h-7 w-7 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                          <Activity className="h-4 w-4" />
                        </div>
                      </div>
                      <div className="mt-2">
                        <span className="text-2xl font-extrabold text-white">{activeMissions.length}</span>
                        <span className="text-[10px] text-slate-400 block mt-0.5">Active robot transport jobs</span>
                      </div>
                    </div>

                    <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between">
                      <div className="flex justify-between items-start">
                        <span className="text-slate-400 text-xs font-bold uppercase tracking-wider">Operations Queued</span>
                        <div className="h-7 w-7 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400">
                          <Layers className="h-4 w-4" />
                        </div>
                      </div>
                      <div className="mt-2">
                        <span className="text-2xl font-extrabold text-white">{queuedTrucks.length}</span>
                        <span className="text-[10px] text-slate-400 block mt-0.5">Trucks in queue for docks</span>
                      </div>
                    </div>
                  </div>

                  {/* Main Overview Grid: Map + Side Panel */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* SVG Interactive Transit Radar Map */}
                    <div className="lg:col-span-2 bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5 flex flex-col items-center justify-center">
                      <div className="w-full flex justify-between items-center mb-3">
                        <h3 className="font-bold text-sm text-slate-200 flex items-center space-x-2">
                          <span className="h-2.5 w-2.5 rounded-full bg-indigo-500 animate-pulse"></span>
                          <span>Radar de Transit Logistique (Temps Réel)</span>
                        </h3>
                        <span className="text-[10px] text-slate-400 bg-slate-950 border border-slate-800 px-2 py-1 rounded">
                          Central Warehouse (Scale 1:1)
                        </span>
                      </div>

                      {/* SVG Map Frame */}
                      <div className="relative w-full max-w-[400px] aspect-square bg-slate-950/80 rounded-xl border border-slate-850 p-2 flex items-center justify-center">
                        <style>{`
                          @keyframes radar-sweep {
                            from { transform: rotate(0deg); }
                            to { transform: rotate(360deg); }
                          }
                          .radar-sweep-line {
                            transform-origin: 200px 200px;
                            animation: radar-sweep 10s linear infinite;
                          }
                          @keyframes pulse-ring {
                            0% { transform: scale(0.95); opacity: 1; }
                            50% { transform: scale(1.1); opacity: 0.5; }
                            100% { transform: scale(0.95); opacity: 1; }
                          }
                          .warehouse-pulse {
                            animation: pulse-ring 3s cubic-bezier(0.4, 0, 0.6, 1) infinite;
                          }
                        `}</style>
                        <svg className="w-full h-full" viewBox="0 0 400 400" fill="none" xmlns="http://www.w3.org/2000/svg">
                          {/* Glow definitions */}
                          <defs>
                            <linearGradient id="warehouseGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                              <stop offset="0%" stopColor="#4f46e5" />
                              <stop offset="100%" stopColor="#7c3aed" />
                            </linearGradient>
                            <linearGradient id="sweepGrad" x1="200" y1="200" x2="200" y2="40">
                              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.3" />
                              <stop offset="50%" stopColor="#6366f1" stopOpacity="0.1" />
                              <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
                            </linearGradient>
                            <filter id="glow-purple" x="-30%" y="-30%" width="160%" height="160%">
                              <feGaussianBlur stdDeviation="3" result="blur" />
                              <feMerge>
                                <feMergeNode in="blur" />
                                <feMergeNode in="SourceGraphic" />
                              </feMerge>
                            </filter>
                            <filter id="glow-cyan" x="-30%" y="-30%" width="160%" height="160%">
                              <feGaussianBlur stdDeviation="3" result="blur" />
                              <feMerge>
                                <feMergeNode in="blur" />
                                <feMergeNode in="SourceGraphic" />
                              </feMerge>
                            </filter>
                            <filter id="glow-red" x="-30%" y="-30%" width="160%" height="160%">
                              <feGaussianBlur stdDeviation="4" result="blur" />
                              <feMerge>
                                <feMergeNode in="blur" />
                                <feMergeNode in="SourceGraphic" />
                              </feMerge>
                            </filter>
                          </defs>

                          {/* High-tech Matrix Dot Grid (Replaces compass circles) */}
                          <g stroke="#1e293b" strokeWidth="1.5" strokeDasharray="1,19" strokeLinecap="round">
                            {/* Vertical lines */}
                            <line x1="40" y1="0" x2="40" y2="400" />
                            <line x1="80" y1="0" x2="80" y2="400" />
                            <line x1="120" y1="0" x2="120" y2="400" />
                            <line x1="160" y1="0" x2="160" y2="400" />
                            <line x1="200" y1="0" x2="200" y2="400" />
                            <line x1="240" y1="0" x2="240" y2="400" />
                            <line x1="280" y1="0" x2="280" y2="400" />
                            <line x1="320" y1="0" x2="320" y2="400" />
                            <line x1="360" y1="0" x2="360" y2="400" />
                            {/* Horizontal lines */}
                            <line x1="0" y1="40" x2="400" y2="40" />
                            <line x1="0" y1="80" x2="400" y2="80" />
                            <line x1="0" y1="120" x2="400" y2="120" />
                            <line x1="0" y1="160" x2="400" y2="160" />
                            <line x1="0" y1="200" x2="400" y2="200" />
                            <line x1="0" y1="240" x2="400" y2="240" />
                            <line x1="0" y1="280" x2="400" y2="280" />
                            <line x1="0" y1="320" x2="400" y2="320" />
                            <line x1="0" y1="360" x2="400" y2="360" />
                          </g>

                          {/* Rotating Radar Sweep Line */}
                          <line x1="200" y1="200" x2="200" y2="40" stroke="url(#sweepGrad)" strokeWidth="3.5" className="radar-sweep-line" />

                          {/* Highway routes (Double roads) */}
                          {/* Route 1: North Hub (Vertical) */}
                          <rect x="193" y="40" width="14" height="160" fill="#1e293b" stroke="#334155" strokeWidth="1" rx="4" />
                          <line x1="200" y1="40" x2="200" y2="200" 
                            stroke={isIncidentActive("Route_1", "CONGESTION") ? "#ef4444" : "#6366f1"} 
                            strokeWidth="1.5" strokeLinecap="round" strokeDasharray="5,5"
                            filter={isIncidentActive("Route_1", "CONGESTION") ? "url(#glow-red)" : ""}
                          />

                          {/* Route 2: West Port (Horizontal) */}
                          <rect x="40" y="193" width="160" height="14" fill="#1e293b" stroke="#334155" strokeWidth="1" rx="4" />
                          <line x1="40" y1="200" x2="200" y2="200" 
                            stroke={isIncidentActive("Route_2", "ACCIDENT") ? "#ef4444" : "#6366f1"} 
                            strokeWidth="1.5" strokeLinecap="round" strokeDasharray="5,5"
                            filter={isIncidentActive("Route_2", "ACCIDENT") ? "url(#glow-red)" : ""}
                          />

                          {/* Route 3: South Depot (Vertical) */}
                          <rect x="193" y="200" width="14" height="160" fill="#1e293b" stroke="#334155" strokeWidth="1" rx="4" />
                          <line x1="200" y1="200" x2="200" y2="360" 
                            stroke={isIncidentActive("Route_3", "STORM") ? "#ef4444" : "#6366f1"} 
                            strokeWidth="1.5" strokeLinecap="round" strokeDasharray="5,5"
                            filter={isIncidentActive("Route_3", "STORM") ? "url(#glow-red)" : ""}
                          />

                          {/* Route 4: East Warehouse (Horizontal) */}
                          <rect x="200" y="193" width="160" height="14" fill="#1e293b" stroke="#334155" strokeWidth="1" rx="4" />
                          <line x1="200" y1="200" x2="360" y2="200" 
                            stroke={isIncidentActive("Route_4", "CONGESTION") ? "#ef4444" : "#6366f1"} 
                            strokeWidth="1.5" strokeLinecap="round" strokeDasharray="5,5"
                            filter={isIncidentActive("Route_4", "CONGESTION") ? "url(#glow-red)" : ""}
                          />

                          {/* Route label nodes with background cards */}
                          <g transform="translate(200, 26)">
                            <rect x="-40" y="-8" width="80" height="16" rx="4" fill="#0f172a" stroke="#4f46e5" strokeWidth="1" />
                            <text x="0" y="3" fill="#cbd5e1" fontSize="9" fontWeight="extrabold" textAnchor="middle">NORTH HUB</text>
                          </g>

                          <g transform="translate(40, 175)">
                            <rect x="-40" y="-8" width="80" height="16" rx="4" fill="#0f172a" stroke="#4f46e5" strokeWidth="1" />
                            <text x="0" y="3" fill="#cbd5e1" fontSize="9" fontWeight="extrabold" textAnchor="middle">WEST PORT</text>
                          </g>

                          <g transform="translate(200, 378)">
                            <rect x="-40" y="-8" width="80" height="16" rx="4" fill="#0f172a" stroke="#4f46e5" strokeWidth="1" />
                            <text x="0" y="3" fill="#cbd5e1" fontSize="9" fontWeight="extrabold" textAnchor="middle">SOUTH DEPOT</text>
                          </g>

                          <g transform="translate(360, 175)">
                            <rect x="-45" y="-8" width="90" height="16" rx="4" fill="#0f172a" stroke="#4f46e5" strokeWidth="1" />
                            <text x="0" y="3" fill="#cbd5e1" fontSize="9" fontWeight="extrabold" textAnchor="middle">EAST WAREHOUSE</text>
                          </g>

                          {/* Active Incident Warning Pulsing nodes */}
                          {isIncidentActive("Route_1", "CONGESTION") && (
                            <g transform="translate(200, 110)">
                              <circle cx="0" cy="0" r="10" fill="#ef4444" opacity="0.3" className="animate-ping" />
                              <circle cx="0" cy="0" r="6" fill="#ef4444" />
                              <text x="0" y="2" fill="#fff" fontSize="7" textAnchor="middle" fontWeight="bold">⚠️</text>
                            </g>
                          )}
                          {isIncidentActive("Route_2", "ACCIDENT") && (
                            <g transform="translate(110, 200)">
                              <circle cx="0" cy="0" r="10" fill="#ef4444" opacity="0.3" className="animate-ping" />
                              <circle cx="0" cy="0" r="6" fill="#ef4444" />
                              <text x="0" y="2" fill="#fff" fontSize="7" textAnchor="middle" fontWeight="bold">⚠️</text>
                            </g>
                          )}
                          {isIncidentActive("Route_3", "STORM") && (
                            <g transform="translate(200, 290)">
                              <circle cx="0" cy="0" r="10" fill="#ef4444" opacity="0.3" className="animate-ping" />
                              <circle cx="0" cy="0" r="6" fill="#ef4444" />
                              <text x="0" y="2" fill="#fff" fontSize="7" textAnchor="middle" fontWeight="bold">⚠️</text>
                            </g>
                          )}
                          {isIncidentActive("Route_4", "CONGESTION") && (
                            <g transform="translate(290, 200)">
                              <circle cx="0" cy="0" r="10" fill="#ef4444" opacity="0.3" className="animate-ping" />
                              <circle cx="0" cy="0" r="6" fill="#ef4444" />
                              <text x="0" y="2" fill="#fff" fontSize="7" textAnchor="middle" fontWeight="bold">⚠️</text>
                            </g>
                          )}

                          {/* Central SWOS Warehouse Node */}
                          <g transform="translate(200, 200)">
                            <circle cx="0" cy="0" r="24" fill="#6366f1" opacity="0.15" className="warehouse-pulse" />
                            <rect x="-18" y="-18" width="36" height="36" rx="8" fill="url(#warehouseGrad)" stroke="#818cf8" strokeWidth="2" />
                            <Warehouse className="h-5 w-5 text-white" style={{ transform: "translate(-10px, -10px)" }} />
                          </g>

                          {/* Moving Trucks Circles with Large Legible Labels */}
                          {mapTrucks.map((truck: any) => {
                            const { x, y } = getTruckCoordinates(truck.route_id, truck.gps_progress, truck.status, truck.company_truck_status);
                            const activeInc = state.incidents.find((inc: any) => inc.route_id === truck.route_id && inc.active === true);
                            const isOutbound = truck.company_truck_status === "EN_ROUTE_TO_CLIENT";
                            
                            // Determine pointer angle
                            let angle = 0;
                            if (truck.route_id === "Route_1") angle = isOutbound ? 180 : 0;
                            if (truck.route_id === "Route_2") angle = isOutbound ? 270 : 90;
                            if (truck.route_id === "Route_3") angle = isOutbound ? 0 : 180;
                            if (truck.route_id === "Route_4") angle = isOutbound ? 90 : 270;

                            const themeColor = activeInc ? "#f97316" : isOutbound ? "#c084fc" : "#22d3ee";
                            const glowFilter = isOutbound ? "url(#glow-purple)" : "url(#glow-cyan)" ;
                            const labelLeft = x > 200;

                            return (
                              <g key={truck.truck_id} transform={`translate(${x}, ${y})`} className="cursor-pointer">
                                {/* Small Direction Pointer */}
                                <polygon points="0,-16 -5,-11 5,-11" fill={themeColor} transform={`rotate(${angle})`} />
                                
                                {/* Base Truck Circle */}
                                <circle cx="0" cy="0" r="11" fill={themeColor} stroke="#0f172a" strokeWidth="2.5" filter={glowFilter} />
                                <Truck className="h-3.5 w-3.5 text-slate-950" style={{ transform: "translate(-7px, -7px)" }} />
                                
                                {/* High-contrast Legible Label Card popup */}
                                <g transform={`translate(${labelLeft ? -125 : 15}, -18)`}>
                                  <rect x="0" y="0" width="110" height="36" rx="6" fill="#0b0f19" stroke={themeColor} strokeWidth="1.5" opacity="0.95" />
                                  <text x="8" y="15" fill="#ffffff" fontSize="9" fontWeight="bold">{truck.supplier}</text>
                                  <text x="8" y="28" fill={themeColor} fontSize="8" fontWeight="semibold">
                                    {isOutbound ? "Outbound" : "Inbound"} {(truck.gps_progress * 100).toFixed(0)}%
                                  </text>
                                </g>
                              </g>
                            );
                          })}
                        </svg>
                      </div>
                      
                      {/* Map Legend */}
                      <div className="w-full mt-4 bg-slate-950/60 border border-slate-850 rounded-xl p-3 flex flex-wrap justify-center items-center gap-6 text-[10px] text-slate-400">
                        <div className="flex items-center space-x-2">
                          <span className="h-2.5 w-2.5 rounded-full bg-purple-500 shadow-[0_0_8px_#a855f7]"></span>
                          <span>Camion en Livraison (Aller)</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="h-2.5 w-2.5 rounded-full bg-cyan-500 shadow-[0_0_8px_#06b6d4]"></span>
                          <span>Camion en Retour (Vide)</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="flex space-x-0.5">
                            <span className="h-1 w-2 bg-indigo-500"></span>
                            <span className="h-1 w-2 bg-indigo-500"></span>
                          </div>
                          <span>Route Normale</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="flex space-x-0.5">
                            <span className="h-1 w-2 bg-red-500"></span>
                            <span className="h-1 w-2 bg-red-500"></span>
                          </div>
                          <span>Route Congestionnée / Incidentée</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="text-red-500">⚠️</span>
                          <span>Zone d'incident</span>
                        </div>
                      </div>
                    </div>

                    {/* Active Missions List & Queue Column */}
                    <div className="lg:col-span-1 flex flex-col space-y-6">
                      <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5 flex-1 flex flex-col">
                        <h3 className="font-bold text-sm text-slate-200 mb-4 flex items-center justify-between">
                          <span>Active Transport Missions</span>
                          <span className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded font-bold">
                            Live AGV
                          </span>
                        </h3>
                        {activeMissions.length === 0 ? (
                          <div className="flex-1 flex flex-col items-center justify-center py-10 border border-dashed border-slate-800 rounded-xl">
                            <Layers className="h-8 w-8 text-slate-600 mb-2" />
                            <span className="text-xs text-slate-500 text-center">
                              No active robot transport missions.<br />Dispatched trucks will trigger missions upon arrival.
                            </span>
                          </div>
                        ) : (
                          <div className="space-y-3 max-h-[320px] overflow-y-auto pr-1">
                            {activeMissions.map((m: any) => {
                              // Find corresponding truck operation
                              const robot = state.robots.find((r: any) => r.robot_id === m.robot_id);
                              // We see if it is pickup or delivery based on zone matching
                              const isPickup = m.source_zone > 4; // Storage Zones are IDs 1-5, docks map to 1-4.
                              // Actually in our logic: dock zone is 1-4. Storage zone is z_id.
                              // So if source is Storage, it's a PICKUP! (e.g. source > 4 or source zone doesn't map to dock).
                              // We set operation_type in schema mission completed callback or we can check source.
                              return (
                                <div key={m.mission_id} className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
                                  <div className="space-y-1">
                                    <div className="flex items-center space-x-2">
                                      <span className="text-xs font-bold text-slate-200">Mission #{m.mission_id}</span>
                                      <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded ${
                                        isPickup ? 'bg-amber-500/10 text-amber-400' : 'bg-cyan-500/10 text-cyan-400'
                                      }`}>
                                        {isPickup ? 'PICKUP' : 'DELIVERY'}
                                      </span>
                                    </div>
                                    <div className="text-xs text-slate-400 flex items-center space-x-1.5">
                                      <span>Zone {m.source_zone}</span>
                                      <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
                                      <span className="text-slate-300">Zone {m.destination_zone}</span>
                                    </div>
                                    <div className="text-[10px] text-slate-500 flex items-center space-x-1">
                                      <Cpu className="h-3 w-3 text-indigo-400" />
                                      <span>AGV R{m.robot_id} ({robot?.battery}% battery)</span>
                                    </div>
                                  </div>
                                  <button
                                    onClick={() => handleCompleteMission(m.mission_id)}
                                    className="flex items-center space-x-1 py-1 px-2.5 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/25 rounded-lg text-xs font-semibold text-emerald-400 transition"
                                  >
                                    <span>Finish</span>
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      {/* NEW: Planning d'Arrivée (ETA Queue) */}
                      <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5 flex flex-col max-h-[400px]">
                        <h3 className="font-bold text-sm text-slate-200 mb-4 flex items-center justify-between">
                          <span>Planning d'Arrivée (ETA Queue)</span>
                          <span className="text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded font-bold">
                            Live JIT
                          </span>
                        </h3>
                        {inTransitTrucks.length === 0 ? (
                           <div className="flex-1 flex flex-col items-center justify-center py-6 border border-dashed border-slate-800 rounded-xl">
                            <span className="text-xs text-slate-500 text-center">Aucun camion en approche.</span>
                           </div>
                        ) : (
                          <div className="space-y-3 overflow-y-auto pr-1">
                            {[...inTransitTrucks].sort((a: any, b: any) => new Date(a.eta).getTime() - new Date(b.eta).getTime()).map((t: any, idx: number) => {
                               const etaStr = new Date(t.eta).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
                               const isCompany = t.is_company_truck;
                               return (
                                 <div key={t.truck_id} className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 flex items-center justify-between">
                                   <div className="flex items-center space-x-3">
                                     <div className={`h-6 w-6 rounded flex items-center justify-center font-bold text-xs ${idx === 0 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'}`}>{idx + 1}</div>
                                     <div>
                                       <div className="text-xs font-bold text-slate-200">{t.supplier}</div>
                                       <div className="text-[10px] text-slate-400">{isCompany ? 'Flotte Propre' : 'Fournisseur'} • {t.route_id}</div>
                                     </div>
                                   </div>
                                   <div className="text-right">
                                     <div className="text-xs font-bold text-indigo-400">{etaStr}</div>
                                     <div className="text-[10px] text-slate-500">ETA</div>
                                   </div>
                                 </div>
                               );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Separate section for live logistics tables */}
                  <div className="mt-8 grid grid-cols-1 xl:grid-cols-2 gap-6">
                    {/* Table 1: Company Fleet Status */}
                    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5">
                      <h3 className="font-bold text-sm text-slate-200 mb-4 flex items-center justify-between">
                        <span className="flex items-center space-x-2">
                          <span className="h-2.5 w-2.5 rounded-full bg-cyan-500 animate-pulse"></span>
                          <span>Flotte Propre de l'Entreprise (Radar Actif)</span>
                        </span>
                        <span className="text-[10px] text-slate-400 bg-slate-950 border border-slate-800 px-2 py-0.5 rounded font-bold">
                          {state.trucks.filter((t: any) => t.is_company_truck === true).length} AGENTS
                        </span>
                      </h3>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-850 text-xs">
                          <thead>
                            <tr className="text-slate-400 font-bold uppercase tracking-wider text-[10px] bg-slate-950/40">
                              <th className="px-4 py-2 text-left">Camion</th>
                              <th className="px-4 py-2 text-left">Status</th>
                              <th className="px-4 py-2 text-left">Location / Route</th>
                              <th className="px-4 py-2 text-left">Dist. Entrepôt</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-850">
                            {state.trucks.filter((t: any) => t.is_company_truck === true).map((truck: any) => {
                              const isIdle = truck.company_truck_status === "IDLE";
                              const isOutbound = truck.company_truck_status === "EN_ROUTE_TO_CLIENT";
                              const isLoading = truck.company_truck_status === "LOADING";
                              
                              const remDist = isIdle ? "0.0 miles" : ((truck.distance || 100) * (1.0 - truck.gps_progress)).toFixed(1) + " miles";
                              
                              return (
                                <tr key={truck.truck_id} className="hover:bg-slate-900/20 transition">
                                  <td className="px-4 py-3 font-semibold text-slate-200">{truck.supplier}</td>
                                  <td className="px-4 py-3">
                                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                                      isIdle ? "bg-slate-800 text-slate-400 border border-slate-700" :
                                      isLoading ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                                      isOutbound ? "bg-purple-500/10 text-purple-400 border border-purple-500/20" :
                                      "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                                    }`}>
                                      {truck.company_truck_status}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-slate-300">
                                    {isIdle ? "Parked (Warehouse)" : `${truck.route_id} (${isOutbound ? "Outbound" : "Inbound"})`}
                                  </td>
                                  <td className="px-4 py-3 font-mono font-bold text-slate-300">
                                    {remDist}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Table 2: Supplier Transit Estimates */}
                    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-5">
                      <h3 className="font-bold text-sm text-slate-200 mb-4 flex items-center justify-between">
                        <span className="flex items-center space-x-2">
                          <span className="h-2.5 w-2.5 rounded-full bg-slate-500"></span>
                          <span>Livraisons Fournisseurs Attendues (Estimations API)</span>
                        </span>
                        <span className="text-[10px] text-slate-400 bg-slate-950 border border-slate-800 px-2 py-0.5 rounded font-bold">
                          {inTransitTrucks.length} EN ROUTE
                        </span>
                      </h3>
                      <div className="overflow-x-auto max-h-[180px] overflow-y-auto pr-1">
                        <table className="min-w-full divide-y divide-slate-850 text-xs">
                          <thead>
                            <tr className="text-slate-400 font-bold uppercase tracking-wider text-[10px] bg-slate-950/40">
                              <th className="px-4 py-2 text-left">Fournisseur</th>
                              <th className="px-4 py-2 text-left">Cargo</th>
                              <th className="px-4 py-2 text-left">ETA Estimé</th>
                              <th className="px-4 py-2 text-left">Progress</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-850">
                            {inTransitTrucks.length === 0 ? (
                              <tr>
                                <td colSpan={4} className="px-4 py-8 text-center text-slate-500 italic">
                                  No supplier trucks currently en route. Use Simulator tab to dispatch.
                                </td>
                              </tr>
                            ) : (
                              inTransitTrucks.map((truck: any) => {
                                const remDist = ((truck.distance || 100) * (1.0 - truck.gps_progress)).toFixed(1) + " miles";
                                return (
                                  <tr key={truck.truck_id} className="hover:bg-slate-900/20 transition">
                                    <td className="px-4 py-3 font-semibold text-slate-200">{truck.supplier}</td>
                                    <td className="px-4 py-3 text-slate-300">{truck.cargo_type}</td>
                                    <td className="px-4 py-3 text-indigo-400 font-semibold">{new Date(truck.eta).toLocaleTimeString()}</td>
                                    <td className="px-4 py-3 font-mono">
                                      {(truck.gps_progress * 100).toFixed(0)}% ({remDist})
                                    </td>
                                  </tr>
                                );
                              })
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>

                  {/* Table 3: Latest Client Orders */}
                  <div className="mt-6 bg-slate-900/40 border border-slate-800 rounded-2xl p-5">
                    <h3 className="font-bold text-sm text-slate-200 mb-4 flex items-center justify-between">
                      <span className="flex items-center space-x-2">
                        <span className="h-2.5 w-2.5 rounded-full bg-indigo-500 animate-pulse"></span>
                        <span>Dernières Commandes Clients (Simulator Flow)</span>
                      </span>
                      <span className="text-[10px] text-slate-400 bg-slate-950 border border-slate-800 px-2 py-0.5 rounded font-bold">
                        {state.client_orders?.length || 0} TOTAL
                      </span>
                    </h3>
                    <div className="overflow-x-auto max-h-[200px] overflow-y-auto pr-1">
                      <table className="min-w-full divide-y divide-slate-850 text-xs">
                        <thead>
                          <tr className="text-slate-400 font-bold uppercase tracking-wider text-[10px] bg-slate-950/40">
                            <th className="px-4 py-2 text-left">ID Commande</th>
                            <th className="px-4 py-2 text-left">Client</th>
                            <th className="px-4 py-2 text-left">Cargo</th>
                            <th className="px-4 py-2 text-left">Destination</th>
                            <th className="px-4 py-2 text-left">Status</th>
                            <th className="px-4 py-2 text-left">Camion Affecté</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-850">
                          {!state.client_orders || state.client_orders.length === 0 ? (
                            <tr>
                              <td colSpan={6} className="px-4 py-8 text-center text-slate-500 italic">
                                Aucune commande client. Utilisez l'onglet API Simulator pour passer des commandes.
                              </td>
                            </tr>
                          ) : (
                            state.client_orders.map((o: any) => {
                              const assignedTruck = state.trucks.find((t: any) => t.truck_id === o.assigned_truck_id);
                              return (
                                <tr key={o.order_id} className="hover:bg-slate-900/20 transition">
                                  <td className="px-4 py-3 font-mono font-bold text-indigo-400">#{o.order_id}</td>
                                  <td className="px-4 py-3 font-semibold text-slate-200">{o.client_name}</td>
                                  <td className="px-4 py-3 text-slate-300">{o.cargo_type} (x{o.quantity})</td>
                                  <td className="px-4 py-3 text-slate-300">{o.destination}</td>
                                  <td className="px-4 py-3">
                                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                                      o.status === "PENDING" ? "bg-slate-800 text-slate-400 border border-slate-700" :
                                      o.status === "LOADING" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                                      o.status === "EN_ROUTE" ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse" :
                                      "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                    }`}>
                                      {o.status}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-indigo-300 font-semibold">
                                    {assignedTruck ? assignedTruck.supplier : "Non affecté"}
                                  </td>
                                </tr>
                              );
                            })
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Twin Simulation Portal (Client Orders & Supplier Dispatch) */}
              {activeTab === "dispatch" && (
                <div className="space-y-6">
                  <div>
                    <h2 className="text-lg font-bold text-slate-200 bg-gradient-to-r from-white to-slate-450 bg-clip-text text-transparent">
                      Simulateur Multi-Flux & Portails APIs
                    </h2>
                    <p className="text-xs text-slate-400">
                      Générez des flux d'activités logistiques en simulant les APIs fournisseurs (approvisionnement) et clients (livraisons).
                    </p>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Panel Left: Client Orders Simulator */}
                    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center space-x-2.5 mb-4">
                          <div className="h-8 w-8 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400">
                            <ArrowUpRight className="h-5 w-5" />
                          </div>
                          <div>
                            <h3 className="font-bold text-slate-200 text-sm">Portail Client (Sortant)</h3>
                            <p className="text-[11px] text-slate-400">
                              Simule une commande client. Recherche le meilleur camion d'entreprise disponible et lance le chargement par AGV.
                            </p>
                          </div>
                        </div>

                        <form onSubmit={handlePlaceClientOrder} className="space-y-4">
                          <div>
                            <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Nom du Client</label>
                            <select
                              value={clientName}
                              onChange={(e) => setClientName(e.target.value)}
                              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500 transition"
                            >
                              <option value="Auchan Retail">Auchan Retail</option>
                              <option value="Carrefour Logistics">Carrefour Logistics</option>
                              <option value="Leclerc Distrib">Leclerc Distrib</option>
                              <option value="Decathlon Supply">Decathlon Supply</option>
                              <option value="Renault Group">Renault Group</option>
                            </select>
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Type de Cargo</label>
                              <select
                                value={clientCargo}
                                onChange={(e) => setClientCargo(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500 transition"
                              >
                                <option value="General">General</option>
                                <option value="Cold">Cold (Réfrigéré)</option>
                                <option value="Hazardous">Hazardous (Dangereux)</option>
                                <option value="Electronics">Electronics (Électronique)</option>
                              </select>
                            </div>

                            <div>
                              <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Destination Route</label>
                              <select
                                value={clientDestination}
                                onChange={(e) => setClientDestination(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500 transition"
                              >
                                <option value="Route_1">Route 1 (North Hub)</option>
                                <option value="Route_2">Route 2 (West Port)</option>
                                <option value="Route_3">Route 3 (South Depot)</option>
                                <option value="Route_4">Route 4 (East Warehouse)</option>
                              </select>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Quantité (Unités)</label>
                              <input
                                type="number"
                                min="1"
                                max="50"
                                value={clientQuantity}
                                onChange={(e) => setClientQuantity(parseInt(e.target.value) || 10)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500 transition"
                              />
                            </div>

                            <div>
                              <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Priorité (1-5)</label>
                              <input
                                type="number"
                                min="1"
                                max="5"
                                value={clientPriority}
                                onChange={(e) => setClientPriority(parseInt(e.target.value) || 3)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500 transition"
                              />
                            </div>
                          </div>

                          <button
                            type="submit"
                            disabled={simulating}
                            className="w-full mt-4 py-2.5 px-4 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-xl text-xs transition flex items-center justify-center space-x-2 shadow-lg shadow-purple-600/20"
                          >
                            <Send className="h-3.5 w-3.5" />
                            <span>{simulating ? "Traitement IA..." : "Envoyer Commande Client"}</span>
                          </button>
                        </form>
                      </div>
                    </div>

                    {/* Panel Right: Supplier Dispatch Simulator */}
                    <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center space-x-2.5 mb-4">
                          <div className="h-8 w-8 rounded-lg bg-cyan-500/10 flex items-center justify-center text-cyan-400">
                            <ArrowDownLeft className="h-5 w-5" />
                          </div>
                          <div>
                            <h3 className="font-bold text-slate-200 text-sm">Portail Fournisseur (Entrant)</h3>
                            <p className="text-[11px] text-slate-400">
                              Simule l'envoi d'un camion fournisseur. Il se déplace vers l'entrepôt, son ETA est prédit par XGBoost et il n'est pas tracé par GPS.
                            </p>
                          </div>
                        </div>

                        <form onSubmit={handleSingleSupplierDispatch} className="space-y-3">
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Fournisseur</label>
                              <select
                                value={singleSupplier}
                                onChange={(e) => setSingleSupplier(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition"
                              >
                                {SUPPLIERS.map(s => <option key={s} value={s}>{s}</option>)}
                              </select>
                            </div>

                            <div>
                              <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Cargo Type</label>
                              <select
                                value={singleCargo}
                                onChange={(e) => setSingleCargo(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition"
                              >
                                <option value="General">General</option>
                                <option value="Cold">Cold</option>
                                <option value="Hazardous">Hazardous</option>
                                <option value="Electronics">Electronics</option>
                              </select>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Route & Origine</label>
                              <select
                                value={singleRoute}
                                onChange={(e) => setSingleRoute(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition"
                              >
                                <option value="Route_1">Route 1 (North Hub)</option>
                                <option value="Route_2">Route 2 (West Port)</option>
                                <option value="Route_3">Route 3 (South Depot)</option>
                                <option value="Route_4">Route 4 (East Warehouse)</option>
                              </select>
                            </div>

                            <div>
                              <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Distance (miles)</label>
                              <input
                                type="number"
                                min="10"
                                max="500"
                                value={singleDistance}
                                onChange={(e) => setSingleDistance(parseInt(e.target.value) || 100)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition"
                              />
                            </div>
                          </div>

                          <div className="grid grid-cols-3 gap-2">
                            <div>
                              <label className="text-[9px] uppercase font-bold text-slate-500 block mb-1">Trafic</label>
                              <select
                                value={singleTraffic}
                                onChange={(e) => setSingleTraffic(parseInt(e.target.value))}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-[10px] text-slate-200 focus:outline-none focus:border-cyan-500"
                              >
                                <option value={0}>Fluid</option>
                                <option value={1}>Medium</option>
                                <option value={2}>Heavy</option>
                              </select>
                            </div>

                            <div>
                              <label className="text-[9px] uppercase font-bold text-slate-500 block mb-1">Météo</label>
                              <select
                                value={singleWeather}
                                onChange={(e) => setSingleWeather(parseInt(e.target.value))}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-[10px] text-slate-200 focus:outline-none focus:border-cyan-500"
                              >
                                <option value={0}>Sunny</option>
                                <option value={1}>Rainy</option>
                                <option value={2}>Stormy</option>
                              </select>
                            </div>

                            <div>
                              <label className="text-[9px] uppercase font-bold text-slate-500 block mb-1">Route Risk</label>
                              <select
                                value={singleRisk}
                                onChange={(e) => setSingleRisk(parseInt(e.target.value))}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-[10px] text-slate-200 focus:outline-none focus:border-cyan-500"
                              >
                                <option value={0}>Low</option>
                                <option value={1}>Medium</option>
                                <option value={2}>High</option>
                              </select>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Priorité (1-5)</label>
                              <input
                                type="number"
                                min="1"
                                max="5"
                                value={singlePriority}
                                onChange={(e) => setSinglePriority(parseInt(e.target.value) || 3)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 transition"
                              />
                            </div>
                          </div>

                          <button
                            type="submit"
                            disabled={simulating}
                            className="w-full mt-3 py-2.5 px-4 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-xl text-xs transition flex items-center justify-center space-x-2 shadow-lg shadow-cyan-600/20"
                          >
                            <Send className="h-3.5 w-3.5" />
                            <span>{simulating ? "Orchestration..." : "Dispatche Fournisseur"}</span>
                          </button>
                        </form>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: Trucks */}
              {activeTab === "trucks" && (
                <div className="space-y-8">
                  {/* Flotte Propre Section */}
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <h2 className="text-lg font-bold flex items-center space-x-2">
                        <span>Flotte Propre (Livraisons Clients)</span>
                      </h2>
                      <span className="text-xs text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1 rounded-full">
                        Total: {state.trucks.filter((t: any) => t.is_company_truck).length} camions
                      </span>
                    </div>

                    <div className="border border-slate-800/80 bg-slate-900/40 rounded-2xl overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-850">
                          <thead className="bg-slate-950/60">
                            <tr>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">ID</th>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Identifiant</th>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Cargo & Type</th>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Location / Route</th>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Status Interne</th>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Status Global</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-850 bg-slate-900/20">
                            {state.trucks.filter((t: any) => t.is_company_truck).length === 0 ? (
                              <tr>
                                <td colSpan={6} className="text-center py-10 text-slate-500 text-sm">
                                  Aucun camion d'entreprise configuré.
                                </td>
                              </tr>
                            ) : (
                              state.trucks.filter((t: any) => t.is_company_truck).map((t: any) => (
                                <tr key={t.truck_id} className="hover:bg-slate-900/30 transition">
                                  <td className="px-6 py-4 text-xs font-mono font-bold text-slate-300">#{t.truck_id}</td>
                                  <td className="px-6 py-4 text-xs font-semibold text-slate-200">
                                    <div>{t.supplier}</div>
                                    <div className="text-[10px] text-cyan-500 font-normal mt-0.5">Flotte Interne</div>
                                  </td>
                                  <td className="px-6 py-4 text-xs">
                                    <span className={`w-fit px-2 py-0.5 rounded-full text-[9px] font-semibold border ${
                                      t.cargo_type?.toLowerCase() === "cold" ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/15" :
                                      t.cargo_type?.toLowerCase() === "hazardous" ? "bg-red-500/10 text-red-400 border-red-500/15" :
                                      t.cargo_type?.toLowerCase() === "electronics" ? "bg-amber-500/10 text-amber-400 border-amber-500/15" :
                                      "bg-slate-500/10 text-slate-300 border-slate-500/15"
                                    }`}>
                                      {t.cargo_type}
                                    </span>
                                  </td>
                                  <td className="px-6 py-4 text-xs">
                                    <div className="space-y-1.5">
                                      <div className="flex justify-between text-[10px] text-slate-400">
                                        <span>{t.company_truck_status === "IDLE" ? "Warehouse Parking" : `${t.route_id} (${t.company_truck_status === "EN_ROUTE_TO_CLIENT" ? "Outbound" : "Inbound"})`}</span>
                                        {!["IDLE", "LOADING"].includes(t.company_truck_status) && <span className="font-bold text-slate-300">{(t.gps_progress * 100).toFixed(0)}%</span>}
                                      </div>
                                      {!["IDLE", "LOADING"].includes(t.company_truck_status) && (
                                        <div className="w-24 bg-slate-950 rounded-full h-1.5 overflow-hidden">
                                          <div className="bg-cyan-500 h-1.5 rounded-full" style={{ width: `${t.gps_progress * 100}%` }}></div>
                                        </div>
                                      )}
                                    </div>
                                  </td>
                                  <td className="px-6 py-4 text-xs">
                                    <span className={`px-2 py-1 rounded-lg text-[10px] font-bold ${
                                      t.company_truck_status === "IDLE" ? "bg-slate-800 text-slate-400 border border-slate-700" :
                                      t.company_truck_status === "LOADING" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                                      "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                                    }`}>
                                      {t.company_truck_status}
                                    </span>
                                  </td>
                                  <td className="px-6 py-4 text-xs">
                                    <span className={`px-2 py-1 rounded-lg text-[10px] font-bold ${
                                      t.status === "COMPLETED" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                                      t.status === "PROCESSING" ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20" :
                                      "bg-slate-800 text-slate-400 border border-slate-700"
                                    }`}>
                                      {t.status}
                                    </span>
                                  </td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>

                  {/* Fournisseurs Section */}
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <h2 className="text-lg font-bold flex items-center space-x-2">
                        <span>Camions Fournisseurs (Approvisionnement)</span>
                      </h2>
                      <span className="text-xs text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1 rounded-full">
                        Total: {state.trucks.filter((t: any) => !t.is_company_truck).length} camions
                      </span>
                    </div>

                    <div className="border border-slate-800/80 bg-slate-900/40 rounded-2xl overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-850">
                          <thead className="bg-slate-950/60">
                            <tr>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">ID</th>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Fournisseur</th>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Cargo & Type</th>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Route & Progress</th>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">ETA (XGBoost)</th>
                              <th className="px-6 py-3.5 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-850 bg-slate-900/20">
                            {state.trucks.filter((t: any) => !t.is_company_truck).length === 0 ? (
                              <tr>
                                <td colSpan={6} className="text-center py-10 text-slate-500 text-sm">
                                  Aucun camion fournisseur. Allez dans le Portail Fournisseur pour en dispatcher.
                                </td>
                              </tr>
                            ) : (
                              state.trucks.filter((t: any) => !t.is_company_truck).map((t: any) => (
                                <tr key={t.truck_id} className="hover:bg-slate-900/30 transition">
                                  <td className="px-6 py-4 text-xs font-mono font-bold text-slate-300">#{t.truck_id}</td>
                                  <td className="px-6 py-4 text-xs font-semibold text-slate-200">
                                    <div>{t.supplier}</div>
                                    <div className="text-[10px] text-slate-500 font-normal mt-0.5">Priorité: {t.priority}/5</div>
                                  </td>
                                  <td className="px-6 py-4 text-xs">
                                    <div className="flex flex-col space-y-1">
                                      <span className={`w-fit px-2 py-0.5 rounded text-[9px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/15`}>
                                        DELIVERY
                                      </span>
                                      <span className={`w-fit px-2 py-0.5 rounded-full text-[9px] font-semibold border ${
                                        t.cargo_type?.toLowerCase() === "cold" ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/15" :
                                        t.cargo_type?.toLowerCase() === "hazardous" ? "bg-red-500/10 text-red-400 border-red-500/15" :
                                        t.cargo_type?.toLowerCase() === "electronics" ? "bg-amber-500/10 text-amber-400 border-amber-500/15" :
                                        "bg-slate-500/10 text-slate-300 border-slate-500/15"
                                      }`}>
                                        {t.cargo_type}
                                      </span>
                                    </div>
                                  </td>
                                  <td className="px-6 py-4 text-xs">
                                    <div className="space-y-1.5">
                                      <div className="flex justify-between text-[10px] text-slate-400">
                                        <span>{t.route_id} ({t.origin})</span>
                                        <span className="font-bold text-slate-300">{(t.gps_progress * 100).toFixed(0)}%</span>
                                      </div>
                                      <div className="w-24 bg-slate-950 rounded-full h-1.5 overflow-hidden">
                                        <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${t.gps_progress * 100}%` }}></div>
                                      </div>
                                    </div>
                                  </td>
                                  <td className="px-6 py-4 text-xs font-semibold text-indigo-400">
                                    {new Date(t.eta).toLocaleTimeString()}
                                  </td>
                                  <td className="px-6 py-4 text-xs">
                                    <span className={`px-2 py-1 rounded-lg text-[10px] font-bold ${
                                      t.status === "COMPLETED" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                                      t.status === "PROCESSING" ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20" :
                                      t.status === "PENDING" ? "bg-sky-500/10 text-sky-400 border border-sky-500/20 animate-pulse" :
                                      t.status === "QUEUED" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                                      "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                                    }`}>
                                      {t.status === "PENDING" ? "EN ROUTE" : t.status}
                                    </span>
                                  </td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 4: Robots */}
              {activeTab === "robots" && (
                <div className="space-y-6">
                  <h2 className="text-lg font-bold">Flotte Robotique (AGVs)</h2>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {state.robots.map((r: any) => (
                      <div key={r.robot_id} className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between">
                        <div className="flex justify-between items-start">
                          <div>
                            <h3 className="font-bold text-slate-200">Robot R{r.robot_id}</h3>
                            <div className="flex items-center space-x-1.5 text-xs text-slate-400 mt-1">
                              <MapPin className="h-3.5 w-3.5 text-indigo-500" />
                              <span>Position actuelle : <strong className="text-indigo-400">{r.position}</strong></span>
                            </div>
                          </div>
                          <span className={`px-2.5 py-1 rounded-lg text-[10px] font-bold ${
                            r.status === "AVAILABLE" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                            r.status === "BUSY" ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20" :
                            "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          }`}>
                            {r.status}
                          </span>
                        </div>

                        {/* Battery Level bar */}
                        <div className="mt-6 space-y-1.5">
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-400 flex items-center space-x-1">
                              <Battery className={`h-4.5 w-4.5 ${r.battery < 30 ? 'text-red-400' : 'text-emerald-400'}`} />
                              <span>Niveau Batterie</span>
                            </span>
                            <span className={`font-bold ${r.battery < 30 ? 'text-red-400' : 'text-slate-200'}`}>
                              {r.battery}%
                            </span>
                          </div>
                          <div className="w-full bg-slate-950 border border-slate-800 rounded-full h-2.5 overflow-hidden">
                            <div 
                              className={`h-2.5 rounded-full transition-all duration-500 ${
                                r.battery < 30 ? 'bg-gradient-to-r from-red-600 to-red-400' : 'bg-gradient-to-r from-emerald-600 to-emerald-400'
                              }`} 
                              style={{ width: `${r.battery}%` }}
                            ></div>
                          </div>
                        </div>

                        {/* Active Mission associated */}
                        <div className="mt-6 pt-4 border-t border-slate-800/80 text-xs">
                          {r.status === "BUSY" ? (
                            <div className="flex justify-between text-indigo-400 font-medium">
                              <span>Mission en cours...</span>
                              <span className="underline">Transport</span>
                            </div>
                          ) : (
                            <span className="text-slate-500">Prêt pour affectation</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tab 5: Storage & Docks */}
              {activeTab === "storage" && (
                <div className="space-y-8">
                  {/* Docks configuration */}
                  <div>
                    <h2 className="text-md font-bold mb-4 flex items-center space-x-2">
                      <Truck className="h-5 w-5 text-indigo-400" />
                      <span>Quais de Déchargement / Chargement</span>
                    </h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                      {state.docks.map((d: any) => (
                        <div key={d.dock_id} className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between h-32">
                          <div className="flex justify-between items-center">
                            <span className="font-bold text-slate-200 text-sm">Quai #{d.dock_id}</span>
                            <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                              d.status === "FREE" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                            }`}>
                              {d.status}
                            </span>
                          </div>
                          {d.current_truck ? (
                            <div className="space-y-1">
                              <span className="text-[10px] text-slate-400 block font-semibold uppercase">Camion Actuel</span>
                              <span className="text-xs font-bold text-slate-300">Camion #{d.current_truck}</span>
                            </div>
                          ) : (
                            <span className="text-xs text-slate-500 italic">Vide et disponible</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Storage Zones configuration */}
                  <div>
                    <h2 className="text-md font-bold mb-4 flex items-center space-x-2">
                      <Warehouse className="h-5 w-5 text-indigo-400" />
                      <span>Zones de Stockage</span>
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {state.zones.map((z: any) => {
                        const percent = (z.occupied / z.capacity) * 100;
                        return (
                          <div key={z.zone_id} className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-5 space-y-4">
                            <div className="flex justify-between items-start">
                              <div>
                                <h3 className="font-bold text-slate-200">Zone #{z.zone_id}</h3>
                                <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-950 border border-slate-850 ${
                                  z.product_type === "Cold" ? "text-cyan-400 border-cyan-500/10" :
                                  z.product_type === "Hazardous" ? "text-red-400 border-red-500/10" :
                                  z.product_type === "Electronics" ? "text-amber-400 border-amber-500/10" :
                                  "text-slate-300 border-slate-500/10"
                                }`}>
                                  {z.product_type}
                                </span>
                              </div>
                              <span className="text-xs font-mono font-bold text-slate-300">
                                {z.occupied}/{z.capacity} units
                              </span>
                            </div>

                            {/* Capacity progress */}
                            <div className="space-y-1.5">
                              <div className="w-full bg-slate-950 border border-slate-850 rounded-full h-3 overflow-hidden">
                                <div 
                                  className={`h-3 rounded-full transition-all duration-500 ${
                                    percent >= 90 ? 'bg-red-500' : percent >= 70 ? 'bg-amber-500' : 'bg-indigo-500'
                                  }`} 
                                  style={{ width: `${percent}%` }}
                                ></div>
                              </div>
                              <div className="flex justify-between text-[10px] text-slate-500">
                                <span>Saturation</span>
                                <span className="font-semibold text-slate-400">{percent.toFixed(0)}%</span>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 6: Logs */}
              {activeTab === "logs" && (
                <div className="space-y-6">
                  <div className="flex justify-between items-center">
                    <h2 className="text-lg font-bold">Traçabilité & Historique de l'IA</h2>
                    <span className="text-xs text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1 rounded-full">
                      Logs: {state.decision_logs.length}
                    </span>
                  </div>

                  <div className="border border-slate-800/80 bg-slate-900/40 rounded-2xl overflow-hidden">
                    <div className="overflow-y-auto max-h-[600px]">
                      <div className="divide-y divide-slate-850">
                        {state.decision_logs.length === 0 ? (
                          <div className="text-center py-10 text-slate-500 text-sm">
                            Aucune décision enregistrée. Les décisions apparaissent dès que vous simulez un camion.
                          </div>
                        ) : (
                          state.decision_logs.map((l: any) => (
                            <div key={l.decision_id} className="p-4 hover:bg-slate-900/30 transition flex flex-col sm:flex-row justify-between sm:items-start gap-3">
                              <div className="space-y-1.5 flex-1">
                                <div className="flex items-center space-x-2.5">
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    l.decision_type === "ROUTING_SUCCESS" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/15" :
                                    l.decision_type === "INCIDENT_UPDATE" ? "bg-orange-500/10 text-orange-400 border border-orange-500/15" :
                                    l.decision_type === "MISSION_COMPLETED" ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/15" :
                                    l.decision_type === "TRUCK_REJECTED" ? "bg-red-500/10 text-red-400 border border-red-500/15" :
                                    "bg-slate-800 text-slate-400"
                                  }`}>
                                    {l.decision_type}
                                  </span>
                                  <span className="text-[10px] text-slate-500 font-medium">Source: {l.agent_source}</span>
                                </div>
                                <p className="text-xs text-slate-300 leading-relaxed font-sans">{l.decision_reason}</p>
                              </div>
                              <div className="text-[10px] text-slate-500 font-mono self-end sm:self-start">
                                {new Date(l.timestamp).toLocaleString()}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

const SUPPLIERS = [
  "Amazon Logistics", "DHL Express", "FedEx Supply Chain", 
  "Geodis France", "Kuehne + Nagel", "DB Schenker", 
  "Maersk Logistics", "XPO Logistics", "Ceva Logistics"
];
