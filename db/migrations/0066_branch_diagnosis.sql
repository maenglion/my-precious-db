-- 0066_branch_diagnosis.sql
-- DL-012: Branch Diagnosis & Growth Origin

ALTER TABLE review.ontology_candidate
  DROP CONSTRAINT ontology_candidate_candidate_type_check;

ALTER TABLE review.ontology_candidate
  ADD CONSTRAINT ontology_candidate_candidate_type_check
  CHECK (candidate_type IN (
      'ALIAS',
      'CLASS',
      'MAPPING',
      'SCOPE',
      'NONE'
  ));

ALTER TABLE review.ontology_candidate
  ADD COLUMN branch text NOT NULL DEFAULT 'ONTOLOGY'
    CHECK (branch IN ('ONTOLOGY', 'RULE', 'REPAIR'));

ALTER TABLE review.ontology_candidate
  ADD COLUMN growth_origin text NOT NULL DEFAULT 'BOTTOM_UP'
    CHECK (growth_origin IN ('TOP_DOWN', 'BOTTOM_UP'));

ALTER TABLE review.ontology_candidate
  ADD COLUMN decision_gain text;

CREATE INDEX ontology_candidate_branch_idx
ON review.ontology_candidate(branch);

CREATE INDEX ontology_candidate_growth_idx
ON review.ontology_candidate(growth_origin);