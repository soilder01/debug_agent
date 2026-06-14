type NativeWritebackFieldsProps = {
  fields: Record<string, string>;
};

export function NativeWritebackFields({ fields }: NativeWritebackFieldsProps) {
  const target = fields["影响目标"];
  const delta = fields["结构化差异"];
  const artifacts = fields["证据产物"];
  const recommendedActions = fields["推荐操作"];
  const actionItems = parseRecommendedActions(recommendedActions);

  if (!target && !delta && !artifacts && !recommendedActions) {
    return null;
  }

  return (
    <section aria-label="Native debug writeback">
      <h3>Native Debug Writeback</h3>
      {target ? <p>影响目标：{target}</p> : null}
      {delta ? <p>结构化差异：{delta}</p> : null}
      {artifacts ? <p>证据产物：{artifacts}</p> : null}
      {recommendedActions ? <p>推荐操作：{recommendedActions}</p> : null}
      {actionItems.length > 0 ? (
        <>
          <h4>Recommended Action Items</h4>
          <ul aria-label="Recommended action items">
            {actionItems.map((action) => (
              <li key={`${action.category}:${action.summary}`}>
                <p>类别：{action.category}</p>
                <p>优先级：{action.priority}</p>
                <p>摘要：{action.summary}</p>
                <p>详情：{action.detail}</p>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

type RecommendedActionItem = {
  category: string;
  priority: string;
  summary: string;
  detail: string;
};

function parseRecommendedActions(value: string | undefined): RecommendedActionItem[] {
  if (!value) {
    return [];
  }
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map(parseRecommendedActionLine)
    .filter((action): action is RecommendedActionItem => action !== null);
}

function parseRecommendedActionLine(line: string): RecommendedActionItem | null {
  const [categoryPriority, rest] = line.split("：", 2);
  const [category, priority] = categoryPriority.split("/", 2);
  if (!category || !priority || !rest) {
    return null;
  }
  const [summary, detail = ""] = rest.split(" - ", 2);
  if (!summary) {
    return null;
  }
  return {
    category,
    priority,
    summary,
    detail
  };
}
