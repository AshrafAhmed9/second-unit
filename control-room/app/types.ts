export type Stage = {
  stage: string;
  content: string;
  timestamp?: string;
};

export type DemoRecording = {
  job_id: string;
  shot_id: string;
  sequence: string;
  due_at: string;
  stages: Stage[];
  impact_headline: string;
  plan: string;
  actuator_result: string;
  scorecard: {
    detection_rate: number;
    false_positive_rate: number;
    baseline_detection_rate: number;
    vision_only_catches: number;
  };
};
