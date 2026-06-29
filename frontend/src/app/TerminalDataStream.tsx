import { useEffect, useRef, useState } from "react";
import gsap from "gsap";

const LOG_TEMPLATES = [
  "INITIALIZING NEURAL NET...",
  "ESTABLISHING SECURE CONNECTION...",
  "BYPASSING FIREWALL PROXY...",
  "DECRYPTING PAYLOAD...",
  "ANALYZING METRICS...",
  "SYNCHRONIZING CLUSTER...",
  "ALLOCATING MEMORY BLOCKS...",
  "COMPILING EXECUTION GRAPH...",
  "ROUTING PACKETS TO AGENT...",
  "DETECTING ANOMALIES...",
];

const HEX_CHARS = "0123456789ABCDEF";

function generateHex() {
  let result = "0x";
  for (let i = 0; i < 8; i++) {
    result += HEX_CHARS[Math.floor(Math.random() * 16)];
  }
  return result;
}

function generateLogLine() {
  const timestamp = new Date().toISOString().substring(11, 23);
  const hex = generateHex();
  const template = LOG_TEMPLATES[Math.floor(Math.random() * LOG_TEMPLATES.length)];
  return `[${timestamp}] ${hex} :: ${template}`;
}

export function TerminalDataStream() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    // Initial logs
    const initialLogs = Array.from({ length: 15 }, generateLogLine);
    setLogs(initialLogs);

    // Continuous stream
    const interval = setInterval(() => {
      setLogs(prev => {
        const newLogs = [...prev, generateLogLine()];
        if (newLogs.length > 30) {
          return newLogs.slice(newLogs.length - 30);
        }
        return newLogs;
      });
    }, 400 + Math.random() * 800); // Random interval between 400-1200ms

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (containerRef.current) {
      // Smooth scroll to bottom
      gsap.to(containerRef.current, {
        scrollTop: containerRef.current.scrollHeight,
        duration: 0.5,
        ease: "power2.out"
      });
    }
  }, [logs]);

  return (
    <div
      className="terminal-data-stream"
      style={{
        position: "absolute",
        bottom: "0",
        right: "0",
        width: "350px",
        height: "250px",
        padding: "1rem",
        fontFamily: "var(--font-mono)",
        fontSize: "0.7rem",
        color: "rgba(14, 165, 233, 0.4)", // Muted cyber blue
        overflow: "hidden",
        pointerEvents: "none",
        zIndex: -1,
        maskImage: "linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)",
        WebkitMaskImage: "linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "flex-end"
      }}
    >
      <div ref={containerRef} style={{ overflow: "hidden", display: "flex", flexDirection: "column", gap: "4px" }}>
        {logs.map((log, index) => (
          <div key={index} style={{ whiteSpace: "nowrap", textOverflow: "ellipsis", overflow: "hidden" }}>
            {log}
          </div>
        ))}
      </div>
    </div>
  );
}
