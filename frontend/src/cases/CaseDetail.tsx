type CaseDetailProps = {
  jobId: string | null;
  caseId: string;
  status: string;
};

export function CaseDetail({ jobId, caseId, status }: CaseDetailProps) {
  return (
    <section>
      <h2>样本</h2>
      {jobId ? <p>任务 ID：{jobId}</p> : null}
      <p>样本 ID：{caseId}</p>
      <p>状态：{status}</p>
    </section>
  );
}
