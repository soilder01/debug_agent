import {
  describe,
  expect,
  it,
  vi,
  debugJobExportUrl,
  fetchDebugBatchComparison,
  submitBatchDebugJobs
} from "./client.test.setup";

describe("api client batches", () => {
  it("loads A/B comparison for selected batches", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          generated_at: "2026-06-22T00:00:00+00:00",
          batch_ids: ["batch-a", "batch-b"],
          best_batch_id: "batch-a",
          summary: "推荐 batch-a",
          export_url: "/api/debug-batches/comparison.csv?batch_ids=batch-a,batch-b",
          items: [
            {
              batch_id: "batch-a",
              status: "completed",
              total_jobs: 10,
              model_profile: "公平复测=seedpro",
              model_runner_model: "seedpro",
              model_runner_locked: true,
              thinking_enabled_roles: ["report_root_cause"],
              success_rate: 0.9,
              p95_duration_ms: 1000,
              estimated_cost_units: 2,
              model_call_errors: 0,
              writeback_failed: 0,
              quality_score: 90,
              efficiency_score: 87,
              summary: "成功率 90%"
            }
          ]
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const comparison = await fetchDebugBatchComparison(["batch-a", "batch-b"]);

    expect(fetchMock).toHaveBeenCalledWith("/api/debug-batches/comparison?batch_ids=batch-a%2Cbatch-b");
    expect(comparison.best_batch_id).toBe("batch-a");
    expect(comparison.items[0].model_runner_locked).toBe(true);
  });


  it("builds debug job export URLs for local downloads", () => {
    expect(debugJobExportUrl({ jobIds: ["job-1", "job-2"] })).toBe(
      "/api/exports/debug-jobs.zip?job_ids=job-1%2Cjob-2"
    );
    expect(debugJobExportUrl({ status: "failed", limit: 50 })).toBe(
      "/api/exports/debug-jobs.zip?status=failed&limit=50"
    );
    expect(debugJobExportUrl({ limit: 50, sort: "created_at_desc" })).toBe(
      "/api/exports/debug-jobs.zip?limit=50&sort=created_at_desc"
    );
  });


  it("submits batch jobs with agent model configuration", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ jobs: [], rejected_case_ids: [] }), {
        status: 202,
        headers: { "Content-Type": "application/json" }
      })
    );

    await submitBatchDebugJobs({
      caseIds: ["case-1"],
      maxConcurrency: 2,
      agentModelConfig: {
        roles: {
          model_runner: {
            provider: "ark",
            model_id: "seedpro-source",
            thinking: "disabled",
            locked: true
          }
        }
      }
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/debug-jobs/batch", {
      body: JSON.stringify({
        case_ids: ["case-1"],
        max_concurrency: 2,
        agent_model_config: {
          roles: {
            model_runner: {
              provider: "ark",
              model_id: "seedpro-source",
              thinking: "disabled",
              locked: true
            }
          }
        }
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
  });
});
