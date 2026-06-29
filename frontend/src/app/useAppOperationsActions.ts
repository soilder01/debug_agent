import type { Dispatch, SetStateAction } from "react";

import {
  acknowledgeLarkBotSetupItem,
  completeLarkAuthSession,
  confirmLarkBotBadcaseDraft,
  confirmLarkBotPendingCommand,
  createLarkAuthSession,
  fetchJobStatus,
  fetchLarkBotBadcaseDrafts,
  fetchLarkBotGoLiveGate,
  fetchLarkBotNotificationOutbox,
  fetchLarkBotPendingCommandReplyPreview,
  fetchLarkBotPendingCommands,
  fetchLarkBotPreflight,
  fetchLarkOperationAudits,
  fetchLarkScopeCheck,
  fetchLarkSpreadsheetStatus,
  fetchPilotGate,
  fetchProductionReadiness,
  fetchSpreadsheetWritebackAudits,
  fetchSpreadsheetWritebackAuditSummary,
  rerunSpreadsheetRows,
  syncSpreadsheetRows,
  type AutoDebugClosureResult,
  type BatchDebugJobResponse,
  type DebugBatchProgress,
  type DebugJobStatus,
  type DebugReport,
  type ExperimentEvidence,
  type LarkAuthSession,
  type LarkBotBadcaseDraftConfirmResponse,
  type LarkBotBadcaseDraftListResponse,
  type LarkBotGoLiveGate,
  type LarkBotPendingCommandListResponse,
  type LarkBotPreflight,
  type LarkBotReplyPayload,
  type LarkBotSetupAcknowledgementRequest,
  type LarkNotificationOutboxListResponse,
  type LarkOperationAuditListResponse,
  type LarkScopeCheckResponse,
  type LarkSpreadsheetStatus,
  type PilotGate,
  type ProductionReadiness,
  type SpreadsheetSyncResponse,
  type SpreadsheetWritebackAudit,
  type SpreadsheetWritebackAuditCounts,
  type SpreadsheetWritebackAuditListResponse,
  type SpreadsheetWritebackResult,
  type SubmittedDebugJob,
  writeJobReportToSpreadsheet,
} from "../api/client";
import { jobListLimit, localDevActor, parseRerunRowIds } from "./App.config";

type SelectTab = (tab: "workspace" | "intake" | "operations" | "writeback") => void;

type UseAppOperationsActionsArgs = {
  spreadsheetUrl: string;
  spreadsheetId: string;
  sheetId: string;
  rerunRowIds: string;
  rerunAutoClosure: boolean;
  rerunWriteback: boolean;
  activeWritebackAuditStatus: string | null | undefined;
  spreadsheetWritebackAuditList: SpreadsheetWritebackAuditListResponse | null;
  activeLarkOperationAuditStatus: string | null | undefined;
  larkOperationAuditList: LarkOperationAuditListResponse | null;
  activeLarkBotPendingStatus: string | null | undefined;
  larkBotPendingCommandList: LarkBotPendingCommandListResponse | null;
  activeLarkNotificationOutboxStatus: string | null | undefined;
  larkNotificationOutboxList: LarkNotificationOutboxListResponse | null;
  activeLarkBotBadcaseDraftStatus: string | null | undefined;
  larkBotBadcaseDraftList: LarkBotBadcaseDraftListResponse | null;
  larkAuthSession: LarkAuthSession | null;
  larkScopeCheck: LarkScopeCheckResponse | null;
  larkSpreadsheetStatus: LarkSpreadsheetStatus | null;
  selectTab: SelectTab;
  setError: Dispatch<SetStateAction<string>>;
  setBatchResult: Dispatch<SetStateAction<BatchDebugJobResponse | null>>;
  setJobListSummaryLabel: Dispatch<SetStateAction<string>>;
  setJobListTotalCount: Dispatch<SetStateAction<number | null>>;
  setBatchJobStatuses: Dispatch<SetStateAction<Record<string, DebugJobStatus | SubmittedDebugJob>>>;
  setActiveBatchProgress: Dispatch<SetStateAction<DebugBatchProgress | null>>;
  setLarkSpreadsheetStatus: Dispatch<SetStateAction<LarkSpreadsheetStatus | null>>;
  setSpreadsheetSyncResult: Dispatch<SetStateAction<SpreadsheetSyncResponse | null>>;
  setSpreadsheetWritebackResult: Dispatch<SetStateAction<SpreadsheetWritebackResult | null>>;
  setSpreadsheetWritebackAudit: Dispatch<SetStateAction<SpreadsheetWritebackAudit | null>>;
  setSpreadsheetWritebackAuditSummary: Dispatch<SetStateAction<SpreadsheetWritebackAuditCounts | null>>;
  setSpreadsheetWritebackAuditList: Dispatch<SetStateAction<SpreadsheetWritebackAuditListResponse | null>>;
  setActiveWritebackAuditStatus: Dispatch<SetStateAction<string | null | undefined>>;
  setLarkOperationAuditList: Dispatch<SetStateAction<LarkOperationAuditListResponse | null>>;
  setActiveLarkOperationAuditStatus: Dispatch<SetStateAction<string | null | undefined>>;
  setLarkBotPendingCommandList: Dispatch<SetStateAction<LarkBotPendingCommandListResponse | null>>;
  setActiveLarkBotPendingStatus: Dispatch<SetStateAction<string | null | undefined>>;
  setLarkNotificationOutboxList: Dispatch<SetStateAction<LarkNotificationOutboxListResponse | null>>;
  setActiveLarkNotificationOutboxStatus: Dispatch<SetStateAction<string | null | undefined>>;
  setLarkBotReplyPreview: Dispatch<SetStateAction<LarkBotReplyPayload | null>>;
  setLarkBotBadcaseDraftList: Dispatch<SetStateAction<LarkBotBadcaseDraftListResponse | null>>;
  setActiveLarkBotBadcaseDraftStatus: Dispatch<SetStateAction<string | null | undefined>>;
  setLarkBotBadcaseDraftConfirmation: Dispatch<SetStateAction<LarkBotBadcaseDraftConfirmResponse | null>>;
  setLarkScopeCheck: Dispatch<SetStateAction<LarkScopeCheckResponse | null>>;
  setLarkAuthSession: Dispatch<SetStateAction<LarkAuthSession | null>>;
  setProductionReadiness: Dispatch<SetStateAction<ProductionReadiness | null>>;
  setLarkBotPreflight: Dispatch<SetStateAction<LarkBotPreflight | null>>;
  setLarkBotGoLiveGate: Dispatch<SetStateAction<LarkBotGoLiveGate | null>>;
  setPilotGate: Dispatch<SetStateAction<PilotGate | null>>;
  setSubmittedJob: Dispatch<SetStateAction<SubmittedDebugJob | null>>;
  setJobStatus: Dispatch<SetStateAction<DebugJobStatus | null>>;
  setReport: Dispatch<SetStateAction<DebugReport | null>>;
  setAutoDebugClosureResult: Dispatch<SetStateAction<AutoDebugClosureResult | null>>;
  setAutoDebugClosureMarkdown: Dispatch<SetStateAction<string>>;
  setAutoDebugClosureReportUrl: Dispatch<SetStateAction<string>>;
  setSelectedEvidence: Dispatch<SetStateAction<ExperimentEvidence | null>>;
};

export function useAppOperationsActions({
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
}: UseAppOperationsActionsArgs) {
  async function checkLarkStatus() {
    setError("");
    try {
      setLarkSpreadsheetStatus(
        await fetchLarkSpreadsheetStatus(true, {
          spreadsheetUrl,
          spreadsheetId,
          sheetId
        })
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function syncSpreadsheet() {
    setError("");
    try {
      const result = await syncSpreadsheetRows(spreadsheetId, sheetId, true, 5, spreadsheetUrl);
      setSpreadsheetSyncResult(result);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setJobListSummaryLabel("Spreadsheet 同步任务");
      setJobListTotalCount(result.jobs.length);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function rerunSelectedSpreadsheetRows() {
    setError("");
    try {
      const rowIds = parseRerunRowIds(rerunRowIds);
      const result = await rerunSpreadsheetRows({
        spreadsheetId,
        sheetId,
        spreadsheetUrl,
        rowIds,
        baselineTrials: 5,
        autoRun: true,
        autoClosure: rerunAutoClosure,
        writeback: rerunWriteback
      });
      setSpreadsheetSyncResult(result);
      setBatchResult({ jobs: result.jobs, rejected_case_ids: [] });
      setJobListSummaryLabel("Spreadsheet 重跑任务");
      setJobListTotalCount(result.jobs.length);
      setBatchJobStatuses(Object.fromEntries(result.jobs.map((job) => [job.job_id, job])));
      setActiveBatchProgress(result.batch ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadWritebackAuditSummary() {
    setError("");
    try {
      setSpreadsheetWritebackAuditSummary(await fetchSpreadsheetWritebackAuditSummary());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadWritebackAudits(status: string | null) {
    setError("");
    try {
      setActiveWritebackAuditStatus(status);
      setSpreadsheetWritebackAuditList(await fetchSpreadsheetWritebackAudits(status ?? undefined, jobListLimit));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
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
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadLarkOperationAudits(status: string | null) {
    setError("");
    try {
      setActiveLarkOperationAuditStatus(status);
      setLarkOperationAuditList(await fetchLarkOperationAudits(status ?? undefined, jobListLimit));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadMoreLarkOperationAudits() {
    if (activeLarkOperationAuditStatus === undefined || !larkOperationAuditList) {
      return;
    }
    setError("");
    try {
      const nextPage = await fetchLarkOperationAudits(
        activeLarkOperationAuditStatus ?? undefined,
        jobListLimit,
        larkOperationAuditList.audits.length,
      );
      setLarkOperationAuditList({
        audits: [...larkOperationAuditList.audits, ...nextPage.audits],
        total_count: nextPage.total_count,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadLarkBotPendingCommands(status: string | null) {
    setError("");
    try {
      setActiveLarkBotPendingStatus(status);
      setLarkBotPendingCommandList(await fetchLarkBotPendingCommands(status ?? undefined, jobListLimit));
      setLarkBotReplyPreview(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadLarkNotificationOutbox(status: string | null) {
    setError("");
    try {
      setActiveLarkNotificationOutboxStatus(status);
      setLarkNotificationOutboxList(await fetchLarkBotNotificationOutbox(status ?? undefined, jobListLimit));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadMoreLarkNotificationOutbox() {
    if (activeLarkNotificationOutboxStatus === undefined || !larkNotificationOutboxList) {
      return;
    }
    setError("");
    try {
      const nextPage = await fetchLarkBotNotificationOutbox(
        activeLarkNotificationOutboxStatus ?? undefined,
        jobListLimit,
        larkNotificationOutboxList.notifications.length,
      );
      setLarkNotificationOutboxList({
        notifications: [...larkNotificationOutboxList.notifications, ...nextPage.notifications],
        total_count: nextPage.total_count,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadMoreLarkBotPendingCommands() {
    if (activeLarkBotPendingStatus === undefined || !larkBotPendingCommandList) {
      return;
    }
    setError("");
    try {
      const nextPage = await fetchLarkBotPendingCommands(
        activeLarkBotPendingStatus ?? undefined,
        jobListLimit,
        larkBotPendingCommandList.commands.length,
      );
      setLarkBotPendingCommandList({
        commands: [...larkBotPendingCommandList.commands, ...nextPage.commands],
        total_count: nextPage.total_count,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function confirmCurrentLarkBotPendingCommand(commandId: string) {
    setError("");
    try {
      const confirmed = await confirmLarkBotPendingCommand(commandId, {
        actor: localDevActor,
        note: "Web 控制台确认执行机器人命令"
      });
      setLarkBotPendingCommandList((current) =>
        current
          ? {
              ...current,
              commands: current.commands.map((command) => (command.command_id === commandId ? confirmed : command))
            }
          : current
      );
      setLarkBotReplyPreview(await fetchLarkBotPendingCommandReplyPreview(commandId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function previewCurrentLarkBotReply(commandId: string) {
    setError("");
    try {
      setLarkBotReplyPreview(await fetchLarkBotPendingCommandReplyPreview(commandId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadLarkBotBadcaseDrafts(status: string | null) {
    setError("");
    try {
      setActiveLarkBotBadcaseDraftStatus(status);
      setLarkBotBadcaseDraftList(await fetchLarkBotBadcaseDrafts(status ?? undefined, jobListLimit));
      setLarkBotBadcaseDraftConfirmation(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadMoreLarkBotBadcaseDrafts() {
    if (activeLarkBotBadcaseDraftStatus === undefined || !larkBotBadcaseDraftList) {
      return;
    }
    setError("");
    try {
      const nextPage = await fetchLarkBotBadcaseDrafts(
        activeLarkBotBadcaseDraftStatus ?? undefined,
        jobListLimit,
        larkBotBadcaseDraftList.drafts.length,
      );
      setLarkBotBadcaseDraftList({
        drafts: [...larkBotBadcaseDraftList.drafts, ...nextPage.drafts],
        total_count: nextPage.total_count,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function confirmCurrentLarkBotBadcaseDraft(draftId: string) {
    setError("");
    try {
      const confirmation = await confirmLarkBotBadcaseDraft(draftId, {
        actor: localDevActor,
        note: "Web 控制台确认提交 badcase 草稿",
        create_job: true
      });
      setLarkBotBadcaseDraftConfirmation(confirmation);
      setLarkBotBadcaseDraftList((current) =>
        current
          ? {
              ...current,
              drafts: current.drafts.map((draft) => (draft.draft_id === draftId ? confirmation.draft : draft))
            }
          : current
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function checkLarkScopes() {
    setError("");
    try {
      setLarkScopeCheck(await fetchLarkScopeCheck("sheets"));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function createCurrentLarkAuthSession() {
    setError("");
    try {
      const scopes = Array.from(
        new Set((larkScopeCheck?.requirements ?? []).flatMap((requirement) => requirement.required_scopes))
      );
      setLarkAuthSession(
        await createLarkAuthSession({
          identity: "user",
          profile: larkSpreadsheetStatus?.connector_profile ?? "",
          scopes,
          actor: localDevActor,
          note: "飞书用户授权会话"
        })
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function completeCurrentLarkAuthSession() {
    if (!larkAuthSession) {
      return;
    }
    setError("");
    try {
      setLarkAuthSession(
        await completeLarkAuthSession(larkAuthSession.auth_session_id, {
          actor: localDevActor,
          note: "已在飞书授权入口完成授权"
        })
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadProductionReadiness() {
    setError("");
    try {
      setProductionReadiness(await fetchProductionReadiness());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadLarkBotPreflight() {
    setError("");
    try {
      setLarkBotPreflight(await fetchLarkBotPreflight());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadLarkBotGoLiveGate() {
    setError("");
    try {
      setLarkBotGoLiveGate(await fetchLarkBotGoLiveGate());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function recordLarkBotSetupAcknowledgement(
    itemKey: string,
    request: LarkBotSetupAcknowledgementRequest
  ) {
    setError("");
    try {
      await acknowledgeLarkBotSetupItem(itemKey, request);
      setLarkBotPreflight(await fetchLarkBotPreflight());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
      throw caught;
    }
  }
  async function loadPilotGate() {
    setError("");
    try {
      setPilotGate(await fetchPilotGate());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
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
  async function retryWritebackAudit(audit: SpreadsheetWritebackAudit) {
    setError("");
    try {
      const reportUrl = `${window.location.origin}/api/jobs/${audit.job_id}/report`;
      const result = await writeJobReportToSpreadsheet(audit.job_id, reportUrl, {
        spreadsheetUrl,
        spreadsheetId,
        sheetId
      });
      setSpreadsheetWritebackResult(result);
      setSpreadsheetWritebackAudit(null);
      if (activeWritebackAuditStatus !== undefined) {
        setSpreadsheetWritebackAuditList(
          await fetchSpreadsheetWritebackAudits(activeWritebackAuditStatus ?? undefined, jobListLimit)
        );
      }
      setSpreadsheetWritebackAuditSummary(await fetchSpreadsheetWritebackAuditSummary());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  return {
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
  };
}
