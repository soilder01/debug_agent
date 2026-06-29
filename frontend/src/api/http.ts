export async function buildHttpErrorMessage(prefix: string, response: Response): Promise<string> {
  let detail = "";
  try {
    const body = (await response.json()) as { detail?: unknown };
    detail = typeof body.detail === "string" ? body.detail : "";
  } catch {
    detail = "";
  }
  return detail ? `${prefix}: ${response.status} - ${detail}` : `${prefix}: ${response.status}`;
}
