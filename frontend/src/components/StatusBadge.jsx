const LABELS = { pending: "Pending", confirmed: "Confirmed", dismissed: "Dismissed" };

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{LABELS[status]}</span>;
}
