-- ============================================================
-- TRANSPARÊNCIA AI
-- PostgreSQL - Estrutura inicial
-- ============================================================

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;


-- ============================================================
-- FONTES DE DADOS
-- ============================================================

CREATE TABLE IF NOT EXISTS core.fonte (
    id              BIGSERIAL PRIMARY KEY,
    nome            VARCHAR(150) NOT NULL,
    codigo          VARCHAR(50) NOT NULL UNIQUE,
    tipo            VARCHAR(50) NOT NULL,
    url             TEXT,
    descricao       TEXT,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- ÓRGÃOS
-- ============================================================

CREATE TABLE IF NOT EXISTS core.orgao (
    id              BIGSERIAL PRIMARY KEY,
    fonte_id        BIGINT NOT NULL REFERENCES core.fonte(id),
    codigo          VARCHAR(30) NOT NULL,
    nome            VARCHAR(300) NOT NULL,

    UNIQUE (fonte_id, codigo)
);


-- ============================================================
-- UNIDADES ORÇAMENTÁRIAS
-- ============================================================

CREATE TABLE IF NOT EXISTS core.unidade_orcamentaria (
    id              BIGSERIAL PRIMARY KEY,
    fonte_id        BIGINT NOT NULL REFERENCES core.fonte(id),
    codigo          VARCHAR(30) NOT NULL,
    nome            VARCHAR(300) NOT NULL,

    UNIQUE (fonte_id, codigo)
);


-- ============================================================
-- UNIDADES GESTORAS
-- ============================================================

CREATE TABLE IF NOT EXISTS core.unidade_gestora (
    id              BIGSERIAL PRIMARY KEY,
    fonte_id        BIGINT NOT NULL REFERENCES core.fonte(id),
    codigo          VARCHAR(30),
    nome            VARCHAR(300),

    UNIQUE (fonte_id, codigo)
);


-- ============================================================
-- FAVORECIDOS
-- ============================================================

CREATE TABLE IF NOT EXISTS core.favorecido (
    id              BIGSERIAL PRIMARY KEY,
    fonte_id        BIGINT NOT NULL REFERENCES core.fonte(id),

    documento       VARCHAR(20) NOT NULL,
    nome            VARCHAR(500) NOT NULL,

    tipo_pessoa     VARCHAR(30),

    criado_em       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (fonte_id, documento)
);


-- ============================================================
-- FUNÇÃO
-- ============================================================

CREATE TABLE IF NOT EXISTS core.funcao (
    id              BIGSERIAL PRIMARY KEY,
    fonte_id        BIGINT NOT NULL REFERENCES core.fonte(id),
    codigo          VARCHAR(30) NOT NULL,
    nome            VARCHAR(300) NOT NULL,

    UNIQUE (fonte_id, codigo)
);


-- ============================================================
-- SUBFUNÇÃO
-- ============================================================

CREATE TABLE IF NOT EXISTS core.subfuncao (
    id              BIGSERIAL PRIMARY KEY,
    fonte_id        BIGINT NOT NULL REFERENCES core.fonte(id),
    codigo          VARCHAR(30) NOT NULL,
    nome            VARCHAR(300) NOT NULL,

    UNIQUE (fonte_id, codigo)
);


-- ============================================================
-- PROGRAMA
-- ============================================================

CREATE TABLE IF NOT EXISTS core.programa (
    id              BIGSERIAL PRIMARY KEY,
    fonte_id        BIGINT NOT NULL REFERENCES core.fonte(id),
    codigo          VARCHAR(30) NOT NULL,
    nome            VARCHAR(500) NOT NULL,

    UNIQUE (fonte_id, codigo)
);


-- ============================================================
-- AÇÃO
-- ============================================================

CREATE TABLE IF NOT EXISTS core.acao (
    id              BIGSERIAL PRIMARY KEY,
    fonte_id        BIGINT NOT NULL REFERENCES core.fonte(id),
    codigo          VARCHAR(30) NOT NULL,
    nome            VARCHAR(500) NOT NULL,

    UNIQUE (fonte_id, codigo)
);


-- ============================================================
-- TIPO DE LICITAÇÃO
-- ============================================================

CREATE TABLE IF NOT EXISTS core.tipo_licitacao (
    id              BIGSERIAL PRIMARY KEY,

    codigo           VARCHAR(30) NOT NULL,
    nome             VARCHAR(200) NOT NULL,
    descricao        TEXT,

    UNIQUE (codigo)
);


-- ============================================================
-- STAGING
-- ============================================================

CREATE TABLE IF NOT EXISTS staging.despesa_sp (
    id_staging BIGSERIAL PRIMARY KEY,

    cnpj_cpf_favorecido TEXT,
    nome_favorecido TEXT,

    ano_exercicio INTEGER,

    cod_orgao INTEGER,
    cod_uo INTEGER,

    cod_funcao INTEGER,
    cod_subfuncao INTEGER,

    cod_programa INTEGER,
    cod_acao BIGINT,

    cod_elemento INTEGER,
    cod_ug INTEGER,

    cod_categoria_despesa INTEGER,
    cod_grupo INTEGER,
    cod_modalidade_aplicacao INTEGER,
    cod_item INTEGER,
    cod_fonte INTEGER,
    cod_fonte_detalhada BIGINT,

    cod_tipo_licitacao INTEGER,

    vl_empenhado NUMERIC(20,2),
    vl_liquidado NUMERIC(20,2),
    vl_pago NUMERIC(20,2),
    vl_pago_rp NUMERIC(20,2),

    vl_dotacao_atual NUMERIC(20,2),

    vl_empenhado_inicial NUMERIC(20,2),
    vl_reforco NUMERIC(20,2),
    vl_anulacao NUMERIC(20,2),

    nome_orgao TEXT,
    nome_uo TEXT,
    nome_ug TEXT,

    nome_funcao TEXT,
    nome_subfuncao TEXT,
    nome_programa TEXT,
    nome_acao TEXT,

    nome_elemento TEXT,
    nome_categoria_despesa TEXT,
    nome_grupo TEXT,
    nome_modalidade_aplicacao TEXT,
    nome_item TEXT,
    nome_fonte TEXT,

    num_processo TEXT,

    nome_tipo_licitacao TEXT,

    indicador_restos TEXT,

    data_registro_empenho TIMESTAMP,

    num_empenho TEXT NOT NULL,

    fonte_id BIGINT NOT NULL REFERENCES core.fonte(id),

    carregado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- FATO DESPESA
-- ============================================================

CREATE TABLE IF NOT EXISTS core.fato_despesa (
    id BIGSERIAL PRIMARY KEY,

    fonte_id BIGINT NOT NULL REFERENCES core.fonte(id),

    ano_exercicio INTEGER NOT NULL,

    orgao_id BIGINT REFERENCES core.orgao(id),
    unidade_orcamentaria_id BIGINT REFERENCES core.unidade_orcamentaria(id),
    unidade_gestora_id BIGINT REFERENCES core.unidade_gestora(id),

    favorecido_id BIGINT REFERENCES core.favorecido(id),

    funcao_id BIGINT REFERENCES core.funcao(id),
    subfuncao_id BIGINT REFERENCES core.subfuncao(id),
    programa_id BIGINT REFERENCES core.programa(id),
    acao_id BIGINT REFERENCES core.acao(id),

    tipo_licitacao_id BIGINT REFERENCES core.tipo_licitacao(id),

    cod_elemento INTEGER,
    cod_categoria_despesa INTEGER,
    cod_grupo INTEGER,
    cod_modalidade_aplicacao INTEGER,
    cod_item INTEGER,
    cod_fonte INTEGER,
    cod_fonte_detalhada BIGINT,

    num_empenho VARCHAR(100) NOT NULL,
    num_processo VARCHAR(200),

    data_registro_empenho TIMESTAMP,

    indicador_restos VARCHAR(20),

    vl_empenhado_inicial NUMERIC(20,2),
    vl_empenhado NUMERIC(20,2),
    vl_reforco NUMERIC(20,2),
    vl_anulacao NUMERIC(20,2),

    vl_liquidado NUMERIC(20,2),
    vl_pago NUMERIC(20,2),
    vl_pago_rp NUMERIC(20,2),

    vl_dotacao_atual NUMERIC(20,2),

    liquidado_maior_que_empenhado BOOLEAN
        GENERATED ALWAYS AS (
            COALESCE(vl_liquidado, 0) >
            COALESCE(vl_empenhado, 0)
        ) STORED,

    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (fonte_id, num_empenho)
);


-- ============================================================
-- ÍNDICES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_fato_despesa_ano
    ON core.fato_despesa (ano_exercicio);

CREATE INDEX IF NOT EXISTS idx_fato_despesa_fonte
    ON core.fato_despesa (fonte_id);

CREATE INDEX IF NOT EXISTS idx_fato_despesa_orgao
    ON core.fato_despesa (orgao_id);

CREATE INDEX IF NOT EXISTS idx_fato_despesa_favorecido
    ON core.fato_despesa (favorecido_id);

CREATE INDEX IF NOT EXISTS idx_fato_despesa_funcao
    ON core.fato_despesa (funcao_id);

CREATE INDEX IF NOT EXISTS idx_fato_despesa_subfuncao
    ON core.fato_despesa (subfuncao_id);

CREATE INDEX IF NOT EXISTS idx_fato_despesa_programa
    ON core.fato_despesa (programa_id);

CREATE INDEX IF NOT EXISTS idx_fato_despesa_acao
    ON core.fato_despesa (acao_id);

CREATE INDEX IF NOT EXISTS idx_fato_despesa_data
    ON core.fato_despesa (data_registro_empenho);

CREATE INDEX IF NOT EXISTS idx_fato_despesa_documento
    ON core.favorecido (documento);


-- ============================================================
-- VIEW ANALÍTICA
-- ============================================================

CREATE OR REPLACE VIEW analytics.vw_despesas AS
SELECT
    f.id,

    fo.codigo AS fonte_codigo,
    fo.nome AS fonte_nome,

    f.ano_exercicio,

    o.codigo AS cod_orgao,
    o.nome AS nome_orgao,

    uo.codigo AS cod_uo,
    uo.nome AS nome_uo,

    fav.documento AS cpf_cnpj_favorecido,
    fav.nome AS nome_favorecido,

    fn.codigo AS cod_funcao,
    fn.nome AS nome_funcao,

    sf.codigo AS cod_subfuncao,
    sf.nome AS nome_subfuncao,

    p.codigo AS cod_programa,
    p.nome AS nome_programa,

    a.codigo AS cod_acao,
    a.nome AS nome_acao,

    f.cod_elemento,
    f.cod_categoria_despesa,
    f.cod_grupo,
    f.cod_modalidade_aplicacao,
    f.cod_item,
    f.cod_fonte,
    f.cod_fonte_detalhada,

    f.num_empenho,
    f.num_processo,

    f.data_registro_empenho,

    tl.codigo AS cod_tipo_licitacao,
    tl.nome AS nome_tipo_licitacao,

    f.indicador_restos,

    f.vl_empenhado_inicial,
    f.vl_empenhado,
    f.vl_reforco,
    f.vl_anulacao,
    f.vl_liquidado,
    f.vl_pago,
    f.vl_pago_rp,
    f.vl_dotacao_atual,

    f.liquidado_maior_que_empenhado

FROM core.fato_despesa f

JOIN core.fonte fo
    ON fo.id = f.fonte_id

LEFT JOIN core.orgao o
    ON o.id = f.orgao_id

LEFT JOIN core.unidade_orcamentaria uo
    ON uo.id = f.unidade_orcamentaria_id

LEFT JOIN core.favorecido fav
    ON fav.id = f.favorecido_id

LEFT JOIN core.funcao fn
    ON fn.id = f.funcao_id

LEFT JOIN core.subfuncao sf
    ON sf.id = f.subfuncao_id

LEFT JOIN core.programa p
    ON p.id = f.programa_id

LEFT JOIN core.acao a
    ON a.id = f.acao_id

LEFT JOIN core.tipo_licitacao tl
    ON tl.id = f.tipo_licitacao_id;