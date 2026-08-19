import { useState } from "react";
import { Lock, User, Camera, Trophy, AlertCircle, ArrowRight, ShieldCheck } from "lucide-react";
import { API_BASE } from "../utils/api";

export default function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e, directCreds = null) => {
    if (e) e.preventDefault();
    setError("");
    setLoading(true);

    const u = directCreds ? directCreds.username : username;
    const p = directCreds ? directCreds.password : password;

    if (!u || !p) {
      setError("Please enter both username and password");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username: u, password: p }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed");
      }

      // Success
      localStorage.setItem("token", data.token);
      localStorage.setItem("user", JSON.stringify(data));
      onLoginSuccess(data);
    } catch (err) {
      setError(err.message || "Failed to connect to authentication server");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (role) => {
    const creds = {
      acp: { username: "acp", password: "acp" },
      si: { username: "si", password: "si" },
      constable: { username: "constable", password: "constable" },
      scout: { username: "scout", password: "scout" },
    }[role];
    
    setUsername(creds.username);
    setPassword(creds.password);
    handleSubmit(null, creds);
  };

  const quickRoles = [
    { role: "acp", label: "ACP / Commissioner", icon: ShieldCheck, color: "from-[#FF3366] to-[#FF6B35]", desc: "Full command, metrics & simulator" },
    { role: "si", label: "Sub-Inspector", icon: ShieldCheck, color: "from-[#FF6B35] to-[#FFB800]", desc: "Station dispatch & triage" },
    { role: "constable", label: "Beat Constable", icon: ShieldCheck, color: "from-[#00FF88] to-[#047BD5]", desc: "Field officer panel & alerts" },
    { role: "scout", label: "Flipkart Scout", icon: Camera, color: "from-[#2874F0] to-[#F37A20]", desc: "Parking reporter & leaderboards" },
  ];

  return (
    <div className="min-h-screen bg-base grid-bg noise-overlay flex flex-col justify-center items-center p-4 lg:p-8 select-none relative overflow-hidden">
      {/* Background blobs */}
      <div className="absolute top-[-20%] left-[-20%] w-[500px] h-[500px] rounded-full bg-neon-green/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-20%] w-[500px] h-[500px] rounded-full bg-blue-500/10 blur-[120px] pointer-events-none" />

      <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-12 gap-8 items-center relative z-10 animate-in fade-in zoom-in duration-500">
        
        {/* Brand Column */}
        <div className="md:col-span-5 flex flex-col justify-center text-left space-y-6">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-neon-green/10 flex items-center justify-center border border-neon-green/20 shadow-lg shadow-neon-green/10 overflow-hidden">
              <img src="/app_logo.jpeg" alt="DispatchMind" className="w-10 h-10 object-contain" onError={(e) => {
                e.target.style.display = 'none'
              }} />
            </div>
            <div>
              <h1 className="font-heading font-black text-3xl lg:text-4xl text-chalk tracking-tight">
                DispatchMind
              </h1>
              <p className="text-xs text-muted uppercase tracking-[0.2em] font-semibold">
                BTP AI Co-Pilot
              </p>
            </div>
          </div>
          <div className="space-y-4">
            <h2 className="text-xl lg:text-2xl font-bold text-chalk">
              Illegal Parking Enforcement & Economic Congestion Intelligence
            </h2>
            <p className="text-muted text-sm leading-relaxed">
              DispatchMind leverages Bengaluru Traffic Police (BTP) surveillance cameras and crowdsourced Flipkart delivery partner scouts to detect, quantify, and mitigate parking-induced traffic gridlocks in real-time.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted/60 font-mono">
            <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
            Gridlock Hackathon 2.0 Project
          </div>
        </div>

        {/* Login Card Column */}
        <div className="md:col-span-7 flex flex-col space-y-6">
          <div className="glass-card p-6 lg:p-8 rounded-3xl border border-border/80 shadow-2xl relative overflow-hidden">
            <h3 className="text-xl font-bold text-chalk mb-1">Sign In to Dashboard</h3>
            <p className="text-muted text-xs mb-6">Enter your security credentials or select a demo role below.</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="bg-signal-red/10 border border-signal-red/20 text-signal-red text-xs rounded-xl p-3 flex items-center gap-2 animate-in slide-in-from-top duration-300">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-[10px] uppercase tracking-wider text-muted font-semibold block" htmlFor="username">
                  Username
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-muted/50" />
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter username"
                    className="input-glass pl-10 pr-4 py-2.5 text-sm w-full font-medium text-chalk placeholder:text-muted/40"
                    disabled={loading}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] uppercase tracking-wider text-muted font-semibold block" htmlFor="password">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-muted/50" />
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    className="input-glass pl-10 pr-4 py-2.5 text-sm w-full font-medium text-chalk placeholder:text-muted/40"
                    disabled={loading}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 bg-gradient-to-r from-neon-green to-[#00b359] text-black font-bold py-3 rounded-xl hover:scale-[1.01] active:scale-[0.99] transition-all duration-200 text-sm flex items-center justify-center gap-2 shadow-lg shadow-neon-green/20"
              >
                {loading ? (
                  <span className="w-5 h-5 border-2 border-black border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Authenticate Credentials</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border/80"></div>
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-sidebar px-3 text-muted/50 font-mono text-[9px]">Demo Quick Login</span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {quickRoles.map((qr) => {
                const QrIcon = qr.icon;
                return (
                  <button
                    key={qr.role}
                    type="button"
                    onClick={() => handleQuickLogin(qr.role)}
                    disabled={loading}
                    className="text-left p-3 rounded-2xl bg-elevated/40 border border-border/60 hover:border-border hover:bg-elevated/80 transition-all duration-300 group flex items-start gap-3 hover:scale-[1.01]"
                  >
                    <div className={`w-8 h-8 rounded-xl bg-gradient-to-br ${qr.color} flex items-center justify-center text-white shrink-0 group-hover:scale-110 transition-transform`}>
                      <QrIcon className="w-4.5 h-4.5" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-chalk flex items-center gap-1">
                        {qr.label}
                        <ArrowRight className="w-3 h-3 text-muted/0 group-hover:text-chalk group-hover:translate-x-0.5 transition-all opacity-0 group-hover:opacity-100" />
                      </div>
                      <div className="text-[10px] text-muted truncate mt-0.5">{qr.desc}</div>
                    </div>
                  </button>
                );
              })}
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
