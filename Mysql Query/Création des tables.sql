
CREATE TABLE Familles (
    id_f INT PRIMARY KEY,
    type_f ENUM('S', 'T') NOT NULL,
    description VARCHAR(255)
);


CREATE TABLE Sous_familles (
    id_sousf INT PRIMARY KEY,
    description VARCHAR(255),
    id_f INT,
    FOREIGN KEY (id_f) REFERENCES Familles(id_f)
);


CREATE TABLE Emploi (
    code_Tiahre VARCHAR(10) PRIMARY KEY,
    intitule VARCHAR(255),
    id_sousf INT,
    FOREIGN KEY (id_sousf) REFERENCES Sous_familles(id_sousf)
);


CREATE TABLE Fiches_poste (
    id_fichep INT PRIMARY KEY,
    intitule VARCHAR(255),
    structure_ref VARCHAR(100),
    code_Tiahre VARCHAR(10),
    code_UO VARCHAR(50),
    num_page_nemenclature INT,
    FOREIGN KEY (code_Tiahre) REFERENCES Emploi(code_Tiahre)
);
