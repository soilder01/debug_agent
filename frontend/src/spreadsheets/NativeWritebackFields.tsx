type NativeWritebackFieldsProps = {
  fields: Record<string, string>;
};

export function NativeWritebackFields({ fields }: NativeWritebackFieldsProps) {
  const target = fields["影响目标"];
  const delta = fields["结构化差异"];
  const artifacts = fields["证据产物"];

  if (!target && !delta && !artifacts) {
    return null;
  }

  return (
    <section aria-label="Native debug writeback">
      <h3>Native Debug Writeback</h3>
      {target ? <p>影响目标：{target}</p> : null}
      {delta ? <p>结构化差异：{delta}</p> : null}
      {artifacts ? <p>证据产物：{artifacts}</p> : null}
    </section>
  );
}
