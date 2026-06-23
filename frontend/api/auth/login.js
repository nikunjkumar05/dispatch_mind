export default function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.status(200).end();
    return;
  }

  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  const { username, password } = req.body || {};

  if (!username || !password) {
    res.status(400).json({ detail: "Username and password required" });
    return;
  }

  const roles = {
    acp: { name: "ACP Rajesh Kumar", role: "acp", station: "ALL", badge: "ACP-001" },
    si: { name: "SI Priya Sharma", role: "si", station: "Magadi Road", badge: "SI-042" },
    constable: { name: "Constable Arjun Das", role: "constable", station: "Vijayanagar", badge: "PC-1187" },
    scout: { name: "Scout Vikram Singh", role: "scout", station: "Electronic City", badge: "FK-309" },
  };

  const u = username.toLowerCase().trim();
  const user = roles[u] || { name: username, role: "constable", station: "ALL", badge: "GEN-001" };

  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.status(200).json({
    token: `dm-${u}-${Date.now()}`,
    user,
  });
}
