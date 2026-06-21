import React, { useState } from 'react';
import { 
  BarChart3, Users, MapPin, TrendingUp, AlertTriangle, 
  Shield, Activity, Clock, CheckCircle, Target,
  ChevronRight, Bell, Search, Menu
} from 'lucide-react';
import StatCard from '../components/StatCard';
import TierBadge from '../components/TierBadge';

const ACPDashboard = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const stats = [
    { title: 'Total Zones', value: '24', change: '+2', icon: MapPin, color: 'blue' },
    { title: 'Active Officers', value: '156', change: '+12', icon: Users, color: 'green' },
    { title: 'Crime Rate', value: '-8.2%', change: '↓ 2.1%', icon: TrendingUp, color: 'emerald' },
    { title: 'Pending Cases', value: '43', change: '-5', icon: Clock, color: 'orange' },
  ];

  const zonePerformance = [
    { zone: 'North District', crimeRate: 12, clearance: 87, officers: 42, status: 'good' },
    { zone: 'South District', crimeRate: 18, clearance: 79, officers: 38, status: 'warning' },
    { zone: 'East District', crimeRate: 24, clearance: 71, officers: 35, status: 'critical' },
    { zone: 'West District', crimeRate: 15, clearance: 82, officers: 41, status: 'good' },
  ];

  const recentAlerts = [
    { id: 1, type: 'high', message: 'Spike in theft reports - Central Market', time: '15 min ago' },
    { id: 2, type: 'medium', message: 'Traffic congestion - Highway 42', time: '32 min ago' },
    { id: 3, type: 'low', message: 'Community event - Park Street', time: '1 hour ago' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="bg-white/10 backdrop-blur-md border-b border-white/20 sticky top-0 z-50">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              <Menu className="w-6 h-6 text-white" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-white">ACP Command Center</h1>
              <p className="text-purple-200 text-sm">Strategic Overview & Resource Management</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-purple-300" />
              <input 
                type="text" 
                placeholder="Search zones, officers..." 
                className="pl-10 pr-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-purple-300 focus:outline-none focus:ring-2 focus:ring-purple-500 w-64"
              />
            </div>
            <button className="relative p-2 hover:bg-white/10 rounded-lg transition-colors">
              <Bell className="w-6 h-6 text-white" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>
            <div className="flex items-center gap-3 pl-4 border-l border-white/20">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-white font-semibold">Commissioner Sharma</p>
                <p className="text-purple-300 text-sm">ACP - North Region</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        {sidebarOpen && (
          <aside className="w-64 bg-black/20 backdrop-blur-md min-h-[calc(100vh-80px)] border-r border-white/10 p-6">
            <nav className="space-y-2">
              {[
                { icon: BarChart3, label: 'Overview', active: true },
                { icon: MapPin, label: 'Zone Management' },
                { icon: Users, label: 'Officer Deployment' },
                { icon: Target, label: 'Performance Metrics' },
                { icon: Activity, label: 'Crime Analytics' },
                { icon: AlertTriangle, label: 'Critical Alerts' },
                { icon: CheckCircle, label: 'Case Reviews' },
              ].map((item, idx) => (
                <button
                  key={idx}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                    item.active 
                      ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg shadow-purple-500/30' 
                      : 'text-purple-200 hover:bg-white/10'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                  {item.active && <ChevronRight className="w-4 h-4 ml-auto" />}
                </button>
              ))}
            </nav>

            <div className="mt-8 pt-8 border-t border-white/10">
              <h3 className="text-purple-300 text-sm font-semibold mb-4">Quick Actions</h3>
              <button className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white py-3 rounded-lg font-medium transition-all shadow-lg shadow-emerald-500/30">
                Deploy Resources
              </button>
              <button className="w-full mt-2 bg-white/10 hover:bg-white/20 text-white py-3 rounded-lg font-medium transition-all">
                Generate Report
              </button>
            </div>
          </aside>
        )}

        {/* Main Content */}
        <main className="flex-1 p-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {stats.map((stat, idx) => (
              <StatCard
                key={idx}
                title={stat.title}
                value={stat.value}
                change={stat.change}
                icon={stat.icon}
                color={stat.color}
                gradient="dark"
              />
            ))}
          </div>

          {/* Zone Performance & Alerts */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Zone Performance */}
            <div className="lg:col-span-2 bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white">Zone Performance</h2>
                <button className="text-purple-300 hover:text-white transition-colors text-sm">
                  View All Zones →
                </button>
              </div>
              <div className="space-y-4">
                {zonePerformance.map((zone, idx) => (
                  <div key={idx} className="bg-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <MapPin className="w-5 h-5 text-purple-400" />
                        <span className="text-white font-semibold">{zone.zone}</span>
                      </div>
                      <TierBadge tier={zone.status.toUpperCase()} />
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-purple-300 text-xs mb-1">Crime Rate</p>
                        <p className={`text-lg font-bold ${zone.crimeRate > 20 ? 'text-red-400' : 'text-green-400'}`}>
                          {zone.crimeRate}%
                        </p>
                      </div>
                      <div>
                        <p className="text-purple-300 text-xs mb-1">Clearance</p>
                        <p className="text-lg font-bold text-blue-400">{zone.clearance}%</p>
                      </div>
                      <div>
                        <p className="text-purple-300 text-xs mb-1">Officers</p>
                        <p className="text-lg font-bold text-white">{zone.officers}</p>
                      </div>
                    </div>
                    <div className="mt-3 bg-white/10 rounded-full h-2 overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all ${
                          zone.status === 'critical' ? 'bg-red-500' : 
                          zone.status === 'warning' ? 'bg-orange-500' : 'bg-green-500'
                        }`}
                        style={{ width: `${zone.clearance}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Alerts */}
            <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white">Live Alerts</h2>
                <span className="bg-red-500/20 text-red-400 px-3 py-1 rounded-full text-xs font-semibold">
                  3 New
                </span>
              </div>
              <div className="space-y-4">
                {recentAlerts.map((alert) => (
                  <div key={alert.id} className="bg-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors cursor-pointer">
                    <div className="flex items-start gap-3">
                      <div className={`w-2 h-2 rounded-full mt-2 ${
                        alert.type === 'high' ? 'bg-red-500' : 
                        alert.type === 'medium' ? 'bg-orange-500' : 'bg-blue-500'
                      }`}></div>
                      <div className="flex-1">
                        <p className="text-white text-sm">{alert.message}</p>
                        <p className="text-purple-300 text-xs mt-1">{alert.time}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <button className="w-full mt-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white py-3 rounded-lg font-medium transition-all">
                View All Alerts
              </button>
            </div>
          </div>

          {/* Strategic Insights */}
          <div className="bg-gradient-to-r from-purple-900/50 to-pink-900/50 backdrop-blur-md rounded-2xl border border-white/20 p-6">
            <h2 className="text-xl font-bold text-white mb-4">Strategic Insights</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white/5 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-5 h-5 text-green-400" />
                  <h3 className="text-white font-semibold">Positive Trends</h3>
                </div>
                <p className="text-purple-200 text-sm">Overall crime rate decreased by 8.2% compared to last quarter. Theft cases show significant reduction.</p>
              </div>
              <div className="bg-white/5 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-5 h-5 text-orange-400" />
                  <h3 className="text-white font-semibold">Areas of Concern</h3>
                </div>
                <p className="text-purple-200 text-sm">East District requires additional resources. Clearance rate below target threshold.</p>
              </div>
              <div className="bg-white/5 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-5 h-5 text-blue-400" />
                  <h3 className="text-white font-semibold">Recommended Actions</h3>
                </div>
                <p className="text-purple-200 text-sm">Deploy 5 additional officers to East District. Schedule community engagement programs.</p>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default ACPDashboard;
