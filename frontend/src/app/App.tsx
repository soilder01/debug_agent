import { useEffect, useState } from "react";

import {
  type BatchDebugJobResponse,
  type CsvImportResponse,
  type DebugCaseDetail,
  type DebugCaseSummary,
  fetchCaseDetail,
  fetchCases,
  fetchEvidenceDetail,
  fetchJobStatus,
  fetchWorkerStatus,
  importCsvCases,
  importJsonlCases,
  type JsonlImportResponse,
  startWorker,
  submitBatchDebugJobs,
  submitDebugJob,
  stopWorker,
  type DebugJobStatus,
  type DebugReport,
  type ExperimentEvidence,
  type SubmittedDebugJob,
  type WorkerStatus
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
  const [batchCaseIds, setBatchCaseIds] = useState("");
  const [batchResult, setBatchResult] = useState<BatchDebugJobResponse | null>(null);
  const [batchJobStatuses, setBatchJobStatuses] = useState<Record<string, DebugJobStatus | SubmittedDebugJob>>({});
  const [importedCases, setImportedCases] = useState<DebugCaseSummary[]>([]);
  const [selectedCaseDetail, setSelectedCaseDetail] = useState<DebugCaseDetail | null>(null);
  const [jsonlCases, setJsonlCases] = useState("");
  const [jsonlImportResult, setJsonlImportResult] = useState<JsonlImportResponse | null>(null);
  const [csvCases, setCsvCases] = useState("");
  const [csvImportResult, setCsvImportResult] = useState<CsvImportResponse | null>(null);
  const [workerStatus, setWorkerStatus] = useState<WorkerStatus | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<ExperimentEvidence | null>(null);
  const [error, setError] = useState<string>("");
  const batchJobs = Object.values(batchJobStatuses);
  const completedBatchJobs = batchJobs.filter((job) => job.status === "completed").length;

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

  useEffect(() => {
    const pendingJobs = batchJobs.filter((job) => job.status !== "completed" && job.status !== "failed");
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
            setError(caught instanceof Error ? caught.message : "Unknown error");
          });
      }
    }, 100);

    return () => window.clearTimeout(timeoutId);
  }, [batchJobStatuses]);

  useEffect(() => {
    if (!workerStatus?.running) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      fetchWorkerStatus()
        .then(setWorkerStatus)
        .catch((caught: unknown) => {
          setError(caught instanceof Error ? caught.message : "Unknown error");
        });
    }, 100);

    return () => window.clearTimeout(timeoutId);
  }, [workerStatus]);

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

  async function loadImportedCases() {
    setError("");
    try {
      const result = await fetchCases();
      setImportedCases(result.cases);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  function useImportedCasesForBatch() {
    setBatchCaseIds(importedCases.map((caseSummary) => caseSummary.case_id).join("\n"));
  }

  async function loadCaseDetail(caseId: string) {
    setError("");
    try {
      setSelectedCaseDetail(await fetchCaseDetail(caseId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function submitBatchJobs() {
    setError("");
    const caseIds = batchCaseIds
      .split(/\s+/)
      .map((caseId) => caseId.trim())
      .filter(Boolean);
    try {
      const result = await submitBatchDebugJobs(caseIds);
      setBatchResult(result);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function startWorkerLoop() {
    setError("");
    try {
      setWorkerStatus(await startWorker());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function importJsonl() {
    setError("");
    try {
      const result = await importJsonlCases(jsonlCases);
      setJsonlImportResult(result);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function importCsv() {
    setError("");
    try {
      const result = await importCsvCases(csvCases);
      setCsvImportResult(result);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function stopWorkerLoop() {
    setError("");
    try {
      setWorkerStatus(await stopWorker());
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
      <section>
        <h2>Worker</h2>
        <button type="button" onClick={startWorkerLoop}>
          Start worker
        </button>
        <button type="button" onClick={stopWorkerLoop}>
          Stop worker
        </button>
        {workerStatus ? (
          <>
            <p>Worker running：{String(workerStatus.running)}</p>
            <p>Worker processed：{workerStatus.processed_count}</p>
            <p>Worker errors：{workerStatus.error_count}</p>
            {workerStatus.last_error ? <p role="alert">Worker error：{workerStatus.last_error}</p> : null}
          </>
        ) : null}
      </section>
      <section>
        <h2>JSONL Import</h2>
        <label htmlFor="jsonl-cases">JSONL cases</label>
        <textarea
          id="jsonl-cases"
          value={jsonlCases}
          onChange={(event) => setJsonlCases(event.target.value)}
        />
        <button type="button" onClick={importJsonl}>
          Import JSONL cases
        </button>
        {jsonlImportResult ? (
          <>
            <p>导入样本：{jsonlImportResult.imported_case_ids.length}</p>
            <p>
              导入拒绝：
              {jsonlImportResult.rejected_lines.length === 0
                ? "无"
                : jsonlImportResult.rejected_lines
                    .map((line) => `${line.line_number}:${line.error_message}`)
                    .join(", ")}
            </p>
          </>
        ) : null}
      </section>
      <section>
        <h2>CSV Import</h2>
        <label htmlFor="csv-cases">CSV cases</label>
        <textarea
          id="csv-cases"
          value={csvCases}
          onChange={(event) => setCsvCases(event.target.value)}
        />
        <button type="button" onClick={importCsv}>
          Import CSV cases
        </button>
        {csvImportResult ? (
          <>
            <p>CSV 导入样本：{csvImportResult.imported_case_ids.length}</p>
            <p>
              CSV 导入拒绝：
              {csvImportResult.rejected_rows.length === 0
                ? "无"
                : csvImportResult.rejected_rows
                    .map((row) => `${row.row_number}:${row.error_message}`)
                    .join(", ")}
            </p>
          </>
        ) : null}
      </section>
      <section>
        <h2>Imported Cases</h2>
        <button type="button" onClick={loadImportedCases}>
          Load imported cases
        </button>
        {importedCases.length > 0 ? (
          <>
            <p>已导入样本：{importedCases.length}</p>
            <button type="button" onClick={useImportedCasesForBatch}>
              Use imported cases for batch
            </button>
            <ul aria-label="Imported case summaries">
              {importedCases.map((caseSummary) => (
                <li key={caseSummary.case_id}>
                  {caseSummary.case_id}｜avg_score {caseSummary.avg_score}｜
                  {caseSummary.debug_status || "未标记"}｜{caseSummary.root_cause || "未归因"}
                  <button type="button" onClick={() => void loadCaseDetail(caseSummary.case_id)}>
                    View case detail {caseSummary.case_id}
                  </button>
                </li>
              ))}
            </ul>
            {selectedCaseDetail ? (
              <section aria-label="Selected case detail">
                <h3>样本详情：{selectedCaseDetail.case_id}</h3>
                <p>图片：{selectedCaseDetail.image_uri}</p>
                <p>Prompt：{selectedCaseDetail.prompt}</p>
                <p>评分标准：{selectedCaseDetail.scoring_standard}</p>
                <ul aria-label="Golden answers">
                  {selectedCaseDetail.golden_answer.answers.map((answer) => (
                    <li key={answer.box_id}>
                      标答 {answer.box_id}：{answer.student_answer}
                    </li>
                  ))}
                </ul>
                <ul aria-label="Predictions">
                  {selectedCaseDetail.predictions.map((prediction) => (
                    <li key={prediction.trial}>
                      预测 trial {prediction.trial}：score {prediction.score}
                    </li>
                  ))}
                </ul>
                <p>人工状态：{selectedCaseDetail.human_notes.debug_status || "未标记"}</p>
                <p>人工根因：{selectedCaseDetail.human_notes.root_cause || "未归因"}</p>
              </section>
            ) : null}
          </>
        ) : null}
      </section>
      <section>
        <h2>Batch Jobs</h2>
        <label htmlFor="batch-case-ids">Batch case ids</label>
        <textarea
          id="batch-case-ids"
          value={batchCaseIds}
          onChange={(event) => setBatchCaseIds(event.target.value)}
        />
        <button type="button" onClick={submitBatchJobs}>
          Submit batch jobs
        </button>
        {batchResult ? (
          <>
            <p>批量创建：{batchResult.jobs.length}</p>
            <p>拒绝：{batchResult.rejected_case_ids.join(", ") || "无"}</p>
            <p>
              批量进度：{completedBatchJobs}/{batchResult.jobs.length}
            </p>
            <button type="button" onClick={startWorkerLoop}>
              Start worker for batch
            </button>
            {batchJobs.length > 0 ? (
              <ul aria-label="Batch job statuses">
                {batchJobs.map((job) => (
                  <li key={job.job_id}>
                    <span>
                      {job.job_id}：{job.status}
                    </span>
                    {job.error_message ? <span> {job.job_id} 错误：{job.error_message}</span> : null}
                  </li>
                ))}
              </ul>
            ) : null}
          </>
        ) : null}
      </section>
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
