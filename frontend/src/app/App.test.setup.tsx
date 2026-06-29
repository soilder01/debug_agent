import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

vi.setConfig({ testTimeout: 20_000 });

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

async function openTab(name: "调查工作区" | "数据导入" | "操作监控" | "回写同步") {
  await userEvent.click(screen.getByRole("button", { name }));
}

export { App, describe, expect, fireEvent, it, openTab, render, screen, userEvent, vi };
