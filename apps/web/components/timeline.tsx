import { StatusBadge } from "./status-badge";

type TimelineEvent = {
  id: number;
  eventType: string;
  fromStatus: string | null;
  toStatus: string;
  message: string;
  createdAt: string;
};

export function Timeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) return <p className="empty-inline">No lifecycle events recorded.</p>;
  return (
    <ol className="timeline">
      {events.map((event) => (
        <li className="timeline-item" key={event.id}>
          <span className="timeline-marker" aria-hidden="true" />
          <div className="timeline-body">
            <div className="timeline-heading">
              <strong>{event.eventType.replaceAll("_", " ")}</strong>
              <time dateTime={event.createdAt}>{new Date(event.createdAt).toLocaleString()}</time>
            </div>
            <p>{event.message}</p>
            <div className="timeline-meta">
              {event.fromStatus && <span>{event.fromStatus} to</span>}
              <StatusBadge status={event.toStatus} />
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
