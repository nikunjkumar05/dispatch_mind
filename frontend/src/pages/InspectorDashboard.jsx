import React, { useState } from 'react';
import { 
  FileText, Search, Clock, AlertCircle, CheckCircle, XCircle,
  BarChart2, Users, MapPin, Calendar, Filter, Download,
  Eye, Edit, Trash2, ChevronRight, Bell, Menu, Shield
} from 'lucide-react';
import StatCard from '../components/StatCard';
import TierBadge from '../components/TierBadge';

const InspectorDashboard = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState('cases');

  const stats = [
    { title: 'Active Cases', value: '28', change: '+4', icon: FileText, color: 'blue' },
    { title: 'Pending Review', value: '12', change: '-2', icon: Clock, color: 'orange' },
    { title: 'Resolved Today', value: '7', change: '+3', icon: CheckCircle, color: 'green' },
    { title: 'Team Members', value: '18', change: '0', icon: Users, color: 'purple' },
  ];

  const cases = [
    { id: 'CR-2024-001', type: 'Theft', location: 'Central Market', status: 'investigating', priority: 'high', assigned: 'Officer Kumar', date: '2 hrs ago' },
    { id: 'CR-2024-002', type: 'Assault', location: 'Park Street', status: 'pending', priority: 'critical', assigned: 'Officer Singh', date: '4 hrs ago' },
    { id: 'CR-2024-003', type: 'Fraud', location: 'Business District', status: 'review', priority: 'medium', assigned: 'Officer Patel', date: '6 hrs ago' },
    { id: 'CR-2024-004', type: 'Vandalism', location: 'School Zone', status: 'resolved', priority: 'low', assigned: 'Officer Sharma', date: '1 day ago' },
    { id: 'CR-2024-005', type: 'Burglary', location: 'Residential Area', status: 'investigating', priority: 'high', assigned: 'Officer Verma', date: '1 day ago' },
  ];

  const teamMembers = [
    { name: 'Officer Rajesh Kumar', status: 'active', cases: 5, location: 'North Sector' },
    { name: 'Officer Priya Singh', status: 'on-call', cases: 3, location: 'Central Sector' },
    { name: 'Officer Amit Patel', status: 'active', cases: 4, location: 'East Sector' },
    { name: 'Officer Neha Sharma', status: 'off-duty', cases: 0, location: 'Station' },
  ];

  const getStatusColor = (status) => {
    switch(status) {
      case 'investigating': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'pending': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'review': return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      case 'resolved': return 'bg-green-500/20 text-green-400 border-green-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getPriorityColor = (priority) => {
    switch(priority) {
      case 'critical': return 'bg-red-500 text-white';
      case 'high': return 'bg-orange-500 text-white';
      case 'medium': return 'bg-yellow-500 text-black';
      case 'low': return 'bg-blue-500 text-white';
      default: return 'bg-gray-500 text-white';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
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
              <h1 className="text-2xl font-bold text-white">Inspector Dashboard</h1>
              <p className="text-blue-200 text-sm">Case Management & Team Oversight</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-blue-300" />
              <input 
                type="text" 
                placeholder="Search cases, officers..." 
                className="pl-10 pr-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
              />
            </div>
            <button className="relative p-2 hover:bg-white/10 rounded-lg transition-colors">
              <Bell className="w-6 h-6 text-white" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>
            <div className="flex items-center gap-3 pl-4 border-l border-white/20">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-full flex items-center justify-center">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-white font-semibold">Inspector Gupta</p>
                <p className="text-blue-300 text-sm">Station House Officer</p>
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
                { icon: FileText, label: 'Case Management', active: true },
                { icon: Users, label: 'Team Overview' },
                { icon: MapPin, label: 'Patrol Routes' },
                { icon: BarChart2, label: 'Performance Reports' },
                { icon: Calendar, label: 'Duty Roster' },
                { icon: AlertCircle, label: 'Urgent Reviews' },
                { icon: Download, label: 'Export Data' },
              ].map((item, idx) => (
                <button
                  key={idx}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                    item.active 
                      ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-lg shadow-blue-500/30' 
                      : 'text-blue-200 hover:bg-white/10'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                  {item.active && <ChevronRight className="w-4 h-4 ml-auto" />}
                </button>
              ))}
            </nav>

            <div className="mt-8 pt-8 border-t border-white/10">
              <h3 className="text-blue-300 text-sm font-semibold mb-4">Filters</h3>
              <div className="space-y-2">
                <button className="w-full flex items-center justify-between px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-all">
                  <span>All Cases</span>
                  <Filter className="w-4 h-4" />
                </button>
                <button className="w-full flex items-center justify-between px-4 py-2 text-blue-200 hover:bg-white/10 rounded-lg transition-all">
                  <span>High Priority</span>
                  <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded text-xs">5</span>
                </button>
                <button className="w-full flex items-center justify-between px-4 py-2 text-blue-200 hover:bg-white/10 rounded-lg transition-all">
                  <span>Pending Review</span>
                  <span className="bg-orange-500/20 text-orange-400 px-2 py-0.5 rounded text-xs">12</span>
                </button>
              </div>
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

          {/* Tabs */}
          <div className="flex gap-4 mb-6 border-b border-white/10 pb-2">
            <button 
              onClick={() => setActiveTab('cases')}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                activeTab === 'cases' 
                  ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white' 
                  : 'text-blue-200 hover:bg-white/10'
              }`}
            >
              Active Cases
            </button>
            <button 
              onClick={() => setActiveTab('team')}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                activeTab === 'team' 
                  ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white' 
                  : 'text-blue-200 hover:bg-white/10'
              }`}
            >
              Team Overview
            </button>
            <button 
              onClick={() => setActiveTab('analytics')}
              className={`px-6 py-2 rounded-lg font-medium transition-all ${
                activeTab === 'analytics' 
                  ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white' 
                  : 'text-blue-200 hover:bg-white/10'
              }`}
            >
              Analytics
            </button>
          </div>

          {/* Cases Tab */}
          {activeTab === 'cases' && (
            <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 overflow-hidden">
              <div className="p-6 border-b border-white/10 flex items-center justify-between">
                <h2 className="text-xl font-bold text-white">Case Register</h2>
                <button className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  New Case
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-white/5">
                    <tr>
                      <th className="px-6 py-4 text-left text-blue-300 font-semibold text-sm">Case ID</th>
                      <th className="px-6 py-4 text-left text-blue-300 font-semibold text-sm">Type</th>
                      <th className="px-6 py-4 text-left text-blue-300 font-semibold text-sm">Location</th>
                      <th className="px-6 py-4 text-left text-blue-300 font-semibold text-sm">Priority</th>
                      <th className="px-6 py-4 text-left text-blue-300 font-semibold text-sm">Status</th>
                      <th className="px-6 py-4 text-left text-blue-300 font-semibold text-sm">Assigned To</th>
                      <th className="px-6 py-4 text-left text-blue-300 font-semibold text-sm">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cases.map((caseItem, idx) => (
                      <tr key={idx} className="border-t border-white/10 hover:bg-white/5 transition-colors">
                        <td className="px-6 py-4 text-white font-mono text-sm">{caseItem.id}</td>
                        <td className="px-6 py-4 text-white">{caseItem.type}</td>
                        <td className="px-6 py-4 text-blue-200">{caseItem.location}</td>
                        <td className="px-6 py-4">
                          <span className={`${getPriorityColor(caseItem.priority)} px-3 py-1 rounded-full text-xs font-semibold`}>
                            {caseItem.priority.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`${getStatusColor(caseItem.status)} px-3 py-1 rounded-full text-xs font-semibold border`}>
                            {caseItem.status.charAt(0).toUpperCase() + caseItem.status.slice(1)}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-blue-200">{caseItem.assigned}</td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <button className="p-2 hover:bg-white/10 rounded-lg transition-colors text-blue-300 hover:text-white">
                              <Eye className="w-4 h-4" />
                            </button>
                            <button className="p-2 hover:bg-white/10 rounded-lg transition-colors text-blue-300 hover:text-white">
                              <Edit className="w-4 h-4" />
                            </button>
                            <button className="p-2 hover:bg-red-500/20 rounded-lg transition-colors text-red-400 hover:text-red-300">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Team Tab */}
          {activeTab === 'team' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {teamMembers.map((member, idx) => (
                <div key={idx} className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-6 hover:bg-white/15 transition-all">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                        member.status === 'active' ? 'bg-gradient-to-br from-green-500 to-emerald-500' :
                        member.status === 'on-call' ? 'bg-gradient-to-br from-orange-500 to-yellow-500' :
                        'bg-gradient-to-br from-gray-500 to-slate-500'
                      }`}>
                        <Users className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h3 className="text-white font-semibold">{member.name}</h3>
                        <p className="text-blue-300 text-sm">{member.location}</p>
                      </div>
                    </div>
                    <TierBadge tier={member.status.toUpperCase()} />
                  </div>
                  <div className="flex items-center justify-between pt-4 border-t border-white/10">
                    <div>
                      <p className="text-blue-300 text-xs mb-1">Active Cases</p>
                      <p className="text-white text-xl font-bold">{member.cases}</p>
                    </div>
                    <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all">
                      View Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Analytics Tab */}
          {activeTab === 'analytics' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-6">
                <h3 className="text-white font-bold mb-4">Case Resolution Rate</h3>
                <div className="h-64 flex items-center justify-center">
                  <div className="text-center">
                    <div className="text-5xl font-bold text-green-400 mb-2">78%</div>
                    <p className="text-blue-200">Average resolution rate this month</p>
                  </div>
                </div>
              </div>
              <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-6">
                <h3 className="text-white font-bold mb-4">Cases by Type</h3>
                <div className="space-y-4">
                  {[
                    { type: 'Theft', count: 12, percentage: 35 },
                    { type: 'Assault', count: 8, percentage: 23 },
                    { type: 'Fraud', count: 6, percentage: 17 },
                    { type: 'Others', count: 8, percentage: 25 },
                  ].map((item, idx) => (
                    <div key={idx}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-blue-200">{item.type}</span>
                        <span className="text-white font-semibold">{item.count}</span>
                      </div>
                      <div className="bg-white/10 rounded-full h-2 overflow-hidden">
                        <div 
                          className="bg-gradient-to-r from-blue-500 to-cyan-500 h-full rounded-full"
                          style={{ width: `${item.percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default InspectorDashboard;
