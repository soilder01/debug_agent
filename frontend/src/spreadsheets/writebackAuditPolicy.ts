export function canRetryWritebackAudit(status: string): boolean {
  return status === "failed";
}

export function writebackRetryReason(status: string, errorMessage: string): string {
  if (status === "failed") {
    return errorMessage ? `last writeback failed: ${errorMessage}` : "last writeback failed";
  }
  if (status === "succeeded") {
    return "already succeeded";
  }
  if (errorMessage) {
    return errorMessage;
  }
  return "missing prerequisites";
}
