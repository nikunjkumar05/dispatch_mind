import { useState, useEffect } from "react"
import AppRoutes from "./app/AppRoutes"
import AppShell from "./layout/AppShell"
import Login from "./pages/Login"

export default function App() {
  const [user, setUser] = useState(null)
  const [role, setRole] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Restore session from localStorage on startup
    const storedUser = localStorage.getItem("user")
    const storedToken = localStorage.getItem("token")
    if (storedUser && storedToken) {
      try {
        const u = JSON.parse(storedUser)
        setUser(u)
        setRole(u.role)
      } catch (e) {
        localStorage.removeItem("user")
        localStorage.removeItem("token")
      }
    }
    setLoading(false)
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-base grid-bg flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-neon-green border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!user) {
    return <Login onLoginSuccess={(u) => {
      setUser(u)
      setRole(u.role)
    }} />
  }

  return (
    <AppShell role={role}>
      <AppRoutes role={role} />
    </AppShell>
  )
}
