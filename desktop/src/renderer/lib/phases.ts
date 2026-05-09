export const PHASE_TO_SEGMENT: Record<string, number> = {
  "0": 0,
  "0.5": 1,
  "0.6": 2,
  "1": 3,
  "1.5": 4,
  "2.1": 5,
  "2.2": 5,
  "2.3": 5,
  "2.5": 6,
  "3": 7,
  "4": 8,
}

export const PHASE_LABELS: Record<string, string> = {
  "0": "Reading your idea",
  "0.5": "Identifying the underlying job-to-be-done",
  "0.6": "Exploring alternative framings",
  "1": "Three specialists weighing in (architect, designer, market)",
  "1.5": "Finding disagreements across the specialists",
  "2.1": "Generating alternative branches where opinions diverge",
  "2.2": "Stress-testing each branch",
  "2.3": "Picking the strongest survivor of each branch",
  "2.5": "Distilling the workspace",
  "3": "Cross-domain critique and kill-case",
  "4": "Writing your final brief",
}

export const TOTAL_SEGMENTS = 9
