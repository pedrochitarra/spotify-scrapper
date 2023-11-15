-- Table: ART_Artista
CREATE TABLE ART_Artista (
    ART_codigo VARCHAR(30) NOT NULL UNIQUE,
    ART_primeironome VARCHAR(250) NOT NULL,
    ART_ultimonome VARCHAR(250) NOT NULL,
    ART_seguidores NUMERIC(10) NOT NULL,
    ART_popularidade NUMERIC(3) NOT NULL,
    ART_ouvintes NUMERIC(10) NOT NULL,
    CONSTRAINT art_artista_pk PRIMARY KEY (art_codigo, art_primeironome, art_ultimonome)
);

-- Table: SOC_RedeSocial
CREATE TABLE SOC_RedeSocial (
	soc_art_codigo varchar(30) NOT NULL,
	soc_url varchar(500) NOT NULL,
	soc_seguidores numeric(10) NOT NULL,
	soc_tipo varchar(12) NOT NULL,
	CONSTRAINT soc_redesocial_pk PRIMARY KEY (soc_art_codigo, soc_tipo),
	CONSTRAINT soc_redesocial_soc_art_codigo_fkey FOREIGN KEY (soc_art_codigo) REFERENCES art_artista(art_codigo)
);


-- Table: ALB_Album
CREATE TABLE ALB_Album (
    ALB_codigo VARCHAR(30) NOT NULL PRIMARY KEY,
    ALB_nome VARCHAR(250) NOT NULL,
    ALB_lancamento DATE NULL,
    ALB_tipo VARCHAR(20) CHECK (ALB_tipo IN ('album', 'single', 'compilation')) NOT NULL,
    ALB_qtdmusicas NUMERIC(3) NOT NULL,
    ALB_popularidade NUMERIC(3) NOT NULL
);

-- Table: FAI_Faixa
CREATE TABLE FAI_Faixa (
    FAI_codigo VARCHAR(30) NOT NULL PRIMARY KEY,
    FAI_nome VARCHAR(250) NOT NULL,
    FAI_explicita BOOLEAN NOT NULL,
    FAI_popularidade NUMERIC(3) NOT NULL,
    FAI_duracao NUMERIC(10) NOT NULL,
    FAI_reproducoes NUMERIC(10) NOT NULL
);

-- Table: PLY_Playlist
CREATE TABLE PLY_Playlist (
    PLY_codigo VARCHAR(30) NOT NULL PRIMARY KEY,
    PLY_nome VARCHAR(250) NOT NULL,
    PLY_descricao VARCHAR(250),
    PLY_seguidores NUMERIC(10) NOT NULL
);

-- Table: GEN_Genero
CREATE TABLE GEN_Genero (
	gen_codigo serial4 NOT NULL,
	gen_nome varchar(250) NOT NULL,
	CONSTRAINT gen_genero_pkey PRIMARY KEY (gen_codigo),
	CONSTRAINT gen_genero_uk UNIQUE (gen_nome)
);

-- Table: CID_Cidade
CREATE TABLE CID_Cidade (
	cid_codigo serial4 NOT NULL,
	cid_nome varchar(250) NOT NULL,
	cid_pais varchar NOT NULL,
	cid_regiao varchar NOT NULL,
	CONSTRAINT cid_cidade_pkey PRIMARY KEY (cid_codigo),
	CONSTRAINT cid_cidade_uk UNIQUE (cid_nome, cid_pais, cid_regiao)
);


-- Table: AAL_ArtistaAlbum
CREATE TABLE AAL_ArtistaAlbum (
    AAL_ART_codigo VARCHAR(30) NOT NULL,
    AAL_ALB_codigo VARCHAR(30) NOT NULL,
    PRIMARY KEY (AAL_ART_codigo, AAL_ALB_codigo),
    FOREIGN KEY (AAL_ART_codigo) REFERENCES ART_Artista(ART_codigo),
    FOREIGN KEY (AAL_ALB_codigo) REFERENCES ALB_Album(ALB_codigo)
);

-- Table: AGE_ArtistaGenero
CREATE TABLE AGE_ArtistaGenero (
    AGE_ART_codigo VARCHAR(30) NOT NULL,
    AGE_GEN_codigo INT NOT NULL,
    PRIMARY KEY (AGE_ART_codigo, AGE_GEN_codigo),
    FOREIGN KEY (AGE_ART_codigo) REFERENCES ART_Artista(ART_codigo),
    FOREIGN KEY (AGE_GEN_codigo) REFERENCES GEN_Genero(GEN_codigo)
);

-- Table: ARC_ArtistaCidade
CREATE TABLE ARC_ArtistaCidade (
    ARC_ART_codigo VARCHAR(30) NOT NULL,
    ARC_CID_codigo INT NOT NULL,
    ARC_ouvintes INT NOT NULL,
    PRIMARY KEY (ARC_ART_codigo, ARC_CID_codigo),
    FOREIGN KEY (ARC_ART_codigo) REFERENCES ART_Artista(ART_codigo),
    FOREIGN KEY (ARC_CID_codigo) REFERENCES CID_Cidade(CID_codigo)
);

-- Table: APY_ArtistaPlaylist
CREATE TABLE APY_ArtistaPlaylist (
    APY_ART_codigo VARCHAR(30) NOT NULL,
    APY_PLY_codigo VARCHAR(30) NOT NULL,
    APY_quantidade int4 NOT NULL,
    PRIMARY KEY (APY_ART_codigo, APY_PLY_codigo),
    FOREIGN KEY (APY_ART_codigo) REFERENCES ART_Artista(ART_codigo),
    FOREIGN KEY (APY_PLY_codigo) REFERENCES PLY_Playlist(PLY_codigo)
);

-- Table: FAL_FaixaAlbum
CREATE TABLE FAL_FaixaAlbum (
    FAL_FAI_codigo VARCHAR(30) NOT NULL,
    FAL_ALB_codigo VARCHAR(30) NOT NULL,
    PRIMARY KEY (FAL_FAI_codigo, FAL_ALB_codigo),
    FOREIGN KEY (FAL_FAI_codigo) REFERENCES FAI_Faixa(FAI_codigo),
    FOREIGN KEY (FAL_ALB_codigo) REFERENCES ALB_Album(ALB_codigo)
);

-- Table: AFX_ArtistaFaixa
CREATE TABLE AFX_ArtistaFaixa (
    AFX_ART_codigo VARCHAR(30) NOT NULL,
    AFX_FAI_codigo VARCHAR(30) NOT NULL,
    AFX_principal BOOLEAN NOT NULL,
    PRIMARY KEY (AFX_ART_codigo, AFX_FAI_codigo),
    FOREIGN KEY (AFX_ART_codigo) REFERENCES ART_Artista(ART_codigo),
    FOREIGN KEY (AFX_FAI_codigo) REFERENCES FAI_Faixa(FAI_codigo)
);

-- Table: AA_ArtistaArtista
CREATE TABLE AA_ArtistaArtista (
    AA_ART_A_codigo VARCHAR(30) NOT NULL,
    AA_ART_B_codigo VARCHAR(30) NOT NULL,
    PRIMARY KEY (AA_ART_A_codigo, AA_ART_B_codigo),
    FOREIGN KEY (AA_ART_A_codigo) REFERENCES ART_Artista(ART_codigo),
    FOREIGN KEY (AA_ART_B_codigo) REFERENCES ART_Artista(ART_codigo)
);

-- Table: FXP_FaixaPlaylist
CREATE TABLE FXP_FaixaPlaylist (
    FXP_FAI_codigo VARCHAR(30) NOT NULL,
    FXP_PLY_codigo VARCHAR(30) NOT NULL,
    PRIMARY KEY (FXP_FAI_codigo, FXP_PLY_codigo),
    FOREIGN KEY (FXP_FAI_codigo) REFERENCES FAI_Faixa(FAI_codigo),
    FOREIGN KEY (FXP_PLY_codigo) REFERENCES PLY_Playlist(PLY_codigo)
);

