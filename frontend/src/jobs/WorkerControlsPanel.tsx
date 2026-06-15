import type { WorkerStatus } from "../api/client";
import { ActionRow, ProductSurface } from "../ui/ProductPrimitives";
import { WorkerStatusPanel } from "./WorkerStatusPanel";

type WorkerControlsPanelProps = {
  status: WorkerStatus | null;
  onStart: () => void;
  onStop: () => void;
};

export function WorkerControlsPanel({ status, onStart, onStop }: WorkerControlsPanelProps) {
  return (
    <ProductSurface
      title="Worker"
      eyebrow="Operations"
      description="Control background debug execution and completion writeback hooks."
      className="worker-panel"
    >
      <ActionRow label="Worker actions">
        <button type="button" onClick={onStart}>
          Start worker
        </button>
        <button type="button" onClick={onStop}>
          Stop worker
        </button>
      </ActionRow>
      {status ? <WorkerStatusPanel status={status} /> : null}
    </ProductSurface>
  );
}
