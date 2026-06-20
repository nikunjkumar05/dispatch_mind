export default function TierBadge({ tier }) {
  return (
    <span className={`tier-badge ${tier}`}>
      {tier}
    </span>
  )
}
