import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => {
  const animeRevert = vi.fn();
  return {
    gsapFrom: vi.fn(),
    animeRevert,
    animeAnimate: vi.fn(() => ({ revert: animeRevert })),
    animeStagger: vi.fn(() => "staggered-delay")
  };
});

vi.mock("gsap", () => ({
  default: {
    from: mocks.gsapFrom,
    registerPlugin: vi.fn()
  }
}));

vi.mock("@gsap/react", () => ({
  useGSAP: vi.fn()
}));

vi.mock("animejs", () => ({
  animate: mocks.animeAnimate,
  stagger: mocks.animeStagger
}));

import { runProductMotion } from "./useProductMotion";

afterEach(() => {
  vi.restoreAllMocks();
  mocks.gsapFrom.mockClear();
  mocks.animeAnimate.mockClear();
  mocks.animeRevert.mockClear();
  mocks.animeStagger.mockClear();
});

describe("runProductMotion", () => {
  it("uses selectors scoped to the motion root", () => {
    const outside = document.createElement("div");
    outside.innerHTML = `<div data-gsap-reveal>outside</div><div data-anime-flow>outside flow</div>`;
    document.body.appendChild(outside);
    const scope = document.createElement("main");
    scope.innerHTML = `<section data-gsap-reveal>inside</section><article data-anime-flow>inside flow</article>`;
    document.body.appendChild(scope);

    runProductMotion(scope);

    expect(mocks.gsapFrom).toHaveBeenCalledWith(scope.querySelectorAll("[data-gsap-reveal]"), expect.any(Object));
    expect(mocks.animeAnimate).toHaveBeenCalledWith(scope.querySelectorAll("[data-anime-flow]"), expect.any(Object));
    expect(mocks.gsapFrom.mock.calls[0][0]).not.toContain(outside.querySelector("[data-gsap-reveal]"));
  });

  it("skips animation work when reduced motion is preferred", () => {
    vi.spyOn(window, "matchMedia").mockReturnValue({ matches: true } as MediaQueryList);
    const scope = document.createElement("main");
    scope.innerHTML = `<button data-gsap-reveal>Submit debug job</button><section data-anime-flow>panel</section>`;

    const cleanup = runProductMotion(scope);

    expect(cleanup).toBeUndefined();
    expect(mocks.gsapFrom).not.toHaveBeenCalled();
    expect(mocks.animeAnimate).not.toHaveBeenCalled();
    expect(scope.querySelector("button")).not.toHaveStyle({ visibility: "hidden" });
  });

  it("does not use visibility hiding or pointer disabling animation options", () => {
    const scope = document.createElement("main");
    scope.innerHTML = `<button data-gsap-reveal>Submit debug job</button><section data-anime-flow>panel</section>`;

    runProductMotion(scope);

    expect(mocks.gsapFrom.mock.calls[0][1]).not.toHaveProperty("autoAlpha");
    expect(mocks.gsapFrom.mock.calls[0][1]).not.toHaveProperty("visibility");
    expect(mocks.gsapFrom.mock.calls[0][1]).not.toHaveProperty("pointerEvents");
    expect(scope.querySelector("button")).not.toHaveStyle({ visibility: "hidden" });
  });
});
