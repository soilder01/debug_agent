import type { Dispatch, SetStateAction } from "react";

import {
  confirmLarkWriteConfirmation,
  createFinalAttributionRecoveryJob,
  createFinalAttributionVerificationJob,
  createJobReportWritebackConfirmation,
  createRecommendedActionVerificationJob,
  createStrategyFollowUpJob,
  createTargetedProbeJob,
  fetchDebugRunStages,
  fetchEvidenceDetail,
  fetchEvidenceLedger,
  fetchHumanHandoffStatuses,
  fetchJobEvidenceDetail,
  fetchJobReport,
  fetchJobStatus,
  fetchRecommendedActionStatuses,
  fetchSpreadsheetWritebackAudit,
  fetchStrategyFollowUpJobs,
  fetchTargetedProbeJobs,
  runAutoDebugClosureReport,
  type AutoDebugClosureResult,
  type DebugJobStatus,
  type DebugReport,
  type DebugRunStage,
  type EvidenceLedgerRecord,
  type ExperimentEvidence,
  type HumanHandoffStatus,
  type HumanHandoffStatusValue,
  type LarkWriteConfirmation,
  type RecommendedActionStatusEvent,
  type RecommendedActionStatusValue,
  type RecommendedActionVerification,
  type RecommendedActionVerificationResult,
  type SpreadsheetWritebackAudit,
  type SpreadsheetWritebackResult,
  type StrategyFollowUpJob,
  type SubmittedDebugJob,
  type TargetedProbeJob,
  updateHumanHandoffStatus,
  updateRecommendedActionStatus,
  writeJobReportToSpreadsheet,
} from "../api/client";
import { localDevActor } from "./App.config";

type UseAppReportActionsArgs = {
  report: DebugReport | null;
  submittedJob: SubmittedDebugJob | null;
  jobStatus: DebugJobStatus | null;
  spreadsheetUrl: string;
  spreadsheetId: string;
  sheetId: string;
  larkWriteConfirmation: LarkWriteConfirmation | null;
  setError: Dispatch<SetStateAction<string>>;
  setSubmittedJob: Dispatch<SetStateAction<SubmittedDebugJob | null>>;
  setJobStatus: Dispatch<SetStateAction<DebugJobStatus | null>>;
  setReport: Dispatch<SetStateAction<DebugReport | null>>;
  setDebugRunStages: Dispatch<SetStateAction<DebugRunStage[]>>;
  setEvidenceLedger: Dispatch<SetStateAction<EvidenceLedgerRecord[]>>;
  setSelectedEvidence: Dispatch<SetStateAction<ExperimentEvidence | null>>;
  setSpreadsheetWritebackResult: Dispatch<SetStateAction<SpreadsheetWritebackResult | null>>;
  setSpreadsheetWritebackAudit: Dispatch<SetStateAction<SpreadsheetWritebackAudit | null>>;
  setLarkWriteConfirmation: Dispatch<SetStateAction<LarkWriteConfirmation | null>>;
  setRecommendedActionStatusEvents: Dispatch<SetStateAction<RecommendedActionStatusEvent[]>>;
  setRecommendedActionVerifications: Dispatch<SetStateAction<RecommendedActionVerification[]>>;
  setRecommendedActionVerificationResults: Dispatch<SetStateAction<RecommendedActionVerificationResult[]>>;
  setStrategyFollowUps: Dispatch<SetStateAction<StrategyFollowUpJob[]>>;
  setTargetedProbes: Dispatch<SetStateAction<TargetedProbeJob[]>>;
  setHumanHandoffStatuses: Dispatch<SetStateAction<HumanHandoffStatus[]>>;
  setAutoDebugClosureResult: Dispatch<SetStateAction<AutoDebugClosureResult | null>>;
  setAutoDebugClosureMarkdown: Dispatch<SetStateAction<string>>;
  setAutoDebugClosureReportUrl: Dispatch<SetStateAction<string>>;
};

export function useAppReportActions({
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
}: UseAppReportActionsArgs) {
  async function loadCurrentDebugRunStages() {
    const currentJob = jobStatus ?? submittedJob;
    if (!currentJob) {
      return;
    }
    setError("");
    try {
      setDebugRunStages((await fetchDebugRunStages(currentJob.job_id)).stages);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadCurrentEvidenceLedger() {
    const currentJob = jobStatus ?? submittedJob;
    if (!currentJob) {
      return;
    }
    setError("");
    try {
      setEvidenceLedger((await fetchEvidenceLedger(currentJob.job_id)).records);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
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
      setError(caught instanceof Error ? caught.message : "未知错误");
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
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function loadCurrentJobReport() {
    const currentJob = jobStatus ?? submittedJob;
    if (!currentJob) {
      return;
    }
    setError("");
    try {
      const loadedReport = await fetchJobReport(currentJob.job_id);
      setReport(loadedReport);
      if (loadedReport.job_id && (loadedReport.recommended_actions ?? []).length > 0) {
        const actionStatuses = await fetchRecommendedActionStatuses(loadedReport.job_id);
        setRecommendedActionStatusEvents(actionStatuses.events ?? []);
        setRecommendedActionVerifications(actionStatuses.verifications ?? []);
        setRecommendedActionVerificationResults(actionStatuses.verification_results ?? []);
      } else {
        setRecommendedActionStatusEvents([]);
        setRecommendedActionVerifications([]);
        setRecommendedActionVerificationResults([]);
      }
      if (loadedReport.job_id && (loadedReport.follow_up_experiments ?? []).length > 0) {
        const followUps = await fetchStrategyFollowUpJobs(loadedReport.job_id);
        setStrategyFollowUps(followUps.follow_ups ?? []);
      } else {
        setStrategyFollowUps([]);
      }
      if (
        loadedReport.job_id &&
        (loadedReport.follow_up_experiments ?? []).some((followUp) =>
          followUp.source === "targeted_probe" || followUp.source === "targeted_probe_outcome"
        )
      ) {
        const probes = await fetchTargetedProbeJobs(loadedReport.job_id);
        setTargetedProbes(probes.probes ?? []);
      } else {
        setTargetedProbes([]);
      }
      if (loadedReport.job_id && (loadedReport.human_handoff_requests ?? []).length > 0) {
        const handoffStatuses = await fetchHumanHandoffStatuses(loadedReport.job_id);
        setHumanHandoffStatuses(handoffStatuses.statuses ?? []);
      } else {
        setHumanHandoffStatuses([]);
      }
      setSpreadsheetWritebackResult(null);
      setSpreadsheetWritebackAudit(null);
      setAutoDebugClosureResult(null);
      setAutoDebugClosureMarkdown("");
      setAutoDebugClosureReportUrl("");
      setSelectedEvidence(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function selectBatchJobEvidence(jobId: string, evidenceId: string) {
    setError("");
    try {
      setSelectedEvidence(await fetchJobEvidenceDetail(jobId, evidenceId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function writeCurrentReportToSpreadsheet() {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      const reportUrl = `${window.location.origin}/api/jobs/${report.job_id}/report`;
      setSpreadsheetWritebackResult(
        await writeJobReportToSpreadsheet(report.job_id, reportUrl, {
          spreadsheetUrl,
          spreadsheetId,
          sheetId
        })
      );
      setSpreadsheetWritebackAudit(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function prepareCurrentWritebackConfirmation() {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      const reportUrl = `${window.location.origin}/api/jobs/${report.job_id}/report`;
      setLarkWriteConfirmation(
        await createJobReportWritebackConfirmation(report.job_id, {
          reportUrl,
          spreadsheetUrl,
          spreadsheetId,
          sheetId,
          actor: localDevActor,
          note: "人工确认前预检写回目标"
        })
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function confirmCurrentWritebackAndWrite() {
    if (!report?.job_id || !larkWriteConfirmation) {
      return;
    }
    setError("");
    try {
      const confirmed = await confirmLarkWriteConfirmation(larkWriteConfirmation.confirmation_id, {
        actor: localDevActor,
        note: "确认写回报告到飞书表格"
      });
      setLarkWriteConfirmation(confirmed);
      const reportUrl = `${window.location.origin}/api/jobs/${report.job_id}/report`;
      setSpreadsheetWritebackResult(
        await writeJobReportToSpreadsheet(report.job_id, reportUrl, {
          spreadsheetUrl,
          spreadsheetId,
          sheetId,
          requireConfirmation: true,
          confirmationId: confirmed.confirmation_id,
          actor: localDevActor,
          note: "已通过高风险写回确认"
        })
      );
      setSpreadsheetWritebackAudit(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
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
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function runCurrentAutoDebugClosure() {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      const reportUrl = `${window.location.origin}/api/jobs/${report.job_id}/report`;
      const result = await runAutoDebugClosureReport(report.job_id, {
        actor: localDevActor,
        note: "auto close video badcase",
        writeback: true,
        report_url: reportUrl
      });
      setAutoDebugClosureResult(result.closure);
      setAutoDebugClosureMarkdown(result.markdown);
      setAutoDebugClosureReportUrl(result.report_artifact_url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function updateCurrentRecommendedActionStatus(
    actionIndex: number,
    status: RecommendedActionStatusValue
  ) {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      const updatedStatus = await updateRecommendedActionStatus(report.job_id, actionIndex, {
        status,
        actor: localDevActor,
        note: ""
      });
      setReport((current) => {
        if (!current || current.job_id !== updatedStatus.job_id) {
          return current;
        }
        const recommendedActions = [...(current.recommended_actions ?? [])];
        const action = recommendedActions[actionIndex];
        if (!action) {
          return current;
        }
        recommendedActions[actionIndex] = {
          ...action,
          status: updatedStatus.status
        };
        return {
          ...current,
          recommended_actions: recommendedActions
        };
      });
      const actionStatuses = await fetchRecommendedActionStatuses(report.job_id);
      setRecommendedActionStatusEvents(actionStatuses.events ?? []);
      setRecommendedActionVerifications(actionStatuses.verifications ?? []);
      setRecommendedActionVerificationResults(actionStatuses.verification_results ?? []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function updateCurrentHumanHandoffStatus(targetId: string, status: HumanHandoffStatusValue) {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      const updatedStatus = await updateHumanHandoffStatus(report.job_id, targetId, {
        status,
        actor: localDevActor,
        note: ""
      });
      setHumanHandoffStatuses((current) => [
        ...current.filter(
          (handoffStatus) =>
            handoffStatus.job_id !== updatedStatus.job_id || handoffStatus.target_id !== updatedStatus.target_id
        ),
        updatedStatus
      ]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function verifyCurrentRecommendedAction(actionIndex: number) {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      const verification = await createRecommendedActionVerificationJob(report.job_id, actionIndex, {
        actor: localDevActor,
        note: ""
      });
      setSubmittedJob(verification.verification_job);
      setJobStatus(null);
      setSelectedEvidence(null);
      const actionStatuses = await fetchRecommendedActionStatuses(report.job_id);
      setRecommendedActionStatusEvents(actionStatuses.events ?? []);
      setRecommendedActionVerifications(actionStatuses.verifications ?? []);
      setRecommendedActionVerificationResults(actionStatuses.verification_results ?? []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function createCurrentStrategyFollowUp(stage: string) {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      const followUp = await createStrategyFollowUpJob(report.job_id, stage, {
        actor: localDevActor,
        note: ""
      });
      setSubmittedJob(
        followUp.follow_up_job ?? {
          job_id: followUp.follow_up_job_id,
          case_id: report.case_id,
          status: "created"
        }
      );
      setJobStatus(null);
      setReport(null);
      setStrategyFollowUps([]);
      setSelectedEvidence(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function createCurrentTargetedProbe(targetId: string) {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      const probe = await createTargetedProbeJob(report.job_id, targetId, {
        actor: localDevActor,
        note: ""
      });
      setSubmittedJob(probe.probe_job);
      setJobStatus(null);
      setReport(null);
      setStrategyFollowUps([]);
      setTargetedProbes([]);
      setSelectedEvidence(null);
      setSelectedEvidence(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function createCurrentFinalAttributionFollowUp(targetId: string) {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      const followUp = await createFinalAttributionVerificationJob(report.job_id, targetId, {
        actor: localDevActor,
        note: ""
      });
      setSubmittedJob(
        followUp.follow_up_job ?? {
          job_id: followUp.follow_up_job_id,
          case_id: report.case_id,
          status: "created"
        }
      );
      setJobStatus(null);
      setReport(null);
      setStrategyFollowUps([]);
      setTargetedProbes([]);
      setSelectedEvidence(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function createCurrentFinalAttributionRecovery(targetId: string) {
    if (!report?.job_id) {
      return;
    }
    setError("");
    try {
      const followUp = await createFinalAttributionRecoveryJob(report.job_id, targetId, {
        actor: localDevActor,
        note: ""
      });
      setSubmittedJob(
        followUp.follow_up_job ?? {
          job_id: followUp.follow_up_job_id,
          case_id: report.case_id,
          status: "created"
        }
      );
      setJobStatus(null);
      setReport(null);
      setStrategyFollowUps([]);
      setTargetedProbes([]);
      setSelectedEvidence(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }
  async function openStrategyFollowUpJob(jobId: string) {
    setError("");
    try {
      const status = await fetchJobStatus(jobId);
      setSubmittedJob(status);
      setJobStatus(status);
      setReport(null);
      setStrategyFollowUps([]);
      setTargetedProbes([]);
      setSpreadsheetWritebackResult(null);
      setSpreadsheetWritebackAudit(null);
      setAutoDebugClosureResult(null);
      setAutoDebugClosureMarkdown("");
      setAutoDebugClosureReportUrl("");
      setSelectedEvidence(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "未知错误");
    }
  }

  return {
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
  };
}
