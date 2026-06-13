import type { WorkerStatus } from "../api/client";
import { WorkerStatusPanel } from "./WorkerStatusPanel";

type WorkerControlsPanelProps = {
  status: WorkerStatus | null;
  onStart: () => void;
  onStop: () => void;
};

export function WorkerControlsPanel({ status, onStart, onStop }: WorkerControlsPanelProps) {
  return (
    <section>
      <h2>Worker</h2>
      <button type="button" onClick={onStart}>
        Start worker
      </button>
      <button type="button" onClick={onStop}>
        Stop worker
      </button>
      {status ? <WorkerStatusPanel status={status} /> : null}
    </section>
  );
}
