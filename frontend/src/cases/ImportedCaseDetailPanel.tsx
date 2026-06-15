import type { DebugCaseDetail } from "../api/client";
import { ActionRow } from "../ui/ProductPrimitives";

type ImportedCaseDetailPanelProps = {
  caseDetail: DebugCaseDetail;
  onCreateDebugJob: (caseId: string) => void;
};

export function ImportedCaseDetailPanel({ caseDetail, onCreateDebugJob }: ImportedCaseDetailPanelProps) {
  const hasExpectedOutput = caseDetail.expected_output && Object.keys(caseDetail.expected_output).length > 0;
  const hasOutputSchema = caseDetail.output_schema && Object.keys(caseDetail.output_schema).length > 0;

  return (
    <section aria-label="Selected case detail" className="case-detail">
      <h3>样本详情：{caseDetail.case_id}</h3>
      <ActionRow label="Selected case actions">
        <button type="button" onClick={() => onCreateDebugJob(caseDetail.case_id)}>
          Create debug job for {caseDetail.case_id}
        </button>
      </ActionRow>
      <p>图片：{caseDetail.image_uri}</p>
      <p>Prompt：{caseDetail.prompt}</p>
      <p>评分标准：{caseDetail.scoring_standard}</p>
      <ul aria-label="Golden answers">
        {caseDetail.golden_answer.answers.map((answer) => (
          <li key={answer.box_id}>
            标答 {answer.box_id}：{answer.student_answer}
          </li>
        ))}
      </ul>
      {hasExpectedOutput ? <p>期望输出：{JSON.stringify(caseDetail.expected_output)}</p> : null}
      {hasOutputSchema ? <p>输出 Schema：{JSON.stringify(caseDetail.output_schema)}</p> : null}
      {(caseDetail.box_regions ?? []).length > 0 ? (
        <ul aria-label="Box regions">
          {caseDetail.box_regions?.map((region) => (
            <li key={region.box_id}>
              区域 {region.box_id}：x={region.x}, y={region.y}, width={region.width}, height={region.height}, unit=
              {region.unit}, label={region.label || "无"}
            </li>
          ))}
        </ul>
      ) : null}
      <ul aria-label="Predictions">
        {caseDetail.predictions.map((prediction) => (
          <li key={prediction.trial}>
            预测 trial {prediction.trial}：score {prediction.score}
          </li>
        ))}
      </ul>
      <p>人工状态：{caseDetail.human_notes.debug_status || "未标记"}</p>
      <p>人工根因：{caseDetail.human_notes.root_cause || "未归因"}</p>
    </section>
  );
}
