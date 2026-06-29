import {
  describe,
  expect,
  it,
  vi,
  askProjectAssistant
} from "./client.test.setup";

describe("api client assistant", () => {
  it("asks the project assistant through the RAG chat endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          answer: "先去数据导入，再到调查工作台批量调试。",
          citations: [{ title: "使用流程", source: "workflow.md", snippet: "四个区域完成一次 badcase 调查。" }],
          model_provider: "local-rag",
          model_id: "retrieval-only"
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );

    const response = await askProjectAssistant("怎么开始？");

    expect(fetchMock).toHaveBeenCalledWith("/api/assistant/chat", {
      body: JSON.stringify({ question: "怎么开始？" }),
      headers: { "Content-Type": "application/json" },
      method: "POST"
    });
    expect(response.citations[0].source).toBe("workflow.md");
  });
});
