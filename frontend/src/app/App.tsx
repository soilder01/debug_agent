import { useEffect, useState } from "react";

import {
  type BatchDebugJobResponse,
  type CsvImportResponse,
  type DebugCaseDetail,
  type DebugCaseSummary,
  fetchCaseDetail,
  fetchCases,
  fetchDebugJobs,
  fetchEvidenceDetail,
  fetchJobEvidenceDetail,
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

const jobListLimit = 50;
const caseListLimit = 50;

export function App() {
  const [report, setReport] = useState<DebugReport | null>(null);
  const [submittedJob, setSubmittedJob] = useState<SubmittedDebugJob | null>(null);
  const [jobStatus, setJobStatus] = useState<DebugJobStatus | null>(null);
  const [batchCaseIds, setBatchCaseIds] = useState("");
  const [batchResult, setBatchResult] = useState<BatchDebugJobResponse | null>(null);
  const [jobListSummaryLabel, setJobListSummaryLabel] = useState("批量创建");
  const [jobListTotalCount, setJobListTotalCount] = useState<number | null>(null);
  const [batchJobStatuses, setBatchJobStatuses] = useState<Record<string, DebugJobStatus | SubmittedDebugJob>>({});
  const [importedCases, setImportedCases] = useState<DebugCaseSummary[]>([]);
  const [selectedCaseDetail, setSelectedCaseDetail] = useState<DebugCaseDetail | null>(null);
  const [jsonlCases, setJsonlCases] = useState("");
  const [jsonlImportResult, setJsonlImportResult] = useState<JsonlImportResponse | null>(null);
  const [csvCases, setCsvCases] = useState("");
  const [csvImportResult, setCsvImportResult] = useState<CsvImportResponse | null>(null);
  const [workerStatus, setWorkerStatus] = useState<WorkerStatus | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<ExperimentEvidence | null>(null);
  const [importedCaseTotalCount, setImportedCaseTotalCount] = useState(0);
  const [importedCaseFilteredCount, setImportedCaseFilteredCount] = useState<number | null>(null);
  const [activeImportedCaseHasRegions, setActiveImportedCaseHasRegions] = useState(false);
  const [activeJobStatusFilter, setActiveJobStatusFilter] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string>("");
  const batchJobs = Object.values(batchJobStatuses);
  const completedBatchJobs = batchJobs.filter((job) => job.status === "completed").length;
  const loadedJobCount = batchResult?.jobs.length ?? 0;
  const unloadedJobCount = Math.max(0, (jobListTotalCount ?? loadedJobCount) - loadedJobCount);
  const visibleImportedCases = importedCases;
  const effectiveImportedCaseCount = importedCaseFilteredCount ?? importedCaseTotalCount;
  const unloadedCaseCount = Math.max(0, effectiveImportedCaseCount - visibleImportedCases.length);

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

  async function loadImportedCases(hasRegions = false) {
    setError("");
    try {
      const result = await fetchCases(hasRegions, caseListLimit);
      setImportedCases(result.cases);
      setImportedCaseTotalCount(result.total_count);
      setImportedCaseFilteredCount(result.filtered_count ?? result.total_count);
      setActiveImportedCaseHasRegions(hasRegions);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function loadMoreImportedCases() {
    setError("");
    try {
      const result = await fetchCases(activeImportedCaseHasRegions, caseListLimit, importedCases.length);
      setImportedCases((current) => [...current, ...result.cases]);
      setImportedCaseTotalCount(result.total_count);
      setImportedCaseFilteredCount(result.filtered_count ?? result.total_count);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  function useImportedCasesForBatch() {
    setBatchCaseIds(visibleImportedCases.map((caseSummary) => caseSummary.case_id).join("\n"));
  }

  async function loadCaseDetail(caseId: string) {
    setError("");
    try {
      setSelectedCaseDetail(await fetchCaseDetail(caseId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function submitSelectedCaseJob(caseId: string) {
    setError("");
    try {
      setSubmittedJob(await submitDebugJob(caseId));
      setJobStatus(null);
      setReport(null);
      setSelectedEvidence(null);
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
      setJobListSummaryLabel("批量创建");
      setJobListTotalCount(result.jobs.length);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function loadDebugJobs(status?: string) {
    setError("");
    try {
      const result = await fetchDebugJobs(status, jobListLimit);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setJobListSummaryLabel(status === "failed" ? "失败任务" : "队列任务");
      setJobListTotalCount(result.total_count);
      setActiveJobStatusFilter(status);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function loadMoreDebugJobs() {
    setError("");
    try {
      const result = await fetchDebugJobs(activeJobStatusFilter, jobListLimit, batchJobs.length);
      const jobs = [...batchJobs, ...result.jobs];
      setBatchResult({ jobs, rejected_case_ids: batchResult?.rejected_case_ids ?? [] });
      setJobListTotalCount(result.total_count);
      setBatchJobStatuses(Object.fromEntries(jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  function openBatchJob(job: DebugJobStatus | SubmittedDebugJob) {
    setSubmittedJob(job);
    setJobStatus("evidence_error_counts" in job ? job : null);
    setReport(null);
    setSelectedEvidence(null);
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
      setJobListSummaryLabel("批量创建");
      setJobListTotalCount(result.jobs.length);
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
      setJobListSummaryLabel("批量创建");
      setJobListTotalCount(result.jobs.length);
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

  async function selectJobEvidence(evidenceId: string) {
    const currentJob = jobStatus ?? submittedJob;
    if (!currentJob) {
      return;
    }
    setError("");
    try {
      setSelectedEvidence(await fetchJobEvidenceDetail(currentJob.job_id, evidenceId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function selectBatchJobEvidence(jobId: string, evidenceId: string) {
    setError("");
    try {
      setSelectedEvidence(await fetchJobEvidenceDetail(jobId, evidenceId));
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
        <button type="button" onClick={() => void loadImportedCases(false)}>
          Load imported cases
        </button>
        {importedCases.length > 0 ? (
          <>
            <p>已导入样本：{importedCaseTotalCount}</p>
            <p>
              已显示样本：{visibleImportedCases.length}/{effectiveImportedCaseCount}
            </p>
            <p>未加载样本：{unloadedCaseCount}</p>
            <button type="button" onClick={() => void loadImportedCases(true)}>
              Only cases with regions
            </button>
            <button type="button" onClick={() => void loadImportedCases(false)}>
              Show all imported cases
            </button>
            {unloadedCaseCount > 0 ? (
              <button type="button" onClick={() => void loadMoreImportedCases()}>
                Load more imported cases
              </button>
            ) : null}
            <button type="button" onClick={useImportedCasesForBatch}>
              Use imported cases for batch
            </button>
            <ul aria-label="Imported case summaries">
              {visibleImportedCases.map((caseSummary) => (
                <li key={caseSummary.case_id}>
                  {caseSummary.case_id}｜avg_score {caseSummary.avg_score}｜regions {caseSummary.box_region_count ?? 0}｜
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
                <button type="button" onClick={() => void submitSelectedCaseJob(selectedCaseDetail.case_id)}>
                  Create debug job for {selectedCaseDetail.case_id}
                </button>
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
                {(selectedCaseDetail.box_regions ?? []).length > 0 ? (
                  <ul aria-label="Box regions">
                    {selectedCaseDetail.box_regions?.map((region) => (
                      <li key={region.box_id}>
                        区域 {region.box_id}：x={region.x}, y={region.y}, width={region.width}, height=
                        {region.height}, unit={region.unit}, label={region.label || "无"}
                      </li>
                    ))}
                  </ul>
                ) : null}
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
        <button type="button" onClick={() => void loadDebugJobs()}>
          Load debug jobs
        </button>
        <button type="button" onClick={() => void loadDebugJobs("failed")}>
          Load failed jobs
        </button>
        {batchResult ? (
          <>
            <p>{jobListSummaryLabel}：{batchResult.jobs.length}</p>
            <p>总任务：{jobListTotalCount ?? batchResult.jobs.length}</p>
            <p>未加载：{unloadedJobCount}</p>
            <p>拒绝：{batchResult.rejected_case_ids.join(", ") || "无"}</p>
            <p>
              批量进度：{completedBatchJobs}/{batchResult.jobs.length}
            </p>
            <button type="button" onClick={startWorkerLoop}>
              Start worker for batch
            </button>
            {unloadedJobCount > 0 ? (
              <button type="button" onClick={() => void loadMoreDebugJobs()}>
                Load more debug jobs
              </button>
            ) : null}
            {batchJobs.length > 0 ? (
              <ul aria-label="Batch job statuses">
                {batchJobs.map((job) => (
                  <li key={job.job_id}>
                    <span>
                      {job.job_id}：{job.status}
                    </span>
                    {job.created_at ? (
                      <span title={job.created_at}>
                        {" "}
                        {job.job_id} 创建：{formatJobTimestamp(job.created_at)}
                      </span>
                    ) : null}
                    {job.updated_at ? (
                      <span title={job.updated_at}>
                        {" "}
                        {job.job_id} 更新：{formatJobTimestamp(job.updated_at)}
                      </span>
                    ) : null}
                    {job.error_message ? <span> {job.job_id} 错误：{job.error_message}</span> : null}
                    {job.retry_recommendation_detail ? (
                      <>
                        <span> {job.job_id} 建议：{job.retry_recommendation_detail.label}</span>
                        <span> {job.job_id} 级别：{job.retry_recommendation_detail.severity}</span>
                      </>
                    ) : null}
                    <button type="button" onClick={() => openBatchJob(job)}>
                      Open job {job.job_id}
                    </button>
                    {job.evidence_ids?.map((evidenceId) => (
                      <button
                        key={evidenceId}
                        type="button"
                        onClick={() => void selectBatchJobEvidence(job.job_id, evidenceId)}
                      >
                        Open evidence {evidenceId} for job {job.job_id}
                      </button>
                    ))}
                  </li>
                ))}
              </ul>
            ) : null}
          </>
        ) : null}
      </section>
      {error ? <p role="alert">{error}</p> : null}
      {submittedJob ? (
        <>
          <JobStatusPanel job={jobStatus ?? submittedJob} onSelectEvidence={selectJobEvidence} />
          <EvidenceDetail evidence={selectedEvidence} />
        </>
      ) : null}
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

function formatJobTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return [
    date.getFullYear(),
    padDatePart(date.getMonth() + 1),
    padDatePart(date.getDate())
  ].join("-") + ` ${padDatePart(date.getHours())}:${padDatePart(date.getMinutes())}:${padDatePart(date.getSeconds())}`;
}

function padDatePart(value: number): string {
  return String(value).padStart(2, "0");
}
