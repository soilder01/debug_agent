type CaseDetailProps = {
  jobId: string | null;
  caseId: string;
  status: string;
};

export function CaseDetail({ jobId, caseId, status }: CaseDetailProps) {
  return (
    <section>
      <h2>Case</h2>
      {jobId ? <p>Job ID：{jobId}</p> : null}
      <p>样本 ID：{caseId}</p>
      <p>状态：{status}</p>
    </section>
  );
}
