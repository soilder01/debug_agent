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
  fetchObservabilitySummary,
  fetchSpreadsheetWritebackAudit,
  fetchSpreadsheetWritebackAudits,
  fetchSpreadsheetWritebackAuditSummary,
  fetchWorkerStatus,
  importCsvCases,
  importJsonlCases,
  importSpreadsheetRows,
  type JsonlImportResponse,
  type LarkSpreadsheetStatus,
  type ObservabilitySummary,
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
import { ImportedCasesPanel } from "../cases/ImportedCasesPanel";
import { ImportWorkspace } from "../imports/ImportWorkspace";
import { BatchJobsPanel } from "../jobs/BatchJobsPanel";
import { CurrentJobPanel } from "../jobs/CurrentJobPanel";
import { WorkerControlsPanel } from "../jobs/WorkerControlsPanel";
import { ObservabilitySummaryPanel } from "../observability/ObservabilitySummaryPanel";
import { DebugReportWorkspace } from "../reports/DebugReportWorkspace";
import { SpreadsheetSyncPanel } from "../spreadsheets/SpreadsheetSyncPanel";
import { parseLarkSpreadsheetUrl } from "../spreadsheets/larkUrl";

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
  const [observabilitySummary, setObservabilitySummary] = useState<ObservabilitySummary | null>(null);
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

  async function loadObservabilitySummary() {
    setError("");
    try {
      setObservabilitySummary(await fetchObservabilitySummary());
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
      <h1>Debug Detection Agent</h1>
      <button type="button" onClick={submitJob}>
        Submit debug job
      </button>
      <WorkerControlsPanel status={workerStatus} onStart={startWorkerLoop} onStop={stopWorkerLoop} />
      <section>
        <h2>Operational Monitoring</h2>
        <button type="button" onClick={() => void loadObservabilitySummary()}>
          Load observability summary
        </button>
      </section>
      {observabilitySummary ? (
        <ObservabilitySummaryPanel
          summary={observabilitySummary}
          onLoadFailedJobs={() => void loadDebugJobs("failed")}
          onLoadFailedWritebacks={() => void loadWritebackAudits("failed")}
          onStartWorker={() => void startWorkerLoop()}
        />
      ) : null}
      <ImportWorkspace
        jsonlCases={jsonlCases}
        jsonlImportResult={jsonlImportResult}
        csvCases={csvCases}
        csvImportResult={csvImportResult}
        spreadsheetRowsJson={spreadsheetRowsJson}
        spreadsheetImportResult={spreadsheetImportResult}
        onJsonlChange={setJsonlCases}
        onCsvChange={setCsvCases}
        onSpreadsheetRowsJsonChange={setSpreadsheetRowsJson}
        onImportJsonl={importJsonl}
        onImportCsv={importCsv}
        onImportSpreadsheetRowsJson={importSpreadsheetRowsJson}
      />
      <SpreadsheetSyncPanel
        spreadsheetUrl={spreadsheetUrl}
        spreadsheetId={spreadsheetId}
        sheetId={sheetId}
        larkSpreadsheetStatus={larkSpreadsheetStatus}
        syncResult={spreadsheetSyncResult}
        writebackAuditSummary={spreadsheetWritebackAuditSummary}
        writebackAuditList={spreadsheetWritebackAuditList}
        activeWritebackAuditStatus={activeWritebackAuditStatus ?? null}
        writebackResult={spreadsheetWritebackResult}
        onSpreadsheetUrlChange={setSpreadsheetUrl}
        onSpreadsheetIdChange={setSpreadsheetId}
        onSheetIdChange={setSheetId}
        onUseSpreadsheetUrl={useSpreadsheetUrl}
        onCheckLarkStatus={() => void checkLarkStatus()}
        onSyncSpreadsheet={() => void syncSpreadsheet()}
        onLoadWritebackAuditSummary={() => void loadWritebackAuditSummary()}
        onLoadWritebackAudits={(status) => void loadWritebackAudits(status)}
        onOpenAuditJob={(jobId) => void openWritebackAuditJob(jobId)}
        onRetryAudit={(auditToRetry) => void retryWritebackAudit(auditToRetry)}
        onLoadMoreWritebackAudits={() => void loadMoreWritebackAudits()}
      />
      <ImportedCasesPanel
        cases={visibleImportedCases}
        totalCount={importedCaseTotalCount}
        effectiveCount={effectiveImportedCaseCount}
        unloadedCount={unloadedCaseCount}
        selectedCaseDetail={selectedCaseDetail}
        onLoadImportedCases={() => void loadImportedCases(false)}
        onLoadWithRegions={() => void loadImportedCases(true)}
        onLoadAll={() => void loadImportedCases(false)}
        onLoadMore={() => void loadMoreImportedCases()}
        onUseForBatch={useImportedCasesForBatch}
        onViewCaseDetail={(caseId) => void loadCaseDetail(caseId)}
        onCreateDebugJob={(caseId) => void submitSelectedCaseJob(caseId)}
      />
      <BatchJobsPanel
        caseIds={batchCaseIds}
        batchResult={batchResult}
        jobs={batchJobs}
        summaryLabel={jobListSummaryLabel}
        totalCount={jobListTotalCount ?? loadedJobCount}
        unloadedCount={unloadedJobCount}
        completedCount={completedBatchJobs}
        onCaseIdsChange={setBatchCaseIds}
        onSubmit={submitBatchJobs}
        onLoadJobs={(status, sort) => void loadDebugJobs(status, sort)}
        onStartWorker={startWorkerLoop}
        onLoadMore={() => void loadMoreDebugJobs()}
        onOpenJob={openBatchJob}
        onSelectEvidence={(jobId, evidenceId) => void selectBatchJobEvidence(jobId, evidenceId)}
      />
      {error ? <p role="alert">{error}</p> : null}
      {submittedJob ? (
        <CurrentJobPanel
          job={jobStatus ?? submittedJob}
          selectedEvidence={selectedEvidence}
          onSelectEvidence={selectJobEvidence}
          onLoadReport={() => void loadCurrentJobReport()}
        />
      ) : null}
      {report ? (
        <DebugReportWorkspace
          report={report}
          selectedEvidence={selectedEvidence}
          writebackResult={spreadsheetWritebackResult}
          writebackAudit={spreadsheetWritebackAudit}
          onSelectEvidence={selectEvidence}
          onWriteReport={() => void writeCurrentReportToSpreadsheet()}
          onLoadWritebackAudit={() => void loadCurrentWritebackAudit()}
        />
      ) : submittedJob ? null : (
        <p>点击按钮运行第一条可验证 debug 闭环。</p>
      )}
    </main>
  );
}
