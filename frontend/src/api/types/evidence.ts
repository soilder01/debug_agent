import type { EvidenceArtifact, ImageArtifact, JudgeDelta } from "./debug";

export type ExperimentEvidence = {
  evidence_id: string;
  step_name: string;
  trial: number;
  model_name: string;
  model_provider: string;
  model_id: string;
  request_summary: {
    prompt_length?: number;
    has_image?: boolean;
    image_uri_scheme?: string;
    ablation_variant?: string;
    ablation_modalities?: string[];
  };
  latency_ms: number;
  response_parse_error: string;
  model_call_error_type: string;
  model_call_error_message: string;
  image_artifacts?: ImageArtifact[];
  artifacts?: EvidenceArtifact[];
  raw_output: string;
  judge: {
    score: number;
    reasons: string[];
    deltas?: JudgeDelta[];
  };
};
