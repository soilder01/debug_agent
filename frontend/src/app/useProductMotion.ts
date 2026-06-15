import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import { animate, stagger } from "animejs";
import gsap from "gsap";

gsap.registerPlugin(useGSAP);

function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

export function useProductMotion() {
  const scopeRef = useRef<HTMLElement | null>(null);

  useGSAP(
    () => {
      const scope = scopeRef.current;
      if (!scope || prefersReducedMotion()) {
        return;
      }

      gsap.from(scope.querySelectorAll("[data-gsap-reveal]"), {
        duration: 0.55,
        ease: "power3.out",
        opacity: 0,
        stagger: 0.08,
        y: 18
      });

      const animeFlow = animate(scope.querySelectorAll("[data-anime-flow]"), {
        opacity: [0, 1],
        translateY: [12, 0],
        delay: stagger(45),
        duration: 520,
        easing: "out(3)"
      });

      return () => {
        animeFlow.revert();
      };
    },
    { scope: scopeRef }
  );

  return scopeRef;
}
