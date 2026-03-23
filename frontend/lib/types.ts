export type ExportFormat = "glb" | "obj" | "zip";

export type GenerationResponse = {
  job_id: string;
  status: "mocked" | "completed";
  export_format: ExportFormat;
  output_directory: string;
  generated_at: string;
  input_image_path: string;
  asset_files: string[];
  preprocessing_steps: string[];
  notes: string[];
  generation_time_seconds: number;
};
