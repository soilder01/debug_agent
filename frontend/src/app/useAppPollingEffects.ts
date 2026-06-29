import type { Dispatch, SetStateAction } from "react";
import { useEffect } from "react";

import {
  fetchDebugBatch,
  fetchJobStatus,
  fetchWorkerStatus,
  type DebugBatchProgress,
  type DebugJobStatus,
  type SubmittedDebugJob,
  type WorkerStatus,
} from "../api/client";

type UseAppPollingEffectsArgs = {
  jobStatus: DebugJobStatus | null;
  submittedJob: SubmittedDebugJob | null;
  batchJobs: Array<DebugJobStatus | SubmittedDebugJob>;
  batchJobStatuses: Record<string, DebugJobStatus | SubmittedDebugJob>;
  workerStatus: WorkerStatus | null;
  activeBatchProgress: DebugBatchProgress | null;
  setError: Dispatch<SetStateAction<string>>;
  setJobStatus: Dispatch<SetStateAction<DebugJobStatus | null>>;
  setBatchJobStatuses: Dispatch<SetStateAction<Record<string, DebugJobStatus | SubmittedDebugJob>>>;
  setWorkerStatus: Dispatch<SetStateAction<WorkerStatus | null>>;
  setActiveBatchProgress: Dispatch<SetStateAction<DebugBatchProgress | null>>;
};

export function useAppPollingEffects({
  jobStatus,
  submittedJob,
  batchJobs,
  batchJobStatuses,
  workerStatus,
  activeBatchProgress,
  setError,
  setJobStatus,
  setBatchJobStatuses,
  setWorkerStatus,
  setActiveBatchProgress,
}: UseAppPollingEffectsArgs) {
  useEffect(() => {
    const currentJob = jobStatus ?? submittedJob;
    if (!currentJob || currentJob.status === "completed" || currentJob.status === "failed") {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      fetchJobStatus(currentJob.job_id)
        .then(setJobStatus)
        .catch((caught: unknown) => {
          setError(caught instanceof Error ? caught.message : "未知错误");
        });
    }, 100);

    return () => window.clearTimeout(timeoutId);
  }, [jobStatus, setError, setJobStatus, submittedJob]);

  useEffect(() => {
    const pendingJobs = batchJobs.filter((job) => {
      if (job.status === "completed" || job.status === "failed") {
        return false;
      }
      return job.status === "running" || workerStatus?.running;
    });
    if (pendingJobs.length === 0) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      for (const job of pendingJobs) {
        fetchJobStatus(job.job_id)
          .then((status) => {
            setBatchJobStatuses((current) => ({ ...current, [status.job_id]: status }));
          })
          .catch((caught: unknown) => {
            setError(caught instanceof Error ? caught.message : "未知错误");
          });
      }
    }, 100);

    return () => window.clearTimeout(timeoutId);
  }, [batchJobStatuses, batchJobs, setBatchJobStatuses, setError, workerStatus?.running]);

  useEffect(() => {
    if (!workerStatus?.running) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      fetchWorkerStatus()
        .then(setWorkerStatus)
        .catch((caught: unknown) => {
          setError(caught instanceof Error ? caught.message : "未知错误");
        });
    }, 100);

    return () => window.clearTimeout(timeoutId);
  }, [setError, setWorkerStatus, workerStatus]);

  useEffect(() => {
    if (!activeBatchProgress || (!workerStatus?.running && activeBatchProgress.batch.status !== "running")) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      fetchDebugBatch(activeBatchProgress.batch.batch_id)
        .then((progress) => {
          setActiveBatchProgress(progress);
          setBatchJobStatuses((current) => ({
            ...current,
            ...Object.fromEntries(progress.recent_jobs.map((job) => [job.job_id, job])),
          }));
        })
        .catch((caught: unknown) => {
          setError(caught instanceof Error ? caught.message : "未知错误");
        });
    }, 250);

    return () => window.clearTimeout(timeoutId);
  }, [
    activeBatchProgress,
    setActiveBatchProgress,
    setBatchJobStatuses,
    setError,
    workerStatus?.running,
  ]);
}
