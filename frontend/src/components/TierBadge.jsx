export default function TierBadge({ tier }) {
  const getTierStyles = (tierValue) => {
    const tierLower = tierValue.toLowerCase();
    
    // Status-based styles (for dashboards)
    if (tierLower === 'good' || tierLower === 'active' || tierLower === 'approved') {
      return 'bg-green-500/20 text-green-400 border-green-500/30';
    }
    if (tierLower === 'warning' || tierLower === 'on-call' || tierLower === 'submitted') {
      return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    }
    if (tierLower === 'critical' || tierLower === 'urgent') {
      return 'bg-red-500/20 text-red-400 border-red-500/30';
    }
    if (tierLower === 'off-duty' || tierLower === 'pending') {
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
    
    // Original tier-based styles
    switch (tierLower) {
      case 'high':
      case 'tier1':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'medium':
      case 'tier2':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'low':
      case 'tier3':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
  };

  return (
    <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getTierStyles(tier)}`}>
      {typeof tier === 'string' ? tier.toUpperCase() : tier}
    </span>
  )
}
