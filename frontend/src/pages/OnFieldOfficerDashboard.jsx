import React, { useState } from 'react';
import { 
  MapPin, Navigation, Camera, Phone, AlertTriangle, CheckCircle,
  Clock, User, FileText, Send, Mic, Image, Video, ChevronRight,
  Bell, Menu, Shield, Wifi, Battery, GPS
} from 'lucide-react';

const OnFieldOfficerDashboard = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('patrol');
  const [reportType, setReportType] = useState('incident');

  const stats = [
    { title: 'Patrol Hours', value: '6.5', change: '+1.2', icon: Clock, color: 'blue' },
    { title: 'Reports Filed', value: '8', change: '+3', icon: FileText, color: 'green' },
    { title: 'Incidents', value: '3', change: '-1', icon: AlertTriangle, color: 'orange' },
    { title: 'Assistance Calls', value: '12', change: '+4', icon: Phone, color: 'purple' },
  ];

  const activeTasks = [
    { id: 1, type: 'Patrol', location: 'Sector 7 - Main Road', status: 'in-progress', time: 'Started 30 min ago' },
    { id: 2, type: 'Verification', location: 'Shop No. 42, Market Area', status: 'pending', time: 'Due in 1 hour' },
    { id: 3, type: 'Response', location: 'Call from Resident - Block C', status: 'urgent', time: 'Received 5 min ago' },
  ];

  const recentReports = [
    { id: 1, type: 'Traffic Violation', location: 'Highway Junction', time: '1 hour ago', status: 'submitted' },
    { id: 2, type: 'Suspicious Activity', location: 'Park Entrance', time: '2 hours ago', status: 'submitted' },
    { id: 3, type: 'Document Check', location: 'Commercial Complex', time: '3 hours ago', status: 'approved' },
  ];

  const quickActions = [
    { icon: Camera, label: 'Photo Report', color: 'from-blue-500 to-cyan-500' },
    { icon: Mic, label: 'Voice Note', color: 'from-purple-500 to-pink-500' },
    { icon: Video, label: 'Video Record', color: 'from-red-500 to-orange-500' },
    { icon: Phone, label: 'Emergency Call', color: 'from-green-500 to-emerald-500' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-emerald-900 to-slate-900">
      {/* Header */}
      <header className="bg-white/10 backdrop-blur-md border-b border-white/20 sticky top-0 z-50">
        <div className="px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              <Menu className="w-6 h-6 text-white" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-white">Field Officer</h1>
              <p className="text-emerald-200 text-xs">On-Duty Mode</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-2 bg-white/10 px-3 py-1.5 rounded-lg">
              <GPS className="w-4 h-4 text-emerald-400" />
              <span className="text-white text-sm">Tracking Active</span>
            </div>
            <button className="relative p-2 hover:bg-white/10 rounded-lg transition-colors">
              <Bell className="w-5 h-5 text-white" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>
            <div className="flex items-center gap-2 pl-3 border-l border-white/20">
              <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="hidden sm:block">
                <p className="text-white font-semibold text-sm">Constable Yadav</p>
                <p className="text-emerald-300 text-xs">Badge #4521</p>
              </div>
            </div>
          </div>
        </div>
        
        {/* Status Bar */}
        <div className="px-4 py-2 bg-black/20 flex items-center justify-between text-xs">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 text-emerald-400">
              <Wifi className="w-4 h-4" />
              <span>Online</span>
            </div>
            <div className="flex items-center gap-1 text-white">
              <Battery className="w-4 h-4" />
              <span>78%</span>
            </div>
          </div>
          <div className="text-emerald-200">
            Shift: 08:00 AM - 04:00 PM
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Mobile Sidebar Overlay */}
        {sidebarOpen && (
          <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)}></div>
        )}

        {/* Sidebar */}
        {sidebarOpen && (
          <aside className="fixed lg:relative w-64 bg-black/20 backdrop-blur-md min-h-[calc(100vh-120px)] border-r border-white/10 p-4 z-50">
            <nav className="space-y-1">
              {[
                { icon: Navigation, label: 'Patrol Route', active: true },
                { icon: FileText, label: 'File Report' },
                { icon: AlertTriangle, label: 'Emergency' },
                { icon: CheckCircle, label: 'Task List' },
                { icon: MapPin, label: 'Location Share' },
                { icon: Phone, label: 'Contact Station' },
              ].map((item, idx) => (
                <button
                  key={idx}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                    item.active 
                      ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-500/30' 
                      : 'text-emerald-200 hover:bg-white/10'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                  {item.active && <ChevronRight className="w-4 h-4 ml-auto" />}
                </button>
              ))}
            </nav>

            <div className="mt-6 pt-6 border-t border-white/10">
              <h3 className="text-emerald-300 text-xs font-semibold mb-3">Quick Report Types</h3>
              <div className="space-y-2">
                {['Incident', 'Traffic', 'Verification', 'Community'].map((type) => (
                  <button
                    key={type}
                    onClick={() => setReportType(type.toLowerCase())}
                    className={`w-full px-4 py-2 rounded-lg text-left text-sm transition-all ${
                      reportType === type.toLowerCase()
                        ? 'bg-emerald-600 text-white'
                        : 'bg-white/5 text-emerald-200 hover:bg-white/10'
                    }`}
                  >
                    {type} Report
                  </button>
                ))}
              </div>
            </div>
          </aside>
        )}

        {/* Main Content */}
        <main className="flex-1 p-4">
          {/* Stats Grid - Compact for mobile */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
            {stats.map((stat, idx) => (
              <div key={idx} className="bg-white/10 backdrop-blur-md rounded-xl border border-white/20 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <stat.icon className="w-4 h-4 text-emerald-400" />
                  <span className="text-emerald-200 text-xs">{stat.title}</span>
                </div>
                <p className="text-white text-xl font-bold">{stat.value}</p>
                <p className={`text-xs ${stat.change.startsWith('+') ? 'text-green-400' : 'text-red-400'}`}>
                  {stat.change}
                </p>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
            {['patrol', 'reports', 'tasks'].map((tab) => (
              <button 
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-lg font-medium text-sm whitespace-nowrap transition-all ${
                  activeTab === tab 
                    ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white' 
                    : 'bg-white/10 text-emerald-200 hover:bg-white/20'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {/* Patrol Tab */}
          {activeTab === 'patrol' && (
            <div className="space-y-4">
              {/* Map Placeholder */}
              <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 h-64 flex items-center justify-center relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-emerald-900/50 to-teal-900/50"></div>
                <div className="text-center z-10">
                  <MapPin className="w-12 h-12 text-emerald-400 mx-auto mb-2" />
                  <p className="text-white font-semibold">Live Location Tracking</p>
                  <p className="text-emerald-200 text-sm">Sector 7, Main Road</p>
                </div>
                {/* Simulated map markers */}
                <div className="absolute top-1/4 left-1/4 w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
                <div className="absolute top-1/2 left-1/2 w-3 h-3 bg-emerald-500 rounded-full animate-pulse"></div>
                <div className="absolute bottom-1/3 right-1/4 w-3 h-3 bg-orange-500 rounded-full animate-pulse"></div>
              </div>

              {/* Active Tasks */}
              <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-4">
                <h2 className="text-lg font-bold text-white mb-4">Active Tasks</h2>
                <div className="space-y-3">
                  {activeTasks.map((task) => (
                    <div key={task.id} className="bg-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Navigation className="w-4 h-4 text-emerald-400" />
                          <span className="text-white font-semibold">{task.type}</span>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          task.status === 'urgent' ? 'bg-red-500 text-white' :
                          task.status === 'in-progress' ? 'bg-blue-500 text-white' :
                          'bg-orange-500 text-white'
                        }`}>
                          {task.status.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-emerald-200 text-sm mb-2">{task.location}</p>
                      <p className="text-emerald-300 text-xs">{task.time}</p>
                      <div className="flex gap-2 mt-3">
                        <button className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded-lg text-sm font-medium transition-all">
                          Start
                        </button>
                        <button className="flex-1 bg-white/10 hover:bg-white/20 text-white py-2 rounded-lg text-sm font-medium transition-all">
                          Details
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quick Actions */}
              <div className="grid grid-cols-2 gap-3">
                {quickActions.map((action, idx) => (
                  <button 
                    key={idx}
                    className={`bg-gradient-to-br ${action.color} p-4 rounded-xl hover:opacity-90 transition-all flex flex-col items-center gap-2`}
                  >
                    <action.icon className="w-6 h-6 text-white" />
                    <span className="text-white text-sm font-medium">{action.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Reports Tab */}
          {activeTab === 'reports' && (
            <div className="space-y-4">
              {/* New Report Button */}
              <button className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white py-4 rounded-xl font-semibold transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/30">
                <FileText className="w-5 h-5" />
                File New Report
              </button>

              {/* Recent Reports */}
              <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-4">
                <h2 className="text-lg font-bold text-white mb-4">Recent Reports</h2>
                <div className="space-y-3">
                  {recentReports.map((report) => (
                    <div key={report.id} className="bg-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="text-white font-semibold">{report.type}</h3>
                          <p className="text-emerald-200 text-sm">{report.location}</p>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${
                          report.status === 'approved' ? 'bg-green-500/20 text-green-400' :
                          'bg-blue-500/20 text-blue-400'
                        }`}>
                          {report.status.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-emerald-300 text-xs">{report.time}</p>
                      <div className="flex gap-2 mt-3">
                        <button className="flex-1 bg-white/10 hover:bg-white/20 text-white py-2 rounded-lg text-sm font-medium transition-all">
                          View
                        </button>
                        <button className="flex-1 bg-white/10 hover:bg-white/20 text-white py-2 rounded-lg text-sm font-medium transition-all">
                          Share
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Tasks Tab */}
          {activeTab === 'tasks' && (
            <div className="space-y-4">
              <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-4">
                <h2 className="text-lg font-bold text-white mb-4">Today's Checklist</h2>
                <div className="space-y-3">
                  {[
                    { task: 'Morning Patrol - Sector 7', completed: true },
                    { task: 'Verify 5 Shop Licenses', completed: false },
                    { task: 'Traffic Control at School Zone', completed: false },
                    { task: 'Community Meeting - Block C', completed: false },
                    { task: 'Submit Daily Report', completed: false },
                  ].map((item, idx) => (
                    <div key={idx} className="flex items-center gap-3 bg-white/5 rounded-xl p-4 hover:bg-white/10 transition-colors">
                      <button className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                        item.completed 
                          ? 'bg-green-500 border-green-500' 
                          : 'border-emerald-400 hover:border-emerald-300'
                      }`}>
                        {item.completed && <CheckCircle className="w-4 h-4 text-white" />}
                      </button>
                      <span className={`text-sm ${
                        item.completed ? 'text-emerald-300 line-through' : 'text-white'
                      }`}>
                        {item.task}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Emergency Contact */}
              <div className="bg-gradient-to-r from-red-900/50 to-orange-900/50 backdrop-blur-md rounded-2xl border border-red-500/30 p-4">
                <div className="flex items-center gap-3 mb-3">
                  <AlertTriangle className="w-6 h-6 text-red-400" />
                  <h2 className="text-lg font-bold text-white">Emergency Contacts</h2>
                </div>
                <div className="space-y-2">
                  <button className="w-full bg-red-600 hover:bg-red-700 text-white py-3 rounded-lg font-semibold transition-all flex items-center justify-center gap-2">
                    <Phone className="w-5 h-5" />
                    Call Control Room
                  </button>
                  <button className="w-full bg-white/10 hover:bg-white/20 text-white py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2">
                    <Send className="w-5 h-5" />
                    Send SOS Alert
                  </button>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Bottom Navigation - Mobile Only */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-black/80 backdrop-blur-md border-t border-white/20 px-4 py-2 z-50">
        <div className="flex items-center justify-around">
          {[
            { icon: Navigation, label: 'Patrol', active: activeTab === 'patrol' },
            { icon: FileText, label: 'Reports', active: activeTab === 'reports' },
            { icon: CheckCircle, label: 'Tasks', active: activeTab === 'tasks' },
            { icon: AlertTriangle, label: 'Emergency', active: false },
          ].map((item, idx) => (
            <button
              key={idx}
              onClick={() => item.label !== 'Emergency' && setActiveTab(item.label.toLowerCase())}
              className={`flex flex-col items-center gap-1 p-2 rounded-lg transition-all ${
                item.active 
                  ? 'text-emerald-400' 
                  : 'text-emerald-200/60 hover:text-emerald-200'
              } ${item.label === 'Emergency' ? 'text-red-400' : ''}`}
            >
              <item.icon className="w-6 h-6" />
              <span className="text-xs">{item.label}</span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
};

export default OnFieldOfficerDashboard;
