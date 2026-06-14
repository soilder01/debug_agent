import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchRecommendedActionStatuses, updateRecommendedActionStatus } from "./client";

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
          ]
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await fetchRecommendedActionStatuses("job-1");

    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1/recommended-actions/statuses");
    expect(response.events).toHaveLength(1);
    expect(response.events[0].event_id).toBe(7);
  });
});
