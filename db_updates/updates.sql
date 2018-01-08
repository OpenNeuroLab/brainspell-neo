-- noinspection SqlNoDataSourceInspectionForFile
-- noinspection SqlDialectInspectionForFile

DROP TABLE IF EXISTS articles_updated CASCADE;
DROP TABLE IF EXISTS experiments_updated CASCADE ;
DROP TABLE IF EXISTS locations_updated CASCADE ;
DROP TABLE IF EXISTS tags_updated CASCADE;

CREATE TABLE articles_updated(
  uniqueid bigserial PRIMARY KEY,
  'timestamp' TIMESTAMP,
   authors text,
   title text,
   abstract text,
   reference text,
   pmid VARCHAR(64),
   doi VARCHAR(128),
   neurosynthid VARCHAR(64),
   metadata text
);

CREATE TABLE experiments_updated(
  experiment_id bigserial PRIMARY KEY,
  title text,
  caption text,
  markBadTable text,
  articleId VARCHAR(64),
  FOREIGN KEY (articleId) REFERENCES articles_updated(pmid)
);

CREATE TABLE locations_updated(
  x INTEGER,
  y INTEGER,
  z INTEGER,
  zScore INTEGER,
  experimentID INTEGER,
  FOREIGN KEY (experimentID) REFERENCES experiments_updated(experiment_id),
  PRIMARY KEY(x,y,z,experimentID)
);

CREATE TABLE tags_updated(
  'name' VARCHAR(20),
  ontology text,
  agree INTEGER,
  disagree INTEGER,
  experimentID INTEGER,
  FOREIGN KEY (experimentID) REFERENCES experiments_updated(experiment_id),
  PRIMARY KEY('name',experimentID)
);





                  -- Constraint Generation --
ALTER TABLE articles_updated ADD CONSTRAINT uniqueness UNIQUE (pmid);

                  -- Index Generation --
CREATE INDEX pmid_lookup ON articles_updated USING HASH (pmid);
CREATE INDEX experiment_lookup ON experiments_updated (articleId);
CREATE INDEX coordinate_lookup ON locations_updated (experimentID);