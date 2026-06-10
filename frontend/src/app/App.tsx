import { useEffect, useState } from "react";

import {
  fetchEvidenceDetail,
  fetchJobStatus,
  submitDebugJob,
  type DebugJobStatus,
  type DebugReport,
  type ExperimentEvidence,
  type SubmittedDebugJob
} from "../api/client";
import { CaseDetail } from "../cases/CaseDetail";
import { EvidenceDetail } from "../evidence/EvidenceDetail";
import { ExperimentTimeline } from "../experiments/ExperimentTimeline";
import { JobStatusPanel } from "../jobs/JobStatusPanel";
import { ReportPanel } from "../reports/ReportPanel";

export function App() {
  const [report, setReport] = useState<DebugReport | null>(null);
  const [submittedJob, setSubmittedJob] = useState<SubmittedDebugJob | null>(null);
  const [jobStatus, setJobStatus] = useState<DebugJobStatus | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<ExperimentEvidence | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const currentJob = jobStatus ?? submittedJob;
    if (!currentJob || currentJob.status === "completed" || currentJob.status === "failed") {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      fetchJobStatus(currentJob.job_id)
        .then(setJobStatus)
        .catch((caught: unknown) => {
          setError(caught instanceof Error ? caught.message : "Unknown error");
        });
    }, 100);

    return () => window.clearTimeout(timeoutId);
  }, [jobStatus, submittedJob]);

  async function submitJob() {
    setError("");
    try {
      setSubmittedJob(await submitDebugJob("handwrite233"));
      setJobStatus(null);
      setReport(null);
      setSelectedEvidence(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function selectEvidence(evidenceId: string) {
    if (!report) {
      return;
    }
    setError("");
    try {
      setSelectedEvidence(await fetchEvidenceDetail(report.case_id, evidenceId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  return (
    <main>
      <h1>Handwriting OCR Debug Agent</h1>
      <button type="button" onClick={submitJob}>
        Submit debug job
      </button>
      {error ? <p role="alert">{error}</p> : null}
      {submittedJob ? <JobStatusPanel job={jobStatus ?? submittedJob} /> : null}
      {report ? (
        <>
          <CaseDetail jobId={report.job_id} caseId={report.case_id} status={report.status} />
          <ExperimentTimeline
            experiments={report.planned_experiments}
            summary={report.experiment_summary}
            onSelectEvidence={selectEvidence}
          />
          <EvidenceDetail evidence={selectedEvidence} />
          <ReportPanel report={report} />
        </>
      ) : submittedJob ? null : (
        <p>点击按钮运行第一条可验证 debug 闭环。</p>
      )}
    </main>
  );
}
