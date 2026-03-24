export type ExportFormat = "glb" | "obj" | "zip";
export type ArtifactKind = "input" | "mesh" | "archive" | "log" | "metadata";
export type ResolvedInferenceMode = "mock" | "local" | "real";

export type ArtifactDescriptor = {
  kind: ArtifactKind;
  file_name: string;
  relative_path: string;
  url: string;
};

export type GenerationResponse = {
  job_id: string;
  status: "mocked" | "completed";
  export_format: ExportFormat;
  output_directory: string;
  generated_at: string;
  input_image_path: string;
  asset_files: string[];
  artifacts: ArtifactDescriptor[];
  viewer_asset_url: string | null;
  download_urls: string[];
  processed_image_url: string | null;
  preprocessing_steps: string[];
  preprocessing_applied: string[];
  preprocessing_metadata: Record<string, number | string | null>;
  notes: string[];
  generation_time_seconds: number;
};

export type HealthResponse = {
  service: string;
  status: string;
  resolved_inference_mode: ResolvedInferenceMode;
  sf3d_repo_ready: boolean;
  viewer_preview_expected: boolean;
  torch_version: string | null;
  cuda_available: boolean;
  cuda_device_name: string | null;
  cuda_extension_ready: boolean;
  sf3d_force_cpu: boolean;
  expected_runner_device: "cpu" | "cuda";
  warnings: string[];
};
