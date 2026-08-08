// Shared learner-profile objects (single source of truth for the simulation + tests
// + start-state generator). The YAML in learner_profiles/*.md is the human-readable
// spec; these JS objects are the machine-consumed form.

export const PROFILE_01 = {
  profile_id: 'addition-beginner',
  display_name: 'Mia (beginner, ~7)',
  operations: ['+'],
  number_range: [0, 9],
  initial_state: {
    default: 'unknown',
    overrides: [
      { facts: 'num1 in 0..1', level: 'fluent' },
      { facts: 'num2 in 0..1', level: 'fluent' },
      { facts: 'doubles up to 5+5', level: 'emerging' },
      { facts: 'sum <= 6', level: 'emerging' },
    ],
  },
  response_model: {
    unknown:  { p_correct: 0.55, rt_ms: { dist: 'lognormal', median: 6500, sigma: 0.5 } },
    emerging: { p_correct: 0.85, rt_ms: { dist: 'lognormal', median: 3200, sigma: 0.4 } },
    fluent:   { p_correct: 0.98, rt_ms: { dist: 'lognormal', median: 1300, sigma: 0.3 } },
  },
  learning_model: { type: 'exposure-based', promote_after: 4, regress_after: 2, max_new_facts_per_session: 3 },
  schedule: { sessions: 50, problems_per_session: [8, 15] },
};

export const PROFILE_02 = {
  profile_id: 'mixed-with-holes',
  display_name: 'Noah (mixed, ~9)',
  operations: ['+', '-', '*'],
  number_range: [0, 9],
  initial_state: {
    default: 'fluent',
    overrides: [
      { facts: "operation == '*' and (num1 in 6..9 or num2 in 6..9)", level: 'unknown' },
      { facts: "operation == '*' and (num1 == 7 or num2 == 7)", level: 'unknown' },
      { facts: "operation == '-' and num1 in 8..9 and num2 in 4..7", level: 'emerging' },
    ],
  },
  response_model: {
    unknown:  { p_correct: 0.50, rt_ms: { dist: 'lognormal', median: 5500, sigma: 0.5 } },
    emerging: { p_correct: 0.85, rt_ms: { dist: 'lognormal', median: 3000, sigma: 0.4 } },
    fluent:   { p_correct: 0.98, rt_ms: { dist: 'lognormal', median: 1200, sigma: 0.3 } },
  },
  learning_model: { type: 'exposure-based', promote_after: 4, regress_after: 2, max_new_facts_per_session: 20 },
  schedule: { sessions: 30, problems_per_session: [25, 35] },
};

export const PROFILE_03 = {
  profile_id: 'proficient-adult',
  display_name: 'Sam (proficient adult)',
  operations: ['+', '-', '*'],
  number_range: [0, 9],
  initial_state: { default: 'fluent' },
  response_model: {
    fluent: { p_correct: 0.99, rt_ms: { dist: 'lognormal', median: 1100, sigma: 0.25 } },
  },
  learning_model: { type: 'static' },
  schedule: { sessions: 1, problems_per_session: 80 },
};

export const PROFILES = [PROFILE_01, PROFILE_02, PROFILE_03];
