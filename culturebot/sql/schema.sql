CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.oauth
(
    service         CHARACTER VARYING NOT NULL,
    key             CHARACTER VARYING NOT NULL,
    access_token    CHARACTER VARYING NOT NULL,
    refresh_token   CHARACTER VARYING,
    scope           CHARACTER VARYING,
    expires         TIMESTAMP WITH TIME ZONE,
    token_type      CHARACTER VARYING NOT NULL DEFAULT 'Bearer',
    user_id         CHARACTER VARYING NOT NULL,

    PRIMARY KEY (KEY),
    UNIQUE (service, user_id)
);

CREATE TABLE IF NOT EXISTS auth.genshin
(
    discord_id      BIGINT NOT NULL,

    uid             BIGINT,
    hoyolab_id      BIGINT,

    cookies         CHARACTER VARYING,
    authkey         CHARACTER VARYING,
    lang            CHARACTER VARYING,
    region          CHARACTER VARYING,

    UNIQUE (uid),
    PRIMARY KEY (discord_id)

);


CREATE SCHEMA IF NOT EXISTS swears;

CREATE TABLE IF NOT EXISTS swears.user
(
    user_id         BIGINT NOT NULL,
    guild_id        BIGINT NOT NULL,
    
    optout          BOOLEAN NOT NULL DEFAULT FALSE,
    
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS swears.swear
(
    user_id         BIGINT NOT NULL,
    guild_id        BIGINT NOT NULL,

    swear           CHARACTER VARYING NOT NULL,
    amount          INT NOT NULL DEFAULT 0,
    
    FOREIGN KEY (user_id, guild_id)
        REFERENCES swears.user(user_id, guild_id),

    UNIQUE (user_id, guild_id, swear)
);
