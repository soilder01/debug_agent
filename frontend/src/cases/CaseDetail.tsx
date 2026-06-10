type CaseDetailProps = {
  caseId: string;
  status: string;
};

export function CaseDetail({ caseId, status }: CaseDetailProps) {
  return (
    <section>
      <h2>Case</h2>
      <p>样本 ID：{caseId}</p>
      <p>状态：{status}</p>
    </section>
  );
}