type BatchJobControlsPanelProps = {
  caseIds: string;
  onCaseIdsChange: (value: string) => void;
  onSubmit: () => void;
  onLoadJobs: (status?: string, sort?: string) => void;
  showHeading?: boolean;
};

export function BatchJobControlsPanel({
  caseIds,
  onCaseIdsChange,
  onSubmit,
  onLoadJobs,
  showHeading = true
}: BatchJobControlsPanelProps) {
  return (
    <>
      {showHeading ? <h2>Batch Jobs</h2> : null}
      <label htmlFor="batch-case-ids">Batch case ids</label>
      <textarea id="batch-case-ids" value={caseIds} onChange={(event) => onCaseIdsChange(event.target.value)} />
      <button type="button" onClick={onSubmit}>
        Submit batch jobs
      </button>
      <button type="button" onClick={() => onLoadJobs(undefined, undefined)}>
        Load debug jobs
      </button>
      <button type="button" onClick={() => onLoadJobs("failed", undefined)}>
        Load failed jobs
      </button>
      <button type="button" onClick={() => onLoadJobs(undefined, "created_at_desc")}>
        Load newest debug jobs
      </button>
    </>
  );
}
