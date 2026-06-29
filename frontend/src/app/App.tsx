import { useEffect, useState } from "react";

import {
  type AgentModelConfig,
  type AutoDebugClosureResult,
  type BatchDebugJobResponse,
  type DebugBatchProgress,
  debugJobExportUrl,
  type CsvImportResponse,
  type DebugCaseDetail,
  type DebugCaseSummary,
  fetchCaseDetail,
  fetchCases,
  fetchAgentModelCatalog,
  fetchDebugJobs,
  fetchDebugBatches,
  fetchObservabilitySummary,
  importCsvCases,
  importJsonlCases,
  importSpreadsheetRows,
  type JsonlImportResponse,
  type HumanHandoffStatus,
  type LarkOperationAuditListResponse,
  type LarkAuthSession,
  type LarkBotBadcaseDraftConfirmResponse,
  type LarkBotBadcaseDraftListResponse,
  type LarkNotificationOutboxListResponse,
  type LarkBotPendingCommandListResponse,
  type LarkBotGoLiveGate,
  type LarkBotPreflight,
  type LarkBotReplyPayload,
  type LarkScopeCheckResponse,
  type LarkSpreadsheetStatus,
  type LarkWriteConfirmation,
  type ModelCatalogOption,
  type ObservabilitySummary,
  type PilotGate,
  type ProductionReadiness,
  type RecommendedActionStatusEvent,
  type RecommendedActionVerification,
  type RecommendedActionVerificationResult,
  startWorker,
  submitBatchDebugJobs,
  submitDebugJob,
  type SpreadsheetRowImportResponse,
  type SpreadsheetWritebackAudit,
  type SpreadsheetWritebackAuditCounts,
  type SpreadsheetWritebackAuditListResponse,
  type SpreadsheetSyncResponse,
  type StrategyFollowUpJob,
  type TargetedProbeJob,
  type SpreadsheetWritebackResult,
  stopWorker,
  type DebugJobStatus,
  type DebugRunStage,
  type DebugReport,
  type EvidenceLedgerRecord,
  type ExperimentEvidence,
  type SubmittedDebugJob,
  type WorkerStatus,
  updateDebugBatchStatus,
} from "../api/client";
import { FloatingAssistant } from "../assistant/FloatingAssistant";
import { ImportedCasesPanel } from "../cases/ImportedCasesPanel";
import { ImportWorkspace } from "../imports/ImportWorkspace";
import { BatchJobsPanel } from "../jobs/BatchJobsPanel";
import { CurrentJobPanel } from "../jobs/CurrentJobPanel";
import { WorkerControlsPanel } from "../jobs/WorkerControlsPanel";
import { ObservabilitySummaryPanel } from "../observability/ObservabilitySummaryPanel";
import { LarkBotBadcaseDraftPanel } from "../observability/LarkBotBadcaseDraftPanel";
import { LarkBotGoLiveGatePanel } from "../observability/LarkBotGoLiveGatePanel";
import { LarkNotificationOutboxPanel } from "../observability/LarkNotificationOutboxPanel";
import { LarkBotPendingCommandPanel } from "../observability/LarkBotPendingCommandPanel";
import { LarkBotPreflightPanel } from "../observability/LarkBotPreflightPanel";
import { PilotGatePanel } from "../observability/PilotGatePanel";
import { ProductionReadinessPanel } from "../observability/ProductionReadinessPanel";
import { AgentTopologyPanel } from "../orchestration/AgentTopologyPanel";
import { DebugReportWorkspace } from "../reports/DebugReportWorkspace";
import { SpreadsheetSyncPanel } from "../spreadsheets/SpreadsheetSyncPanel";
import { parseLarkSpreadsheetUrl } from "../spreadsheets/larkUrl";
import {
  caseListLimit,
  defaultSheetId,
  defaultSpreadsheetId,
  defaultSpreadsheetUrl,
  jobListLimit,
} from "./App.config";
import { TerminalDataStream } from "./TerminalDataStream";
import { useAppOperationsActions } from "./useAppOperationsActions";
import { useAppPollingEffects } from "./useAppPollingEffects";
import { useAppReportActions } from "./useAppReportActions";
import { useProductMotion } from "./useProductMotion";

export function App() {
  const motionScopeRef = useProductMotion();
  const [report, setReport] = useState<DebugReport | null>(null);
  const [submittedJob, setSubmittedJob] = useState<SubmittedDebugJob | null>(null);
  const [jobStatus, setJobStatus] = useState<DebugJobStatus | null>(null);
  const [debugRunStages, setDebugRunStages] = useState<DebugRunStage[]>([]);
  const [evidenceLedger, setEvidenceLedger] = useState<EvidenceLedgerRecord[]>([]);
  const [batchCaseIds, setBatchCaseIds] = useState("");
  const [agentModelConfig, setAgentModelConfig] = useState<AgentModelConfig | null>(null);
  const [modelCatalog, setModelCatalog] = useState<ModelCatalogOption[]>([]);
  const [batchResult, setBatchResult] = useState<BatchDebugJobResponse | null>(null);
  const [activeBatchProgress, setActiveBatchProgress] = useState<DebugBatchProgress | null>(null);
  const [batchHistory, setBatchHistory] = useState<DebugBatchProgress[]>([]);
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
  const [rerunRowIds, setRerunRowIds] = useState("2-8");
  const [rerunAutoClosure, setRerunAutoClosure] = useState(true);
  const [rerunWriteback, setRerunWriteback] = useState(true);
  const [spreadsheetSyncResult, setSpreadsheetSyncResult] = useState<SpreadsheetSyncResponse | null>(null);
  const [spreadsheetWritebackResult, setSpreadsheetWritebackResult] = useState<SpreadsheetWritebackResult | null>(null);
  const [spreadsheetWritebackAudit, setSpreadsheetWritebackAudit] = useState<SpreadsheetWritebackAudit | null>(null);
  const [recommendedActionStatusEvents, setRecommendedActionStatusEvents] = useState<RecommendedActionStatusEvent[]>([]);
  const [recommendedActionVerifications, setRecommendedActionVerifications] = useState<RecommendedActionVerification[]>([]);
  const [recommendedActionVerificationResults, setRecommendedActionVerificationResults] = useState<
    RecommendedActionVerificationResult[]
  >([]);
  const [strategyFollowUps, setStrategyFollowUps] = useState<StrategyFollowUpJob[]>([]);
  const [targetedProbes, setTargetedProbes] = useState<TargetedProbeJob[]>([]);
  const [humanHandoffStatuses, setHumanHandoffStatuses] = useState<HumanHandoffStatus[]>([]);
  const [autoDebugClosureResult, setAutoDebugClosureResult] = useState<AutoDebugClosureResult | null>(null);
  const [autoDebugClosureMarkdown, setAutoDebugClosureMarkdown] = useState("");
  const [autoDebugClosureReportUrl, setAutoDebugClosureReportUrl] = useState("");
  const [spreadsheetWritebackAuditSummary, setSpreadsheetWritebackAuditSummary] =
    useState<SpreadsheetWritebackAuditCounts | null>(null);
  const [spreadsheetWritebackAuditList, setSpreadsheetWritebackAuditList] =
    useState<SpreadsheetWritebackAuditListResponse | null>(null);
  const [activeWritebackAuditStatus, setActiveWritebackAuditStatus] = useState<string | null | undefined>(undefined);
  const [larkOperationAuditList, setLarkOperationAuditList] = useState<LarkOperationAuditListResponse | null>(null);
  const [activeLarkOperationAuditStatus, setActiveLarkOperationAuditStatus] = useState<string | null | undefined>(undefined);
  const [larkBotPendingCommandList, setLarkBotPendingCommandList] =
    useState<LarkBotPendingCommandListResponse | null>(null);
  const [activeLarkBotPendingStatus, setActiveLarkBotPendingStatus] = useState<string | null | undefined>(undefined);
  const [larkBotReplyPreview, setLarkBotReplyPreview] = useState<LarkBotReplyPayload | null>(null);
  const [larkNotificationOutboxList, setLarkNotificationOutboxList] =
    useState<LarkNotificationOutboxListResponse | null>(null);
  const [activeLarkNotificationOutboxStatus, setActiveLarkNotificationOutboxStatus] = useState<
    string | null | undefined
  >(undefined);
  const [larkBotBadcaseDraftList, setLarkBotBadcaseDraftList] =
    useState<LarkBotBadcaseDraftListResponse | null>(null);
  const [activeLarkBotBadcaseDraftStatus, setActiveLarkBotBadcaseDraftStatus] = useState<string | null | undefined>(
    undefined
  );
  const [larkBotBadcaseDraftConfirmation, setLarkBotBadcaseDraftConfirmation] =
    useState<LarkBotBadcaseDraftConfirmResponse | null>(null);
  const [larkScopeCheck, setLarkScopeCheck] = useState<LarkScopeCheckResponse | null>(null);
  const [larkAuthSession, setLarkAuthSession] = useState<LarkAuthSession | null>(null);
  const [larkWriteConfirmation, setLarkWriteConfirmation] = useState<LarkWriteConfirmation | null>(null);
  const [larkSpreadsheetStatus, setLarkSpreadsheetStatus] = useState<LarkSpreadsheetStatus | null>(null);
  const [workerStatus, setWorkerStatus] = useState<WorkerStatus | null>(null);
  const [observabilitySummary, setObservabilitySummary] = useState<ObservabilitySummary | null>(null);
  const [productionReadiness, setProductionReadiness] = useState<ProductionReadiness | null>(null);
  const [larkBotGoLiveGate, setLarkBotGoLiveGate] = useState<LarkBotGoLiveGate | null>(null);
  const [larkBotPreflight, setLarkBotPreflight] = useState<LarkBotPreflight | null>(null);
  const [pilotGate, setPilotGate] = useState<PilotGate | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<ExperimentEvidence | null>(null);
  const [importedCaseTotalCount, setImportedCaseTotalCount] = useState(0);
  const [importedCaseFilteredCount, setImportedCaseFilteredCount] = useState<number | null>(null);
  const [activeImportedCaseHasRegions, setActiveImportedCaseHasRegions] = useState(false);
  const [activeJobStatusFilter, setActiveJobStatusFilter] = useState<string | undefined>(undefined);
  const [activeJobSort, setActiveJobSort] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"workspace" | "intake" | "operations" | "writeback">("workspace");

  const batchJobs = Object.values(batchJobStatuses);
  const completedBatchJobs = batchJobs.filter((job) => job.status === "completed").length;
  const loadedJobCount = batchResult?.jobs.length ?? 0;
  const unloadedJobCount = Math.max(0, (jobListTotalCount ?? loadedJobCount) - loadedJobCount);
  const visibleImportedCases = importedCases;
  const effectiveImportedCaseCount = importedCaseFilteredCount ?? importedCaseTotalCount;
  const unloadedCaseCount = Math.max(0, effectiveImportedCaseCount - visibleImportedCases.length);
  const currentBatchExportHref =
    batchJobs.length > 0 ? debugJobExportUrl({ jobIds: batchJobs.map((job) => job.job_id) }) : undefined;
  const failedJobsExportHref = debugJobExportUrl({ status: "failed", limit: 50 });
  const newestJobsExportHref = debugJobExportUrl({ limit: 50, sort: "created_at_desc" });
  const spreadsheetBatchExportHref =
    spreadsheetSyncResult?.jobs.length ? debugJobExportUrl({ jobIds: spreadsheetSyncResult.jobs.map((job) => job.job_id) }) : undefined;

  const {
    loadCurrentDebugRunStages,
    loadCurrentEvidenceLedger,
    selectEvidence,
    selectJobEvidence,
    loadCurrentJobReport,
    selectBatchJobEvidence,
    writeCurrentReportToSpreadsheet,
    prepareCurrentWritebackConfirmation,
    confirmCurrentWritebackAndWrite,
    loadCurrentWritebackAudit,
    runCurrentAutoDebugClosure,
    updateCurrentRecommendedActionStatus,
    updateCurrentHumanHandoffStatus,
    verifyCurrentRecommendedAction,
    createCurrentStrategyFollowUp,
    createCurrentTargetedProbe,
    createCurrentFinalAttributionFollowUp,
    createCurrentFinalAttributionRecovery,
    openStrategyFollowUpJob,
  } = useAppReportActions({
    report,
    submittedJob,
    jobStatus,
    spreadsheetUrl,
    spreadsheetId,
    sheetId,
    larkWriteConfirmation,
    setError,
    setSubmittedJob,
    setJobStatus,
    setReport,
    setDebugRunStages,
    setEvidenceLedger,
    setSelectedEvidence,
    setSpreadsheetWritebackResult,
    setSpreadsheetWritebackAudit,
    setLarkWriteConfirmation,
    setRecommendedActionStatusEvents,
    setRecommendedActionVerifications,
    setRecommendedActionVerificationResults,
    setStrategyFollowUps,
    setTargetedProbes,
    setHumanHandoffStatuses,
    setAutoDebugClosureResult,
    setAutoDebugClosureMarkdown,
    setAutoDebugClosureReportUrl,
  });

  function selectTab(tab: "workspace" | "intake" | "operations" | "writeback") {
    setError("");
    setActiveTab(tab);
  }

  const {
    checkLarkStatus,
    syncSpreadsheet,
    rerunSelectedSpreadsheetRows,
    loadWritebackAuditSummary,
    loadWritebackAudits,
    loadMoreWritebackAudits,
    loadLarkOperationAudits,
    loadMoreLarkOperationAudits,
    loadLarkBotPendingCommands,
    loadLarkNotificationOutbox,
    loadMoreLarkNotificationOutbox,
    loadMoreLarkBotPendingCommands,
    confirmCurrentLarkBotPendingCommand,
    previewCurrentLarkBotReply,
    loadLarkBotBadcaseDrafts,
    loadMoreLarkBotBadcaseDrafts,
    confirmCurrentLarkBotBadcaseDraft,
    checkLarkScopes,
    createCurrentLarkAuthSession,
    completeCurrentLarkAuthSession,
    loadProductionReadiness,
    loadLarkBotPreflight,
    loadLarkBotGoLiveGate,
    recordLarkBotSetupAcknowledgement,
    loadPilotGate,
    openWritebackAuditJob,
    retryWritebackAudit,
  } = useAppOperationsActions({
    spreadsheetUrl,
    spreadsheetId,
    sheetId,
    rerunRowIds,
    rerunAutoClosure,
    rerunWriteback,
    activeWritebackAuditStatus,
    spreadsheetWritebackAuditList,
    activeLarkOperationAuditStatus,
    larkOperationAuditList,
    activeLarkBotPendingStatus,
    larkBotPendingCommandList,
    activeLarkNotificationOutboxStatus,
    larkNotificationOutboxList,
    activeLarkBotBadcaseDraftStatus,
    larkBotBadcaseDraftList,
    larkAuthSession,
    larkScopeCheck,
    larkSpreadsheetStatus,
    selectTab,
    setError,
    setBatchResult,
    setJobListSummaryLabel,
    setJobListTotalCount,
    setBatchJobStatuses,
    setActiveBatchProgress,
    setLarkSpreadsheetStatus,
    setSpreadsheetSyncResult,
    setSpreadsheetWritebackResult,
    setSpreadsheetWritebackAudit,
    setSpreadsheetWritebackAuditSummary,
    setSpreadsheetWritebackAuditList,
    setActiveWritebackAuditStatus,
    setLarkOperationAuditList,
    setActiveLarkOperationAuditStatus,
    setLarkBotPendingCommandList,
    setActiveLarkBotPendingStatus,
    setLarkNotificationOutboxList,
    setActiveLarkNotificationOutboxStatus,
    setLarkBotReplyPreview,
    setLarkBotBadcaseDraftList,
    setActiveLarkBotBadcaseDraftStatus,
    setLarkBotBadcaseDraftConfirmation,
    setLarkScopeCheck,
    setLarkAuthSession,
    setProductionReadiness,
    setLarkBotPreflight,
    setLarkBotGoLiveGate,
    setPilotGate,
    setSubmittedJob,
    setJobStatus,
    setReport,
    setAutoDebugClosureResult,
    setAutoDebugClosureMarkdown,
    setAutoDebugClosureReportUrl,
    setSelectedEvidence,
  });

  useAppPollingEffects({
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
  });

  useEffect(() => {
    if (import.meta.env.MODE === "test") {
      return;
    }
    fetchAgentModelCatalog()
      .then((result) => {
        setAgentModelConfig(result.runtime.default_config);
        setModelCatalog(result.runtime.catalog);
      })
      .catch((caught: unknown) => {
        setError(caught instanceof Error ? caught.message : "未知错误");
      });
  }, []);

  async function submitJob() {
    setError("");
    if (!selectedCaseDetail) {
      selectTab("intake");
      setError("请先在数据导入或飞书同步结果中选择一个案件，再提交调试任务。");
      return;
    }
    try {
      setSubmittedJob(await submitDebugJob(selectedCaseDetail.case_id));
      setJobStatus(null);
      setReport(null);
      setSpreadsheetWritebackResult(null);
      setSpreadsheetWritebackAudit(null);
      setLarkWriteConfirmation(null);
      setAutoDebugClosureResult(null);
      setAutoDebugClosureMarkdown("");
      setAutoDebugClosureReportUrl("");
      setSelectedEvidence(null);
      setSelectedEvidence(null);
      selectTab("workspace");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
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
      setError(caught instanceof Error ? caught.message : "未知错误");
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
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  function useImportedCasesForBatch() {
    setBatchCaseIds(visibleImportedCases.map((caseSummary) => caseSummary.case_id).join("\n"));
    selectTab("workspace");
  }

  async function loadCaseDetail(caseId: string) {
    setError("");
    try {
      setSelectedCaseDetail(await fetchCaseDetail(caseId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
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
      setAutoDebugClosureResult(null);
      setAutoDebugClosureMarkdown("");
      setAutoDebugClosureReportUrl("");
      setSelectedEvidence(null);
      setSelectedEvidence(null);
      selectTab("workspace");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  async function submitBatchJobs() {
    setError("");
    const caseIds = batchCaseIds
      .split(/\s+/)
      .map((caseId) => caseId.trim())
      .filter(Boolean);
    try {
      const result = await submitBatchDebugJobs({ caseIds, agentModelConfig: agentModelConfig ?? undefined });
      setBatchResult(result);
      setActiveBatchProgress(result.batch ?? null);
      setJobListSummaryLabel("批量创建");
      setJobListTotalCount(result.jobs.length);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  async function loadDebugJobs(status?: string, sort?: string) {
    setError("");
    try {
      const result = await fetchDebugJobs(status, jobListLimit, undefined, sort);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setActiveBatchProgress(null);
      setJobListSummaryLabel(sort === "created_at_desc" ? "最新任务" : status === "failed" ? "失败任务" : "队列任务");
      setJobListTotalCount(result.total_count);
      setActiveJobStatusFilter(status);
      setActiveJobSort(sort);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  async function loadMoreDebugJobs() {
    setError("");
    try {
      const result = await fetchDebugJobs(activeJobStatusFilter, jobListLimit, batchJobs.length, activeJobSort);
      const jobs = [...batchJobs, ...result.jobs];
      setBatchResult({
        batch_id: batchResult?.batch_id ?? "",
        batch: batchResult?.batch,
        jobs,
        rejected_case_ids: batchResult?.rejected_case_ids ?? []
      });
      setJobListTotalCount(result.total_count);
      setBatchJobStatuses(Object.fromEntries(jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  async function loadBatchHistory() {
    setError("");
    try {
      const result = await fetchDebugBatches();
      setBatchHistory(result.batches);
      setActiveBatchProgress(result.batches[0] ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  async function changeActiveBatch(action: "pause" | "resume" | "cancel") {
    if (!activeBatchProgress) {
      return;
    }
    setError("");
    try {
      setActiveBatchProgress(await updateDebugBatchStatus(activeBatchProgress.batch.batch_id, action));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  function openBatchJob(job: DebugJobStatus | SubmittedDebugJob) {
    setSubmittedJob(job);
    setJobStatus("evidence_error_counts" in job ? job : null);
    setReport(null);
    setSpreadsheetWritebackResult(null);
    setSpreadsheetWritebackAudit(null);
    setAutoDebugClosureResult(null);
    setAutoDebugClosureMarkdown("");
    setAutoDebugClosureReportUrl("");
    setSelectedEvidence(null);
    setDebugRunStages([]);
    setEvidenceLedger([]);
  }

  async function startWorkerLoop() {
    setError("");
    try {
      setWorkerStatus(await startWorker());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  async function loadObservabilitySummary() {
    setError("");
    try {
      setObservabilitySummary(await fetchObservabilitySummary());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
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
      setError(caught instanceof Error ? caught.message : "未知错误");
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
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  async function importSpreadsheetRowsJson() {
    setError("");
    try {
      const parsedRows = JSON.parse(spreadsheetRowsJson) as unknown;
      if (!Array.isArray(parsedRows)) {
        throw new Error("飞书行 JSON 必须是数组");
      }
      const result = await importSpreadsheetRows(parsedRows as Array<Record<string, unknown>>);
      setSpreadsheetImportResult(result);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setJobListSummaryLabel("批量创建");
      setJobListTotalCount(result.jobs.length);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  function useSpreadsheetUrl() {
    setError("");
    try {
      const reference = parseLarkSpreadsheetUrl(spreadsheetUrl);
      setSpreadsheetId(reference.spreadsheetId);
      setSheetId(reference.sheetId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }


  async function stopWorkerLoop() {
    setError("");
    try {
      setWorkerStatus(await stopWorker());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  return (
    <div ref={motionScopeRef} className="app-container" data-motion-scope="debug-console">
      <TerminalDataStream />
      <FloatingAssistant />
      <aside className="app-sidebar" data-gsap-reveal>
        <div className="app-sidebar__header">
          <div className="app-logo">Harness Debug</div>
        </div>
        <nav className="app-sidebar__nav" aria-label="主导航">
          <button className={activeTab === "workspace" ? "active" : ""} onClick={() => selectTab("workspace")}>
            调查工作区
          </button>
          <button className={activeTab === "intake" ? "active" : ""} onClick={() => selectTab("intake")}>
            数据导入
          </button>
          <button className={activeTab === "operations" ? "active" : ""} onClick={() => selectTab("operations")}>
            操作监控
          </button>
          <button className={activeTab === "writeback" ? "active" : ""} onClick={() => selectTab("writeback")}>
            回写同步
          </button>
        </nav>
        <div className="app-sidebar__footer">
          <button className="app-sidebar__primary-action" type="button" aria-label="提交调试任务" onClick={submitJob}>
            + 提交调试任务
          </button>
        </div>
      </aside>

      <main className="app-main" data-anime-flow>
        <header className="app-main__header">
          <div>
            <h1>
              {activeTab === "workspace" && "调查工作区"}
              {activeTab === "intake" && "数据导入"}
              {activeTab === "operations" && "操作监控"}
              {activeTab === "writeback" && "回写同步"}
            </h1>
            <p className="app-main__subtitle">基于证据驱动的模型坏案排查与修复操作台</p>
          </div>
        </header>

        <div className="app-main__content">
          {error ? <p role="alert" className="error-message">{error}</p> : null}

          {activeTab === "operations" && (
            <div className="view-section" id="operations">
              <WorkerControlsPanel status={workerStatus} onStart={startWorkerLoop} onStop={stopWorkerLoop} />
              <section id="observability" aria-label="监控面板">
                <h2>运行监控</h2>
                <button type="button" onClick={() => void loadObservabilitySummary()}>
                  加载监控概览
                </button>
                <button type="button" onClick={() => void loadProductionReadiness()}>
                  加载生产运行就绪
                </button>
                <button type="button" onClick={() => void loadLarkBotPreflight()}>
                  加载机器人上线预检
                </button>
                <button type="button" onClick={() => void loadLarkBotGoLiveGate()}>
                  加载机器人真实上线门禁
                </button>
                <button type="button" onClick={() => void loadPilotGate()}>
                  加载试点准入评估
                </button>
                <button type="button" onClick={() => void loadLarkBotPendingCommands("pending")}>
                  加载机器人命令
                </button>
                <button type="button" onClick={() => void loadLarkNotificationOutbox("pending")}>
                  加载飞书通知 Outbox
                </button>
                <button type="button" onClick={() => void loadLarkBotBadcaseDrafts("ready_for_confirmation")}>
                  加载 badcase 草稿
                </button>
                {observabilitySummary ? (
                  <ObservabilitySummaryPanel
                    summary={observabilitySummary}
                    onLoadFailedJobs={() => void loadDebugJobs("failed")}
                    onLoadFailedWritebacks={() => void loadWritebackAudits("failed")}
                    onStartWorker={() => void startWorkerLoop()}
                    onClose={() => setObservabilitySummary(null)}
                  />
                ) : null}
                {productionReadiness ? <ProductionReadinessPanel readiness={productionReadiness} /> : null}
                {larkBotPreflight ? (
                  <LarkBotPreflightPanel
                    preflight={larkBotPreflight}
                    onAcknowledgeSetupItem={recordLarkBotSetupAcknowledgement}
                  />
                ) : null}
                {larkBotGoLiveGate ? <LarkBotGoLiveGatePanel gate={larkBotGoLiveGate} /> : null}
                {pilotGate ? <PilotGatePanel gate={pilotGate} /> : null}
                {larkBotPendingCommandList ? (
                  <LarkBotPendingCommandPanel
                    commands={larkBotPendingCommandList.commands}
                    totalCount={larkBotPendingCommandList.total_count}
                    activeStatus={activeLarkBotPendingStatus ?? null}
                    replyPreview={larkBotReplyPreview}
                    onLoadStatus={(status) => void loadLarkBotPendingCommands(status)}
                    onLoadMore={() => void loadMoreLarkBotPendingCommands()}
                    onConfirm={(commandId) => void confirmCurrentLarkBotPendingCommand(commandId)}
                    onPreviewReply={(commandId) => void previewCurrentLarkBotReply(commandId)}
                  />
                ) : null}
                {larkNotificationOutboxList ? (
                  <LarkNotificationOutboxPanel
                    notifications={larkNotificationOutboxList.notifications}
                    totalCount={larkNotificationOutboxList.total_count}
                    activeStatus={activeLarkNotificationOutboxStatus ?? null}
                    onLoadStatus={(status) => void loadLarkNotificationOutbox(status)}
                    onLoadMore={() => void loadMoreLarkNotificationOutbox()}
                  />
                ) : null}
                {larkBotBadcaseDraftList ? (
                  <LarkBotBadcaseDraftPanel
                    drafts={larkBotBadcaseDraftList.drafts}
                    totalCount={larkBotBadcaseDraftList.total_count}
                    activeStatus={activeLarkBotBadcaseDraftStatus ?? null}
                    lastConfirmation={larkBotBadcaseDraftConfirmation}
                    onLoadStatus={(status) => void loadLarkBotBadcaseDrafts(status)}
                    onLoadMore={() => void loadMoreLarkBotBadcaseDrafts()}
                    onConfirm={(draftId) => void confirmCurrentLarkBotBadcaseDraft(draftId)}
                  />
                ) : null}
              </section>
              <AgentTopologyPanel
                runStages={debugRunStages}
                agentModelConfig={agentModelConfig}
                modelCatalog={modelCatalog}
                onAgentModelConfigChange={setAgentModelConfig}
              />
            </div>
          )}

          {activeTab === "intake" && (
            <div className="view-section" id="case-intake">
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
            </div>
          )}

          {activeTab === "writeback" && (
            <div className="view-section" id="writeback">
              <SpreadsheetSyncPanel
                spreadsheetUrl={spreadsheetUrl}
                spreadsheetId={spreadsheetId}
                sheetId={sheetId}
                rerunRowIds={rerunRowIds}
                rerunAutoClosure={rerunAutoClosure}
                rerunWriteback={rerunWriteback}
                larkSpreadsheetStatus={larkSpreadsheetStatus}
                syncResult={spreadsheetSyncResult}
                writebackAuditSummary={spreadsheetWritebackAuditSummary}
                writebackAuditList={spreadsheetWritebackAuditList}
                activeWritebackAuditStatus={activeWritebackAuditStatus ?? null}
                larkOperationAuditList={larkOperationAuditList}
                activeLarkOperationAuditStatus={activeLarkOperationAuditStatus ?? null}
                larkScopeCheck={larkScopeCheck}
                larkAuthSession={larkAuthSession}
                writebackResult={spreadsheetWritebackResult}
                batchExportHref={spreadsheetBatchExportHref}
                onSpreadsheetUrlChange={setSpreadsheetUrl}
                onSpreadsheetIdChange={setSpreadsheetId}
                onSheetIdChange={setSheetId}
                onRerunRowIdsChange={setRerunRowIds}
                onRerunAutoClosureChange={setRerunAutoClosure}
                onRerunWritebackChange={setRerunWriteback}
                onUseSpreadsheetUrl={useSpreadsheetUrl}
                onCheckLarkStatus={() => void checkLarkStatus()}
                onSyncSpreadsheet={() => void syncSpreadsheet()}
                onRerunSpreadsheetRows={() => void rerunSelectedSpreadsheetRows()}
                onLoadWritebackAuditSummary={() => void loadWritebackAuditSummary()}
                onLoadWritebackAudits={(status) => void loadWritebackAudits(status)}
                onLoadLarkOperationAudits={(status) => void loadLarkOperationAudits(status)}
                onCheckLarkScopes={() => void checkLarkScopes()}
                onCreateLarkAuthSession={() => void createCurrentLarkAuthSession()}
                onCompleteLarkAuthSession={() => void completeCurrentLarkAuthSession()}
                onOpenAuditJob={(jobId) => void openWritebackAuditJob(jobId)}
                onRetryAudit={(auditToRetry) => void retryWritebackAudit(auditToRetry)}
                onLoadMoreWritebackAudits={() => void loadMoreWritebackAudits()}
                onLoadMoreLarkOperationAudits={() => void loadMoreLarkOperationAudits()}
              />
            </div>
          )}

          {activeTab === "workspace" && (
            <div className="view-section" id="investigation-workspace">
              <BatchJobsPanel
                caseIds={batchCaseIds}
                batchResult={batchResult}
                jobs={batchJobs}
                summaryLabel={jobListSummaryLabel}
                totalCount={jobListTotalCount ?? loadedJobCount}
                unloadedCount={unloadedJobCount}
                completedCount={completedBatchJobs}
                batchProgress={activeBatchProgress}
                batchHistory={batchHistory}
                exportHref={currentBatchExportHref}
                failedExportHref={failedJobsExportHref}
                newestExportHref={newestJobsExportHref}
                onCaseIdsChange={setBatchCaseIds}
                onSubmit={submitBatchJobs}
                onLoadJobs={(status, sort) => void loadDebugJobs(status, sort)}
                onStartWorker={startWorkerLoop}
                onPauseBatch={() => void changeActiveBatch("pause")}
                onResumeBatch={() => void changeActiveBatch("resume")}
                onCancelBatch={() => void changeActiveBatch("cancel")}
                onLoadBatches={() => void loadBatchHistory()}
                onLoadMore={() => void loadMoreDebugJobs()}
                onOpenJob={openBatchJob}
                onSelectEvidence={(jobId, evidenceId) => void selectBatchJobEvidence(jobId, evidenceId)}
              />
              {workerStatus ? (
                <section aria-label="工作区 worker 状态" className="worker-summary-inline">
                  <p>后台进程运行中：{workerStatus.running ? "是" : "否"}</p>
                  <p>后台进程已处理：{workerStatus.processed_count}</p>
                  <p>后台进程错误：{workerStatus.error_count}</p>
                </section>
              ) : null}
              <div className="agent-shell__investigation">
                {submittedJob ? (
                  <CurrentJobPanel
                    job={jobStatus ?? submittedJob}
                    runStages={debugRunStages}
                    evidenceLedger={evidenceLedger}
                    selectedEvidence={selectedEvidence}
                    onSelectEvidence={selectJobEvidence}
                    onLoadReport={() => void loadCurrentJobReport()}
                    onLoadRunStages={() => void loadCurrentDebugRunStages()}
                    onLoadEvidenceLedger={() => void loadCurrentEvidenceLedger()}
                  />
                ) : null}
                {report ? (
                  <DebugReportWorkspace
                    report={report}
                    selectedEvidence={selectedEvidence}
                    recommendedActionStatusEvents={recommendedActionStatusEvents}
                    recommendedActionVerifications={recommendedActionVerifications}
                    recommendedActionVerificationResults={recommendedActionVerificationResults}
                    strategyFollowUps={strategyFollowUps}
                    targetedProbes={targetedProbes}
                    humanHandoffStatuses={humanHandoffStatuses}
                    writebackResult={spreadsheetWritebackResult}
                    writebackAudit={spreadsheetWritebackAudit}
                    writeConfirmation={larkWriteConfirmation}
                    onSelectEvidence={selectEvidence}
                    onWriteReport={() => void writeCurrentReportToSpreadsheet()}
                    onPrepareWriteConfirmation={() => void prepareCurrentWritebackConfirmation()}
                    onConfirmWriteReport={() => void confirmCurrentWritebackAndWrite()}
                    onLoadWritebackAudit={() => void loadCurrentWritebackAudit()}
                    onUpdateRecommendedActionStatus={(actionIndex, status) =>
                      void updateCurrentRecommendedActionStatus(actionIndex, status)
                    }
                    onUpdateHumanHandoffStatus={(targetId, status) => void updateCurrentHumanHandoffStatus(targetId, status)}
                    onVerifyRecommendedAction={(actionIndex) => void verifyCurrentRecommendedAction(actionIndex)}
                    onCreateStrategyFollowUp={(stage) => void createCurrentStrategyFollowUp(stage)}
                    onCreateTargetedProbe={(targetId) => void createCurrentTargetedProbe(targetId)}
                    onCreateFinalAttributionFollowUp={(targetId) => void createCurrentFinalAttributionFollowUp(targetId)}
                    onCreateFinalAttributionRecovery={(targetId) => void createCurrentFinalAttributionRecovery(targetId)}
                    onOpenStrategyFollowUp={(jobId) => void openStrategyFollowUpJob(jobId)}
                    onOpenTargetedProbe={(jobId) => void openStrategyFollowUpJob(jobId)}
                    autoDebugClosureResult={autoDebugClosureResult}
                    autoDebugClosureMarkdown={autoDebugClosureMarkdown}
                    autoDebugClosureReportUrl={autoDebugClosureReportUrl}
                    onRunAutoDebugClosure={() => void runCurrentAutoDebugClosure()}
                  />
                ) : submittedJob ? null : (
                  <div className="empty-state" style={{ marginTop: '1rem' }}>
                    <p className="empty-state__title">尚未选择任务</p>
                    <p>请从上方列表选择或提交一个新任务，开启排查与修复流程。</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
