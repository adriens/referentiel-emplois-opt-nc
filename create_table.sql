DROP TABLE IF EXISTS Familles;
DROP TABLE IF EXISTS Sous_familles;
DROP TABLE IF EXISTS Emploi;
DROP TABLE IF EXISTS Fiches_poste;

CREATE TABLE Familles (
  id_f integer PRIMARY KEY,
  type_f varchar NOT NULL CHECK (type_f IN ('S','T')),
  description varchar
);

CREATE TABLE Sous_familles (
  id_sousf integer PRIMARY KEY,
  description varchar,
  id_f integer REFERENCES Familles
);

CREATE TABLE Emploi (
  code_Tiahre integer PRIMARY KEY,
  intitule varchar,
  id_sousf integer REFERENCES Sous_familles
);

CREATE TABLE Fiches_poste (
  id_fichep integer PRIMARY KEY,
  intitule varchar,
  structure_ref varchar,
  code_Tiahre integer REFERENCES Emploi,
  code_UO varchar,
  num_page_nemenclature integer
);
