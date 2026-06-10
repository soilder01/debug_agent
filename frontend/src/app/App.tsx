import { useState } from "react";

import { debugFixtureCase, type DebugReport } from "../api/client";
import { CaseDetail } from "../cases/CaseDetail";
import { ExperimentTimeline } from "../experiments/ExperimentTimeline";
import { ReportPanel } from "../reports/ReportPanel";

export function App() {
  const [report, setReport] = useState<DebugReport | null>(null);
  const [error, setError] = useState<string>("");

  async function runDebug() {
    setError("");
    try {
      setReport(await debugFixtureCase("handwrite233"));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unknown error");
    }
  }

  return (
    <main>
      <h1>Handwriting OCR Debug Agent</h1>
      <button type="button" onClick={runDebug}>
        Run single-case debug
      </button>
      {error ? <p role="alert">{error}</p> : null}
      {report ? (
        <>
          <CaseDetail caseId={report.case_id} status={report.status} />
          <ExperimentTimeline
            experiments={report.planned_experiments}
            summary={report.experiment_summary}
          />
          <ReportPanel report={report} />
        </>
      ) : (
        <p>点击按钮运行第一条可验证 debug 闭环。</p>
      )}
    </main>
  );
}
