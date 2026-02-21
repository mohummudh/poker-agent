import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { UIEvent } from "react";
import type { ReplayEvent } from "../types/game";

interface ActionLogProps {
  events: ReplayEvent[];
}

const ROW_HEIGHT = 64;
const OVERSCAN_ROWS = 4;

function amountSuffix(amount?: number): string {
  if (!amount || amount <= 0) {
    return "";
  }
  return ` ${amount}`;
}

export const ActionLog = memo(function ActionLog({ events }: ActionLogProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(270);

  const updateViewportHeight = useCallback(() => {
    if (!scrollRef.current) {
      return;
    }
    setViewportHeight(Math.max(1, scrollRef.current.clientHeight));
  }, []);

  useEffect(() => {
    updateViewportHeight();
    window.addEventListener("resize", updateViewportHeight);
    return () => {
      window.removeEventListener("resize", updateViewportHeight);
    };
  }, [updateViewportHeight]);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) {
      return;
    }
    const distanceFromBottom = node.scrollHeight - (node.scrollTop + node.clientHeight);
    if (distanceFromBottom <= ROW_HEIGHT * 2) {
      node.scrollTop = node.scrollHeight;
      setScrollTop(node.scrollTop);
    }
  }, [events.length]);

  const onScroll = useCallback((event: UIEvent<HTMLDivElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  const { startIndex, endIndex, totalHeight } = useMemo(() => {
    const totalRows = events.length;
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN_ROWS);
    const visibleCount = Math.ceil(viewportHeight / ROW_HEIGHT) + OVERSCAN_ROWS * 2;
    const end = Math.min(totalRows, start + visibleCount);
    return {
      startIndex: start,
      endIndex: end,
      totalHeight: totalRows * ROW_HEIGHT
    };
  }, [events.length, scrollTop, viewportHeight]);

  const visibleEvents = useMemo(() => events.slice(startIndex, endIndex), [endIndex, events, startIndex]);

  return (
    <section className="pixel-panel log-panel">
      <header className="panel-header">
        <h3 className="pixel-title-sm">Action Feed</h3>
      </header>

      <div className="action-feed-scroll" onScroll={onScroll} ref={scrollRef}>
        <ol className="action-feed-list" style={{ height: totalHeight }}>
          {visibleEvents.map((event, index) => {
            const absoluteIndex = startIndex + index;
            return (
              <li
                key={event.id}
                className={`action-feed-item actor-${event.actor}`}
                style={{ transform: `translateY(${absoluteIndex * ROW_HEIGHT}px)` }}
              >
                <span className="event-street">{event.street.toUpperCase()}</span>
                <span className="event-body">
                  {event.actor}: {event.action}
                  {amountSuffix(event.amount)} (pot {event.pot})
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
});
