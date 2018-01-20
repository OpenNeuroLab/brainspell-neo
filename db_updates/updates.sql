DROP TABLE IF EXISTS articles_updated CASCADE;
DROP TABLE IF EXISTS experiments_updated CASCADE ;
DROP TABLE IF EXISTS locations_updated CASCADE ;
DROP TABLE IF EXISTS tags_updated CASCADE;
DROP TABLE IF EXISTS votes CASCADE;

CREATE TABLE articles_updated(
  uniqueid bigserial PRIMARY KEY,
  "timestamp" TIMESTAMP,
   authors text,
   title text,
   abstract text,
   reference text,
   pmid VARCHAR(64),
   doi VARCHAR(128),
   neurosynthid VARCHAR(64),
   meshTags jsonb
);

CREATE TABLE experiments_updated(
  experiment_id bigserial PRIMARY KEY,
  title text,
  caption text,
  flagged BOOLEAN,
  articleId VARCHAR(64),
  numSubjects INTEGER,
  "space" VARCHAR(10),
  FOREIGN KEY (articleId) REFERENCES articles_updated(pmid)
);

CREATE TABLE locations_updated(
  x INTEGER,
  y INTEGER,
  z INTEGER,
  zScore INTEGER,
  experimentID INTEGER,
  location INTEGER,
  FOREIGN KEY (experimentID) REFERENCES experiments_updated(experiment_id),
  PRIMARY KEY(x,y,z,experimentID)
);

CREATE TABLE tags_updated(
  tag_name VARCHAR(100),
  agree INTEGER,
  disagree INTEGER,
  articleId VARCHAR(64),
  experimentId INTEGER,
  FOREIGN KEY (articleId) REFERENCES articles_updated(pmid),
  FOREIGN KEY (experimentId) REFERENCES experiments_updated(experiment_id),
  -- Note null experiment Reference if not defined
  UNIQUE(tag_name,articleId,experimentId)
);


CREATE TABLE votes(
  username VARCHAR(50),
  "name" VARCHAR(50),
  experimentID INTEGER,
  articleID INTEGER,
  vote BOOLEAN,
  "type" BOOLEAN,
  FOREIGN KEY (username) REFERENCES users(username),
  UNIQUE("username","name","experimentID")
);





                  -- Constraint Generation --
ALTER TABLE articles_updated ADD CONSTRAINT uniqueness UNIQUE (pmid);
ALTER TABLE users ADD CONSTRAINT uniqueness UNIQUE (username);

                  -- Index Generation --
CREATE INDEX pmid_lookup ON articles_updated USING HASH (pmid);
CREATE INDEX experiment_lookup ON experiments_updated (articleId);
CREATE INDEX coordinate_lookup ON locations_updated (experimentID);

-- Gin (Inverted) Indices for Full Text Search Optimization
CREATE INDEX abstract_text_search ON articles_updated USING gin(to_tsvector(abstract));




-- Our user Collection should be using the Postgres JSON type
ALTER TABLE "users" ALTER COLUMN collections TYPE JSON USING collections::JSON;