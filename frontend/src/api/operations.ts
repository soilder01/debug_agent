import type {
  WorkerStatus,
  ObservabilitySummary
} from "./types";

export async function fetchWorkerStatus(): Promise<WorkerStatus> {
  const response = await fetch("/api/worker/status");
  if (!response.ok) {
    throw new Error(`加载后台进程状态失败：${response.status}`);
  }
  return (await response.json()) as WorkerStatus;
}


export async function fetchObservabilitySummary(): Promise<ObservabilitySummary> {
  const response = await fetch("/api/observability/summary");
  if (!response.ok) {
    throw new Error(`加载监控概览失败：${response.status}`);
  }
  return (await response.json()) as ObservabilitySummary;
}


export async function startWorker(): Promise<WorkerStatus> {
  const response = await fetch("/api/worker/start", { method: "POST" });
  if (!response.ok) {
    throw new Error(`启动后台进程失败：${response.status}`);
  }
  return (await response.json()) as WorkerStatus;
}


export async function stopWorker(): Promise<WorkerStatus> {
  const response = await fetch("/api/worker/stop", { method: "POST" });
  if (!response.ok) {
    throw new Error(`停止后台进程失败：${response.status}`);
  }
  return (await response.json()) as WorkerStatus;
}
