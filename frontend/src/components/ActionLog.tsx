import type { ReplayEvent } from "../types/game";

interface ActionLogProps {
  events: ReplayEvent[];
}

function amountSuffix(amount?: number): string {
  if (!amount || amount <= 0) {
    return "";
  }
  return ` ${amount}`;
}

export function ActionLog({ events }: ActionLogProps) {
  return (
    <section className="pixel-panel log-panel">
      <header className="panel-header">
        <h3 className="pixel-title-sm">Action Feed</h3>
      </header>

      <ol className="action-feed-list">
        {events.map((event) => (
          <li key={event.id} className={`action-feed-item actor-${event.actor}`}>
            <span className="event-street">{event.street.toUpperCase()}</span>
            <span className="event-body">
              {event.actor}: {event.action}
              {amountSuffix(event.amount)} (pot {event.pot})
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
