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
  fetchJobReport,
  fetchJobStatus,
  fetchLarkSpreadsheetStatus,
  fetchSpreadsheetWritebackAudit,
  fetchSpreadsheetWritebackAudits,
  fetchSpreadsheetWritebackAuditSummary,
  fetchWorkerStatus,
  importCsvCases,
  importJsonlCases,
  importSpreadsheetRows,
  type JsonlImportResponse,
  type LarkSpreadsheetStatus,
  startWorker,
  submitBatchDebugJobs,
  submitDebugJob,
  type SpreadsheetRowImportResponse,
  type SpreadsheetWritebackAudit,
  type SpreadsheetWritebackAuditCounts,
  type SpreadsheetWritebackAuditListResponse,
  type SpreadsheetSyncResponse,
  type SpreadsheetWritebackResult,
  stopWorker,
  syncSpreadsheetRows,
  type DebugJobStatus,
  type DebugReport,
  type ExperimentEvidence,
  type SubmittedDebugJob,
  type WorkerStatus,
  writeJobReportToSpreadsheet
} from "../api/client";
import { CaseDetail } from "../cases/CaseDetail";
import { EvidenceDetail } from "../evidence/EvidenceDetail";
import { ExperimentTimeline } from "../experiments/ExperimentTimeline";
import { JSONLImportResultPanel } from "../imports/JSONLImportResultPanel";
import { JobStatusPanel } from "../jobs/JobStatusPanel";
import { ReportPanel } from "../reports/ReportPanel";
import { LarkSpreadsheetStatusPanel } from "../spreadsheets/LarkSpreadsheetStatusPanel";
import { SpreadsheetImportResultPanel } from "../spreadsheets/SpreadsheetImportResultPanel";
import { SpreadsheetSyncResultPanel } from "../spreadsheets/SpreadsheetSyncResultPanel";
import { WritebackAuditList } from "../spreadsheets/WritebackAuditList";
import { WritebackAuditSummary } from "../spreadsheets/WritebackAuditSummary";

const jobListLimit = 50;
const caseListLimit = 50;
const defaultSpreadsheetUrl = "https://bytedance.larkoffice.com/sheets/NLews6C2ShValptV7IdcJ62tnWc?sheet=qJAomX";
const defaultSpreadsheetId = "NLews6C2ShValptV7IdcJ62tnWc";
const defaultSheetId = "qJAomX";

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
  const [spreadsheetRowsJson, setSpreadsheetRowsJson] = useState("");
  const [spreadsheetImportResult, setSpreadsheetImportResult] = useState<SpreadsheetRowImportResponse | null>(null);
  const [spreadsheetUrl, setSpreadsheetUrl] = useState(defaultSpreadsheetUrl);
  const [spreadsheetId, setSpreadsheetId] = useState(defaultSpreadsheetId);
  const [sheetId, setSheetId] = useState(defaultSheetId);
  const [spreadsheetSyncResult, setSpreadsheetSyncResult] = useState<SpreadsheetSyncResponse | null>(null);
  const [spreadsheetWritebackResult, setSpreadsheetWritebackResult] = useState<SpreadsheetWritebackResult | null>(null);
  const [spreadsheetWritebackAudit, setSpreadsheetWritebackAudit] = useState<SpreadsheetWritebackAudit | null>(null);
  const [spreadsheetWritebackAuditSummary, setSpreadsheetWritebackAuditSummary] =
    useState<SpreadsheetWritebackAuditCounts | null>(null);
  const [spreadsheetWritebackAuditList, setSpreadsheetWritebackAuditList] =
    useState<SpreadsheetWritebackAuditListResponse | null>(null);
  const [activeWritebackAuditStatus, setActiveWritebackAuditStatus] = useState<string | null | undefined>(undefined);
  const [larkSpreadsheetStatus, setLarkSpreadsheetStatus] = useState<LarkSpreadsheetStatus | null>(null);
  const [workerStatus, setWorkerStatus] = useState<WorkerStatus | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<ExperimentEvidence | null>(null);
  const [importedCaseTotalCount, setImportedCaseTotalCount] = useState(0);
  const [importedCaseFilteredCount, setImportedCaseFilteredCount] = useState<number | null>(null);
  const [activeImportedCaseHasRegions, setActiveImportedCaseHasRegions] = useState(false);
  const [activeJobStatusFilter, setActiveJobStatusFilter] = useState<string | undefined>(undefined);
  const [activeJobSort, setActiveJobSort] = useState<string | undefined>(undefined);
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
      setSpreadsheetWritebackResult(null);
      setSpreadsheetWritebackAudit(null);
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
      setSpreadsheetWritebackResult(null);
      setSpreadsheetWritebackAudit(null);
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

  async function loadDebugJobs(status?: string, sort?: string) {
    setError("");
    try {
      const result = await fetchDebugJobs(status, jobListLimit, undefined, sort);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setJobListSummaryLabel(sort === "created_at_desc" ? "最新任务" : status === "failed" ? "失败任务" : "队列任务");
      setJobListTotalCount(result.total_count);
      setActiveJobStatusFilter(status);
      setActiveJobSort(sort);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function loadMoreDebugJobs() {
    setError("");
    try {
      const result = await fetchDebugJobs(activeJobStatusFilter, jobListLimit, batchJobs.length, activeJobSort);
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
    setSpreadsheetWritebackResult(null);
    setSpreadsheetWritebackAudit(null);
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

  async function importSpreadsheetRowsJson() {
    setError("");
    try {
      const parsedRows = JSON.parse(spreadsheetRowsJson) as unknown;
      if (!Array.isArray(parsedRows)) {
        throw new Error("Spreadsheet rows JSON must be an array");
      }
      const result = await importSpreadsheetRows(parsedRows as Array<Record<string, unknown>>);
      setSpreadsheetImportResult(result);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setJobListSummaryLabel("批量创建");
      setJobListTotalCount(result.jobs.length);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  function useSpreadsheetUrl() {
    setError("");
    try {
      const reference = parseLarkSpreadsheetUrl(spreadsheetUrl);
      setSpreadsheetId(reference.spreadsheetId);
      setSheetId(reference.sheetId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }


  async function checkLarkStatus() {
    setError("");
    try {
      setLarkSpreadsheetStatus(await fetchLarkSpreadsheetStatus(true));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function syncSpreadsheet() {
    setError("");
    try {
      const result = await syncSpreadsheetRows(spreadsheetId, sheetId);
      setSpreadsheetSyncResult(result);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setJobListSummaryLabel("Spreadsheet 同步任务");
      setJobListTotalCount(result.jobs.length);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function loadWritebackAuditSummary() {
    setError("");
    try {
      setSpreadsheetWritebackAuditSummary(await fetchSpreadsheetWritebackAuditSummary());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function loadWritebackAudits(status: string | null) {
    setError("");
    try {
      setActiveWritebackAuditStatus(status);
      setSpreadsheetWritebackAuditList(await fetchSpreadsheetWritebackAudits(status ?? undefined, jobListLimit));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function loadMoreWritebackAudits() {
    if (activeWritebackAuditStatus === undefined || !spreadsheetWritebackAuditList) {
      return;
    }
    setError("");
    try {
      const nextPage = await fetchSpreadsheetWritebackAudits(
        activeWritebackAuditStatus ?? undefined,
        jobListLimit,
        spreadsheetWritebackAuditList.audits.length,
      );
      setSpreadsheetWritebackAuditList({
        audits: [...spreadsheetWritebackAuditList.audits, ...nextPage.audits],
        total_count: nextPage.total_count,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function openWritebackAuditJob(jobId: string) {
    setError("");
    try {
      const status = await fetchJobStatus(jobId);
      setSubmittedJob(status);
      setJobStatus(status);
      setReport(null);
      setSpreadsheetWritebackResult(null);
      setSpreadsheetWritebackAudit(null);
      setSelectedEvidence(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function retryWritebackAudit(audit: SpreadsheetWritebackAudit) {
    setError("");
    try {
      const reportUrl = audit.report_url || `${window.location.origin}/api/jobs/${audit.job_id}/report`;
      const result = await writeJobReportToSpreadsheet(audit.job_id, reportUrl);
      setSpreadsheetWritebackResult(result);
      setSpreadsheetWritebackAudit(null);
      if (activeWritebackAuditStatus !== undefined) {
        setSpreadsheetWritebackAuditList(
          await fetchSpreadsheetWritebackAudits(activeWritebackAuditStatus ?? undefined, jobListLimit)
        );
      }
      setSpreadsheetWritebackAuditSummary(await fetchSpreadsheetWritebackAuditSummary());
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

  async function loadCurrentJobReport() {
    const currentJob = jobStatus ?? submittedJob;
    if (!currentJob) {
      return;
    }
    setError("");
    try {
      setReport(await fetchJobReport(currentJob.job_id));
      setSpreadsheetWritebackResult(null);
      setSpreadsheetWritebackAudit(null);
      setSelectedEvidence(null);
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

  async function writeCurrentReportToSpreadsheet() {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      const reportUrl = `${window.location.origin}/api/jobs/${report.job_id}/report`;
      setSpreadsheetWritebackResult(await writeJobReportToSpreadsheet(report.job_id, reportUrl));
      setSpreadsheetWritebackAudit(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  async function loadCurrentWritebackAudit() {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      setSpreadsheetWritebackAudit(await fetchSpreadsheetWritebackAudit(report.job_id));
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
            <p>Worker auto writeback setting：{workerStatus.auto_writeback_enabled ? "enabled" : "disabled"}</p>
            <p>Worker auto writeback：{workerStatus.completion_hook_enabled ? "enabled" : "disabled"}</p>
            <p>Worker report base URL：{workerStatus.report_base_url}</p>
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
        {jsonlImportResult ? <JSONLImportResultPanel result={jsonlImportResult} /> : null}
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
        <h2>Spreadsheet Rows Import</h2>
        <label htmlFor="spreadsheet-rows-json">Spreadsheet rows JSON</label>
        <textarea
          id="spreadsheet-rows-json"
          value={spreadsheetRowsJson}
          onChange={(event) => setSpreadsheetRowsJson(event.target.value)}
        />
        <button type="button" onClick={importSpreadsheetRowsJson}>
          Import spreadsheet rows JSON
        </button>
        {spreadsheetImportResult ? <SpreadsheetImportResultPanel result={spreadsheetImportResult} /> : null}
      </section>
      <section>
        <h2>Spreadsheet Sync</h2>
        <label htmlFor="lark-spreadsheet-url">Lark spreadsheet URL</label>
        <input
          id="lark-spreadsheet-url"
          value={spreadsheetUrl}
          onChange={(event) => setSpreadsheetUrl(event.target.value)}
        />
        <button type="button" onClick={useSpreadsheetUrl}>
          Use spreadsheet URL
        </button>
        <label htmlFor="spreadsheet-id">Spreadsheet ID</label>
        <input
          id="spreadsheet-id"
          value={spreadsheetId}
          onChange={(event) => setSpreadsheetId(event.target.value)}
        />
        <label htmlFor="sheet-id">Sheet ID</label>
        <input id="sheet-id" value={sheetId} onChange={(event) => setSheetId(event.target.value)} />
        <button type="button" onClick={() => void checkLarkStatus()}>
          Check Lark status
        </button>
        <button type="button" onClick={() => void syncSpreadsheet()}>
          Sync spreadsheet rows
        </button>
        <button type="button" onClick={() => void loadWritebackAuditSummary()}>
          Load writeback audit summary
        </button>
        <button type="button" onClick={() => void loadWritebackAudits(null)}>
          Load all writeback audits
        </button>
        <button type="button" onClick={() => void loadWritebackAudits("succeeded")}>
          Load succeeded writeback audits
        </button>
        <button type="button" onClick={() => void loadWritebackAudits("failed")}>
          Load failed writeback audits
        </button>
        <button type="button" onClick={() => void loadWritebackAudits("skipped")}>
          Load skipped writeback audits
        </button>
        {larkSpreadsheetStatus ? <LarkSpreadsheetStatusPanel status={larkSpreadsheetStatus} /> : null}
        {spreadsheetSyncResult ? <SpreadsheetSyncResultPanel result={spreadsheetSyncResult} /> : null}
        {spreadsheetWritebackAuditSummary ? (
          <WritebackAuditSummary
            summary={spreadsheetWritebackAuditSummary}
            onLoadStatus={(status) => void loadWritebackAudits(status)}
          />
        ) : null}
        {spreadsheetWritebackAuditList ? (
          <WritebackAuditList
            audits={spreadsheetWritebackAuditList.audits}
            activeFilter={activeWritebackAuditStatus ?? null}
            totalCount={spreadsheetWritebackAuditList.total_count}
            writebackResult={spreadsheetWritebackResult}
            onOpenJob={(jobId) => void openWritebackAuditJob(jobId)}
            onRetry={(auditToRetry) => void retryWritebackAudit(auditToRetry)}
            onLoadMore={() => void loadMoreWritebackAudits()}
          />
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
        <button type="button" onClick={() => void loadDebugJobs(undefined, "created_at_desc")}>
          Load newest debug jobs
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
          <JobStatusPanel
            job={jobStatus ?? submittedJob}
            onSelectEvidence={selectJobEvidence}
            onLoadReport={() => void loadCurrentJobReport()}
          />
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
          {report.job_id ? (
            <section>
              <h2>Spreadsheet Writeback</h2>
              <button type="button" onClick={() => void writeCurrentReportToSpreadsheet()}>
                Write report to spreadsheet
              </button>
              <button type="button" onClick={() => void loadCurrentWritebackAudit()}>
                Load writeback audit
              </button>
              {spreadsheetWritebackResult ? (
                <>
                  <p>Spreadsheet writeback row：{spreadsheetWritebackResult.row_id}</p>
                  <ul aria-label="Spreadsheet writeback fields">
                    {Object.entries(spreadsheetWritebackResult.fields).map(([key, value]) => (
                      <li key={key}>
                        {key}：{value}
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
              {spreadsheetWritebackAudit ? (
                <>
                  <p>Writeback audit status：{spreadsheetWritebackAudit.status}</p>
                  <p>Writeback audit row：{spreadsheetWritebackAudit.row_id}</p>
                  <p>Writeback audit report URL：{spreadsheetWritebackAudit.report_url}</p>
                  <p>Writeback audit updated：{spreadsheetWritebackAudit.updated_at}</p>
                  {spreadsheetWritebackAudit.error_message ? (
                    <p role="alert">Writeback audit error：{spreadsheetWritebackAudit.error_message}</p>
                  ) : null}
                </>
              ) : null}
            </section>
          ) : null}
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

function parseLarkSpreadsheetUrl(value: string): { spreadsheetId: string; sheetId: string } {
  const parsed = new URL(value);
  const pathParts = parsed.pathname.split("/").filter(Boolean);
  if (pathParts.length < 2 || pathParts[0] !== "sheets") {
    throw new Error("Lark spreadsheet URL must contain /sheets/{spreadsheet_id}");
  }
  const sheetId = parsed.searchParams.get("sheet") ?? "";
  if (!sheetId) {
    throw new Error("Lark spreadsheet URL must include a sheet query parameter");
  }
  return { spreadsheetId: pathParts[1], sheetId };
}
