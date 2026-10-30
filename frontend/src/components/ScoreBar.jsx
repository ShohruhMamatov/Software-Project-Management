import { percent } from "../utils";

export default function ScoreBar({ score }) {
  const value = percent(score);
  return (
    <div className="score" title="Model confidence">
      <div
        className="score-track"
        role="meter"
        aria-label="Model confidence"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(score * 100)}
      >
        <span style={{ width: value }} />
      </div>
      <span className="score-value">{value}</span>
    </div>
  );
}
