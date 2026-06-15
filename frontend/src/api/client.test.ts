import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createFinalAttributionVerificationJob,
  createRecommendedActionVerificationJob,
  createStrategyFollowUpJob,
  createTargetedProbeJob,
  fetchHumanHandoffStatuses,
  fetchRecommendedActionStatuses,
  fetchStrategyFollowUpJobs,
  fetchTargetedProbeJobs,
  updateHumanHandoffStatus,
  updateRecommendedActionStatus
} from "./client";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api client recommended action status", () => {
  it("patches recommended action status with reviewer context", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          job_id: "job-1",
          action_index: 2,
          status: "accepted",
          actor: "qa-reviewer",
          note: "approved prompt fix",
          created_at: "2026-06-14T00:00:00+00:00",
          updated_at: "2026-06-14T00:00:01+00:00"
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const status = await updateRecommendedActionStatus("job-1", 2, {
      status: "accepted",
      actor: "qa-reviewer",
      note: "approved prompt fix"
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1/recommended-actions/2/status", {
      body: JSON.stringify({
        status: "accepted",
        actor: "qa-reviewer",
        note: "approved prompt fix"
      }),
      headers: { "Content-Type": "application/json" },
      method: "PATCH"
    });
    expect(status.status).toBe("accepted");
    expect(status.action_index).toBe(2);
  });

  it("fetches recommended action status events", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          statuses: [
            {
              job_id: "job-1",
              action_index: 0,
              status: "accepted",
              actor: "qa-reviewer",
              note: "approved",
              created_at: "2026-06-14T00:00:00+00:00",
              updated_at: "2026-06-14T00:00:01+00:00"
            }
          ],
          events: [
            {
              event_id: 7,
              job_id: "job-1",
              action_index: 0,
              status: "accepted",
              actor: "qa-reviewer",
              note: "approved",
              created_at: "2026-06-14T00:00:01+00:00"
            }
          ],
          verifications: [
            {
              job_id: "job-1",
              action_index: 0,
              verification_job_id: "job-verify-1",
              actor: "qa-reviewer",
              note: "verify prompt fix",
              created_at: "2026-06-14T00:00:02+00:00"
            }
          ],
          verification_results: [
            {
              job_id: "job-1",
              action_index: 0,
              verification_job_id: "job-verify-1",
              result: "resolved",
              source_success_rate: 0.5,
              verification_success_rate: 1,
              source_root_cause: "single_modality_capability_gap",
              verification_root_cause: "output_mismatch",
              summary: "验证任务通过率 100%，高于原任务 50%，推荐操作可能已修复该问题。"
            }
          ]
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await fetchRecommendedActionStatuses("job-1");

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1/recommended-actions/statuses");
    expect(response.events).toHaveLength(1);
    expect(response.events[0].event_id).toBe(7);
    expect(response.verifications[0].verification_job_id).toBe("job-verify-1");
    expect(response.verification_results[0].result).toBe("resolved");
  });

  it("creates recommended action verification jobs with reviewer context", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          job_id: "job-1",
          action_index: 0,
          verification_job_id: "job-verify-1",
          actor: "qa-reviewer",
          note: "verify prompt fix",
          created_at: "2026-06-14T00:00:02+00:00",
          verification_job: {
            job_id: "job-verify-1",
            case_id: "case-1",
            status: "created"
          }
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await createRecommendedActionVerificationJob("job-1", 0, {
      actor: "qa-reviewer",
      note: "verify prompt fix"
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1/recommended-actions/0/verification-jobs", {
      body: JSON.stringify({
        actor: "qa-reviewer",
        note: "verify prompt fix"
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(response.verification_job.job_id).toBe("job-verify-1");
  });

  it("creates strategy follow-up jobs with operator context", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          source_job_id: "job-1",
          stage: "ablation_expansion",
          planned_steps: "strategy_ablation_expansion_probe",
          follow_up_job_id: "job-follow-up-1",
          actor: "strategy-operator",
          note: "run ablation expansion",
          created_at: "2026-06-15T00:00:02+00:00",
          follow_up_job: {
            job_id: "job-follow-up-1",
            case_id: "case-1",
            status: "created"
          }
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await createStrategyFollowUpJob("job-1", "ablation_expansion", {
      actor: "strategy-operator",
      note: "run ablation expansion"
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1/strategy-follow-ups/ablation_expansion/debug-jobs", {
      body: JSON.stringify({
        actor: "strategy-operator",
        note: "run ablation expansion"
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(response.follow_up_job.job_id).toBe("job-follow-up-1");
  });

  it("fetches strategy follow-up job lineage", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          follow_ups: [
            {
              source_job_id: "job-1",
              stage: "ablation_expansion",
              planned_steps: "strategy_ablation_expansion_probe",
              follow_up_job_id: "job-follow-up-1",
              actor: "strategy-operator",
              note: "run ablation expansion",
              created_at: "2026-06-15T00:00:02+00:00",
              outcome: "needs_escalation",
              success_rate: 0,
              summary: "Strategy follow-up job still failed; escalation is recommended.",
              escalation: "Run single-modality capability probes before keeping cross-modal attribution."
            }
          ]
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await fetchStrategyFollowUpJobs("job-1");

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1/strategy-follow-ups");
    expect(response.follow_ups[0].follow_up_job_id).toBe("job-follow-up-1");
    expect(response.follow_ups[0].outcome).toBe("needs_escalation");
  });

  it("creates targeted probe jobs with operator context", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          source_job_id: "job-1",
          target_id: "multimodal:conflict:1",
          planned_steps: "targeted_multimodal_conflict_probe",
          probe_job_id: "job-targeted-probe-1",
          actor: "targeted-operator",
          note: "probe conflict target",
          created_at: "2026-06-15T00:00:02+00:00",
          probe_job: {
            job_id: "job-targeted-probe-1",
            case_id: "case-1",
            status: "created"
          }
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await createTargetedProbeJob("job-1", "multimodal:conflict:1", {
      actor: "targeted-operator",
      note: "probe conflict target"
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1/targeted-probes/multimodal%3Aconflict%3A1/debug-jobs", {
      body: JSON.stringify({
        actor: "targeted-operator",
        note: "probe conflict target"
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(response.probe_job.job_id).toBe("job-targeted-probe-1");
  });

  it("fetches targeted probe job history with outcomes", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          probes: [
            {
              source_job_id: "job-1",
              target_id: "multimodal:conflict:1",
              planned_steps: "targeted_multimodal_conflict_probe",
              probe_job_id: "job-targeted-probe-1",
              actor: "targeted-operator",
              note: "probe conflict target",
              created_at: "2026-06-15T00:00:02+00:00",
              outcome: "target_still_failing",
              success_rate: 0,
              summary: "Targeted probe still failed on multimodal:conflict:1; escalation is recommended.",
              escalation: "Run deeper localized replay or modality-specific probes for multimodal:conflict:1."
            }
          ]
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await fetchTargetedProbeJobs("job-1");

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1/targeted-probes");
    expect(response.probes[0].probe_job_id).toBe("job-targeted-probe-1");
    expect(response.probes[0].outcome).toBe("target_still_failing");
  });

  it("patches human handoff status with reviewer context", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          job_id: "job-1",
          target_id: "multimodal:conflict:1",
          status: "in_progress",
          actor: "human-debugger",
          note: "reviewing full probe chain",
          created_at: "2026-06-15T00:00:00+00:00",
          updated_at: "2026-06-15T00:00:01+00:00"
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const status = await updateHumanHandoffStatus("job-1", "multimodal:conflict:1", {
      status: "in_progress",
      actor: "human-debugger",
      note: "reviewing full probe chain"
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1/human-handoffs/multimodal%3Aconflict%3A1/status", {
      body: JSON.stringify({
        status: "in_progress",
        actor: "human-debugger",
        note: "reviewing full probe chain"
      }),
      headers: { "Content-Type": "application/json" },
      method: "PATCH"
    });
    expect(status.status).toBe("in_progress");
    expect(status.target_id).toBe("multimodal:conflict:1");
  });

  it("fetches human handoff statuses", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          statuses: [
            {
              job_id: "job-1",
              target_id: "multimodal:conflict:1",
              status: "resolved",
              actor: "human-debugger",
              note: "prompt issue confirmed",
              created_at: "2026-06-15T00:00:00+00:00",
              updated_at: "2026-06-15T00:00:01+00:00"
            }
          ]
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await fetchHumanHandoffStatuses("job-1");

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1/human-handoffs/statuses");
    expect(response.statuses[0].status).toBe("resolved");
  });

  it("creates final attribution verification jobs with operator context", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          source_job_id: "job-1",
          stage: "final_attribution:multimodal:conflict:1",
          planned_steps: "final_attribution_prompt_verification",
          follow_up_job_id: "job-final-verify-1",
          actor: "final-attribution-operator",
          note: "verify prompt attribution fix",
          created_at: "2026-06-15T00:00:02+00:00",
          follow_up_job: {
            job_id: "job-final-verify-1",
            case_id: "case-1",
            status: "created"
          }
        }),
        { status: 202, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await createFinalAttributionVerificationJob("job-1", "multimodal:conflict:1", {
      actor: "final-attribution-operator",
      note: "verify prompt attribution fix"
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/job-1/final-attributions/multimodal%3Aconflict%3A1/verification-jobs",
      {
        body: JSON.stringify({
          actor: "final-attribution-operator",
          note: "verify prompt attribution fix"
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST"
      }
    );
    expect(response.follow_up_job_id).toBe("job-final-verify-1");
  });
});
