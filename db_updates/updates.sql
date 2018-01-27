DROP TABLE IF EXISTS articles CASCADE;
DROP TABLE IF EXISTS experiments CASCADE ;
DROP TABLE IF EXISTS locations CASCADE ;
DROP TABLE IF EXISTS tags CASCADE;
DROP TABLE IF EXISTS votes CASCADE;

CREATE TABLE articles(
  uniqueid bigserial PRIMARY KEY,
  "timestamp" TIMESTAMP,
   authors text,
   title text,
   abstract text,
   reference text,
   pmid VARCHAR(64),
   doi VARCHAR(128),
   neurosynthid VARCHAR(64)
);

CREATE TABLE experiments(
  experiment_id bigserial PRIMARY KEY,
  title text,
  caption text,
  flagged BOOLEAN,
  articleId VARCHAR(64),
  numSubjects INTEGER,
  "space" VARCHAR(10),
  FOREIGN KEY (articleId) REFERENCES articles(pmid)
);

CREATE TABLE locations(
  x INTEGER,
  y INTEGER,
  z INTEGER,
  zScore INTEGER,
  experimentID INTEGER,
  location INTEGER,
  FOREIGN KEY (experimentID) REFERENCES experiments(experiment_id),
  PRIMARY KEY(x,y,z,experimentID)
);

CREATE TABLE tags(
  tag_name VARCHAR(100),
  agree INTEGER,
  disagree INTEGER,
  articleId VARCHAR(64),
  experimentId INTEGER,
  FOREIGN KEY (articleId) REFERENCES articles(pmid),
  FOREIGN KEY (experimentId) REFERENCES experiments(experiment_id),
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
ALTER TABLE articles ADD CONSTRAINT uniqueness UNIQUE (pmid);
ALTER TABLE users ADD CONSTRAINT uniqueness UNIQUE (username);

                  -- Index Generation --
CREATE INDEX pmid_lookup ON articles USING HASH (pmid);
CREATE INDEX experiment_lookup ON experiments (articleId);
CREATE INDEX coordinate_lookup ON locations (experimentID);

-- Gin (Inverted) Indices for Full Text Search Optimization
CREATE INDEX abstract_text_search ON articles USING gin(to_tsvector(abstract));




-- Our user Collection should be using the Postgres JSON type
ALTER TABLE "users" ALTER COLUMN collections TYPE JSON USING collections::JSON;