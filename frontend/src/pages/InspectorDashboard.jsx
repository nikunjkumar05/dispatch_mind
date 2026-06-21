import { useState, useEffect } from 'react';
import { FileText, Clock, CircleAlert as AlertCircle, CircleCheck as CheckCircle, Circle as XCircle, ChartBar as BarChart2, Users, MapPin, RefreshCw, Eye, ChevronRight, TriangleAlert as AlertTriangle, Car, Truck, Volume2, Zap, TrendingUp } from 'lucide-react';

export default function InspectorDashboard() {
  const [priorityQueue, setPriorityQueue] = useState(null)
  const [repeatOffenders, setRepeatOffenders] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('escalations')

  useEffect(() => {
    Promise.all([
      fetch('/api/priority-queue/ALL?top_n=10').then(r => r.json()).catch(() => null),
      fetch('/api/repeat-offenders?min_violations=3').then(r => r.json()).catch(() => null),
    ]).then(([pq, ro]) => {
      setPriorityQueue(pq)
      setRepeatOffenders(ro)
      setLoading(false)
    })
  }, [])

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-32 bg-elevated rounded-xl animate-pulse" />
        <div className="grid grid-cols-3 gap-4">
          {[1,2,3].map(i => <div key={i} className="h-64 bg-elevated rounded-xl animate-pulse" />)}
        </div>
      </div>
    )
  }

  const cards = priorityQueue?.cards || []
  const offenders = repeatOffenders?.offenders || []

  const escalations = cards.filter(c => c.tier === 'CRITICAL' || c.tier === 'HIGH')
  const pendingReview = cards.filter(c => c.tier === 'MEDIUM')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-chalk flex items-center gap-2">
            <Users className="w-6 h-6 text-accent" />
            SI Inspector Dashboard
          </h1>
          <p className="text-muted text-sm mt-1">
            Escalation queue, evidence approval, and repeat offenders
          </p>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="flex items-center gap-2 px-3 py-1.5 bg-elevated border border-white/[0.08] rounded-lg text-sm text-muted hover:text-chalk transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-signal-red/10 border border-signal-red/20">
          <p className="text-xs text-signal-red font-bold uppercase tracking-wider">Escalations</p>
          <p className="text-2xl font-bold text-chalk mt-1">{escalations.length}</p>
        </div>
        <div className="p-4 rounded-xl bg-signal-amber/10 border border-signal-amber/20">
          <p className="text-xs text-signal-amber font-bold uppercase tracking-wider">Pending Review</p>
          <p className="text-2xl font-bold text-chalk mt-1">{pendingReview.length}</p>
        </div>
        <div className="p-4 rounded-xl bg-elevated border border-white/[0.06]">
          <p className="text-xs text-muted font-bold uppercase tracking-wider">Repeat Offenders</p>
          <p className="text-2xl font-bold text-chalk mt-1">{offenders.length}</p>
        </div>
        <div className="p-4 rounded-xl bg-signal-emerald/10 border border-signal-emerald/20">
          <p className="text-xs text-signal-emerald font-bold uppercase tracking-wider">Evidence Approved</p>
          <p className="text-2xl font-bold text-chalk mt-1">23</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-white/[0.06] pb-2">
        {[
          { key: 'escalations', label: 'Escalation Queue', icon: AlertTriangle },
          { key: 'evidence', label: 'Evidence Approval', icon: FileText },
          { key: 'offenders', label: 'Repeat Offenders', icon: Car },
          { key: 'performance', label: 'Officer Performance', icon: TrendingUp },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'bg-accent/10 text-accent border border-accent/20'
                : 'text-muted hover:text-chalk hover:bg-elevated/50'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'escalations' && (
        <div className="space-y-3">
          {escalations.length === 0 ? (
            <div className="card border border-white/[0.06] text-center py-12">
              <CheckCircle className="w-10 h-10 text-signal-emerald mx-auto mb-3" />
              <p className="text-chalk font-medium">No escalations pending</p>
              <p className="text-sm text-muted mt-1">All critical violations addressed</p>
            </div>
          ) : (
            escalations.map((card, idx) => (
              <div
                key={idx}
                className="card border border-white/[0.06] hover:border-signal-red/20 transition-colors"
              >
                <div className="flex items-center gap-4">
                  {/* Rank */}
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center shrink-0 ${
                    card.tier === 'CRITICAL' ? 'bg-signal-red/20' : 'bg-tier-high/20'
                  }`}>
                    <span className={`font-mono text-xl font-bold ${
                      card.tier === 'CRITICAL' ? 'text-signal-red' : 'text-tier-high'
                    }`}>
                      {card.rank}
                    </span>
                  </div>

                  {/* Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <MapPin className="w-3.5 h-3.5 text-muted" />
                      <span className="text-sm font-medium text-chalk">{card.junction}</span>
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-signal-red/10 text-signal-red">
                        {card.tier}
                      </span>
                    </div>
                    <p className="text-xs text-muted truncate">{card.explanation}</p>
                  </div>

                  {/* Metrics */}
                  <div className="flex items-center gap-6 shrink-0">
                    <div className="text-right">
                      <p className="text-xs text-muted">Total Delay</p>
                      <p className="font-mono text-lg font-bold text-chalk">{card.total_delay}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-muted">Violations</p>
                      <p className="font-mono text-lg font-bold text-chalk">{card.violation_count}</p>
                    </div>
                    <button className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/80 transition-colors">
                      <Eye className="w-4 h-4" />
                      Review
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'evidence' && (
        <div className="card border border-white/[0.06]">
          <div className="p-6 border-b border-white/[0.06]">
            <h3 className="text-sm font-bold text-chalk">Evidence Packets Pending Approval</h3>
            <p className="text-xs text-muted mt-1">Court-ready challans with SHA256 hash verification</p>
          </div>

          <div className="p-6">
            <div className="space-y-3">
              {[
                { id: 'CL-2024-001', junction: 'BTP044', vehicle: 'KA-01-AB-1234', status: 'pending', time: '2 hrs ago' },
                { id: 'CL-2024-002', junction: 'BTP067', vehicle: 'KA-02-CD-5678', status: 'pending', time: '3 hrs ago' },
                { id: 'CL-2024-003', junction: 'BTP089', vehicle: 'KA-03-EF-9012', status: 'approved', time: '5 hrs ago' },
              ].map((evidence, idx) => (
                <div key={idx} className="flex items-center justify-between p-4 rounded-lg bg-elevated/30 border border-white/[0.04] hover:border-accent/20 transition-colors">
                  <div className="flex items-center gap-4">
                    <FileText className="w-5 h-5 text-accent" />
                    <div>
                      <p className="text-sm font-medium text-chalk">{evidence.id} — {evidence.junction}</p>
                      <p className="text-xs text-muted">{evidence.vehicle} • {evidence.time}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {evidence.status === 'pending' ? (
                      <>
                        <button className="px-3 py-1.5 bg-signal-emerald text-white text-xs font-bold rounded hover:bg-signal-emerald/80 transition-colors">
                          Approve
                        </button>
                        <button className="px-3 py-1.5 bg-signal-red text-white text-xs font-bold rounded hover:bg-signal-red/80 transition-colors">
                          Reject
                        </button>
                      </>
                    ) : (
                      <span className="px-2 py-1 bg-signal-emerald/10 text-signal-emerald text-xs font-bold rounded">
                        APPROVED
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'offenders' && (
        <div className="card border border-white/[0.06]">
          <div className="p-6 border-b border-white/[0.06]">
            <h3 className="text-sm font-bold text-chalk">Repeat Offenders</h3>
            <p className="text-xs text-muted mt-1">
              Vehicles with 3+ high-impact violations — {offenders.length} identified
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-elevated/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs text-muted font-bold uppercase tracking-wider">Vehicle</th>
                  <th className="px-4 py-3 text-left text-xs text-muted font-bold uppercase tracking-wider">Violations</th>
                  <th className="px-4 py-3 text-left text-xs text-muted font-bold uppercase tracking-wider">Stations</th>
                  <th className="px-4 py-3 text-left text-xs text-muted font-bold uppercase tracking-wider">Total Delay</th>
                  <th className="px-4 py-3 text-left text-xs text-muted font-bold uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {offenders.slice(0, 10).map((offender, idx) => (
                  <tr key={idx} className="border-t border-white/[0.04] hover:bg-elevated/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Car className="w-4 h-4 text-muted" />
                        <span className="text-sm font-medium text-chalk">{offender.vehicle_number || 'N/A'}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-signal-red/10 text-signal-red text-xs font-bold rounded">
                        {offender.violation_count}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted">{offender.stations}</td>
                    <td className="px-4 py-3 font-mono text-sm text-chalk">{offender.total_delay?.toFixed(1)}</td>
                    <td className="px-4 py-3">
                      <button className="p-2 hover:bg-accent/10 rounded-lg transition-colors text-accent">
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'performance' && (
        <div className="grid grid-cols-2 gap-4">
          {[
            { name: 'Officer Kumar', cleared: 23, avg_response: '4.2 min', rating: 'Excellent' },
            { name: 'Officer Singh', cleared: 18, avg_response: '5.1 min', rating: 'Good' },
            { name: 'Officer Patel', cleared: 15, avg_response: '6.3 min', rating: 'Good' },
            { name: 'Officer Sharma', cleared: 12, avg_response: '7.2 min', rating: 'Average' },
          ].map((officer, idx) => (
            <div key={idx} className="card border border-white/[0.06]">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center">
                    <Users className="w-5 h-5 text-accent" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-chalk">{officer.name}</p>
                    <p className="text-xs text-muted">{officer.rating}</p>
                  </div>
                </div>
                <span className={`px-2 py-1 text-[10px] font-bold rounded ${
                  officer.rating === 'Excellent' ? 'bg-signal-emerald/10 text-signal-emerald' :
                  officer.rating === 'Good' ? 'bg-signal-amber/10 text-signal-amber' :
                  'bg-elevated text-muted'
                }`}>
                  {officer.rating.toUpperCase()}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-elevated/30">
                  <p className="text-xs text-muted">Vehicles Cleared</p>
                  <p className="text-lg font-bold text-chalk">{officer.cleared}</p>
                </div>
                <div className="p-3 rounded-lg bg-elevated/30">
                  <p className="text-xs text-muted">Avg Response</p>
                  <p className="text-lg font-bold text-chalk">{officer.avg_response}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
