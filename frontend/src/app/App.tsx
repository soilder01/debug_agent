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
import { ImportedCaseDetailPanel } from "../cases/ImportedCaseDetailPanel";
import { ImportedCaseListPanel } from "../cases/ImportedCaseListPanel";
import { EvidenceDetail } from "../evidence/EvidenceDetail";
import { ExperimentTimeline } from "../experiments/ExperimentTimeline";
import { CSVImportPanel } from "../imports/CSVImportPanel";
import { JSONLImportPanel } from "../imports/JSONLImportPanel";
import { BatchJobControlsPanel } from "../jobs/BatchJobControlsPanel";
import { BatchJobListPanel } from "../jobs/BatchJobListPanel";
import { JobStatusPanel } from "../jobs/JobStatusPanel";
import { WorkerControlsPanel } from "../jobs/WorkerControlsPanel";
import { ReportPanel } from "../reports/ReportPanel";
import { LarkSpreadsheetStatusPanel } from "../spreadsheets/LarkSpreadsheetStatusPanel";
import { SpreadsheetControlsPanel } from "../spreadsheets/SpreadsheetControlsPanel";
import { SpreadsheetImportPanel } from "../spreadsheets/SpreadsheetImportPanel";
import { SpreadsheetSyncResultPanel } from "../spreadsheets/SpreadsheetSyncResultPanel";
import { SpreadsheetWritebackPanel } from "../spreadsheets/SpreadsheetWritebackPanel";
import { parseLarkSpreadsheetUrl } from "../spreadsheets/larkUrl";
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
      <WorkerControlsPanel status={workerStatus} onStart={startWorkerLoop} onStop={stopWorkerLoop} />
      <section>
        <h2>JSONL Import</h2>
        <JSONLImportPanel value={jsonlCases} result={jsonlImportResult} onChange={setJsonlCases} onImport={importJsonl} />
      </section>
      <section>
        <h2>CSV Import</h2>
        <CSVImportPanel value={csvCases} result={csvImportResult} onChange={setCsvCases} onImport={importCsv} />
      </section>
      <section>
        <h2>Spreadsheet Rows Import</h2>
        <SpreadsheetImportPanel
          value={spreadsheetRowsJson}
          result={spreadsheetImportResult}
          onChange={setSpreadsheetRowsJson}
          onImport={importSpreadsheetRowsJson}
        />
      </section>
      <section>
        <h2>Spreadsheet Sync</h2>
        <SpreadsheetControlsPanel
          spreadsheetUrl={spreadsheetUrl}
          spreadsheetId={spreadsheetId}
          sheetId={sheetId}
          onSpreadsheetUrlChange={setSpreadsheetUrl}
          onSpreadsheetIdChange={setSpreadsheetId}
          onSheetIdChange={setSheetId}
          onUseSpreadsheetUrl={useSpreadsheetUrl}
          onCheckLarkStatus={() => void checkLarkStatus()}
          onSyncSpreadsheet={() => void syncSpreadsheet()}
          onLoadWritebackAuditSummary={() => void loadWritebackAuditSummary()}
          onLoadWritebackAudits={(status) => void loadWritebackAudits(status)}
        />
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
            <ImportedCaseListPanel
              cases={visibleImportedCases}
              totalCount={importedCaseTotalCount}
              effectiveCount={effectiveImportedCaseCount}
              unloadedCount={unloadedCaseCount}
              onLoadWithRegions={() => void loadImportedCases(true)}
              onLoadAll={() => void loadImportedCases(false)}
              onLoadMore={() => void loadMoreImportedCases()}
              onUseForBatch={useImportedCasesForBatch}
              onViewCaseDetail={(caseId) => void loadCaseDetail(caseId)}
            />
            {selectedCaseDetail ? (
              <ImportedCaseDetailPanel
                caseDetail={selectedCaseDetail}
                onCreateDebugJob={(caseId) => void submitSelectedCaseJob(caseId)}
              />
            ) : null}
          </>
        ) : null}
      </section>
      <section>
        <BatchJobControlsPanel
          caseIds={batchCaseIds}
          onCaseIdsChange={setBatchCaseIds}
          onSubmit={submitBatchJobs}
          onLoadJobs={(status, sort) => void loadDebugJobs(status, sort)}
        />
        {batchResult ? (
          <>
            <BatchJobListPanel
              jobs={batchJobs}
              summaryLabel={jobListSummaryLabel}
              totalCount={jobListTotalCount ?? batchResult.jobs.length}
              unloadedCount={unloadedJobCount}
              rejectedCaseIds={batchResult.rejected_case_ids}
              completedCount={completedBatchJobs}
              onStartWorker={startWorkerLoop}
              onLoadMore={() => void loadMoreDebugJobs()}
              onOpenJob={openBatchJob}
              onSelectEvidence={(jobId, evidenceId) => void selectBatchJobEvidence(jobId, evidenceId)}
            />
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
            <SpreadsheetWritebackPanel
              writebackResult={spreadsheetWritebackResult}
              writebackAudit={spreadsheetWritebackAudit}
              onWriteReport={() => void writeCurrentReportToSpreadsheet()}
              onLoadAudit={() => void loadCurrentWritebackAudit()}
            />
          ) : null}
        </>
      ) : submittedJob ? null : (
        <p>点击按钮运行第一条可验证 debug 闭环。</p>
      )}
    </main>
  );
}
