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
      title="后台进程"
      eyebrow="后台操作"
      description="控制后台的调试执行进程与结果回写钩子。"
      className="worker-panel"
    >
      <ActionRow label="后台进程操作">
        <button type="button" aria-label="启动后台进程" onClick={onStart}>
          启动进程
        </button>
        <button type="button" aria-label="停止后台进程" onClick={onStop}>
          停止进程
        </button>
      </ActionRow>
      {status ? <WorkerStatusPanel status={status} /> : null}
    </ProductSurface>
  );
}
