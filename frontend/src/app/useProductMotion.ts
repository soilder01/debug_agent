import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import { animate, stagger } from "animejs";
import gsap from "gsap";

gsap.registerPlugin(useGSAP);

function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

export function runProductMotion(scope: HTMLElement) {
  if (prefersReducedMotion()) {
    return undefined;
  }

  // Enhanced GSAP reveal with subtle vertical slide and blur-like effect
  gsap.from(scope.querySelectorAll("[data-gsap-reveal]"), {
    duration: 1.2,
    ease: "power3.out",
    opacity: 0,
    stagger: 0.15,
    y: 40,
    clearProps: "all"
  });

  // Flow animation for sections and content cards
  const animeFlow = animate(scope.querySelectorAll("[data-anime-flow]"), {
    opacity: [0, 1],
    translateY: [30, 0],
    delay: stagger(100, { start: 200 }),
    duration: 800,
    easing: "out(5)"
  });

  return () => {
    animeFlow.revert();
  };
}

export function useProductMotion() {
  const scopeRef = useRef<HTMLDivElement | null>(null);

  useGSAP(
    () => {
      const scope = scopeRef.current;
      if (!scope || prefersReducedMotion()) {
        return;
      }

      return runProductMotion(scope);
    },
    { scope: scopeRef }
  );

  return scopeRef;
}
