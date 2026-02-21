import { memo, useMemo } from "react";
import type { ReplayEvent } from "../types/game";

interface ActionLogProps {
  events: ReplayEvent[];
}

const LIVE_EVENT_LIMIT = 80;

function amountSuffix(amount?: number): string {
  if (!amount || amount <= 0) {
    return "";
  }
  return ` ${amount}`;
}

export const ActionLog = memo(function ActionLog({ events }: ActionLogProps) {
  const visibleEvents = useMemo(() => events.slice(-LIVE_EVENT_LIMIT), [events]);

  return (
    <section className="pixel-panel log-panel">
      <header className="panel-header">
        <h3 className="pixel-title-sm">Action Feed</h3>
      </header>

      <ol className="action-feed-list">
        {visibleEvents.map((event) => (
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
});
