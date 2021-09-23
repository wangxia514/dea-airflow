--
-- PostgreSQL database dump
--

-- Dumped from database version 12.8 (Ubuntu 12.8-1.pgdg18.04+1)
-- Dumped by pg_dump version 12.8 (Ubuntu 12.8-1.pgdg18.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: agdc; Type: SCHEMA; Schema: -; Owner: agdc_admin
--

CREATE SCHEMA agdc;


ALTER SCHEMA agdc OWNER TO agdc_admin;

--
-- Name: cubedash; Type: SCHEMA; Schema: -; Owner: opendatacubeusername
--

CREATE SCHEMA cubedash;


ALTER SCHEMA cubedash OWNER TO opendatacubeusername;

--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: float8range; Type: TYPE; Schema: agdc; Owner: agdc_admin
--

CREATE TYPE agdc.float8range AS RANGE (
    subtype = double precision,
    subtype_diff = float8mi
);


ALTER TYPE agdc.float8range OWNER TO agdc_admin;

--
-- Name: overviewperiod; Type: TYPE; Schema: public; Owner: opendatacubeusername
--

CREATE TYPE public.overviewperiod AS ENUM (
    'all',
    'year',
    'month',
    'day'
);


ALTER TYPE public.overviewperiod OWNER TO opendatacubeusername;

--
-- Name: timelineperiod; Type: TYPE; Schema: public; Owner: opendatacubeusername
--

CREATE TYPE public.timelineperiod AS ENUM (
    'year',
    'month',
    'week',
    'day'
);


ALTER TYPE public.timelineperiod OWNER TO opendatacubeusername;

--
-- Name: common_timestamp(text); Type: FUNCTION; Schema: agdc; Owner: agdc_admin
--

CREATE FUNCTION agdc.common_timestamp(text) RETURNS timestamp with time zone
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
select ($1)::timestamp at time zone 'utc';
$_$;


ALTER FUNCTION agdc.common_timestamp(text) OWNER TO agdc_admin;

--
-- Name: set_row_update_time(); Type: FUNCTION; Schema: agdc; Owner: opendatacubeusername
--

CREATE FUNCTION agdc.set_row_update_time() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
begin
  new.updated = now();
  return new;
end;
$$;


ALTER FUNCTION agdc.set_row_update_time() OWNER TO opendatacubeusername;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: dataset; Type: TABLE; Schema: agdc; Owner: agdc_admin
--

CREATE TABLE agdc.dataset (
    id uuid NOT NULL,
    metadata_type_ref smallint NOT NULL,
    dataset_type_ref smallint NOT NULL,
    metadata jsonb NOT NULL,
    archived timestamp with time zone,
    added timestamp with time zone DEFAULT now() NOT NULL,
    added_by name DEFAULT CURRENT_USER NOT NULL,
    updated timestamp with time zone
);


ALTER TABLE agdc.dataset OWNER TO agdc_admin;

--
-- Name: dataset_location; Type: TABLE; Schema: agdc; Owner: agdc_admin
--

CREATE TABLE agdc.dataset_location (
    id integer NOT NULL,
    dataset_ref uuid NOT NULL,
    uri_scheme character varying NOT NULL,
    uri_body character varying NOT NULL,
    added timestamp with time zone DEFAULT now() NOT NULL,
    added_by name DEFAULT CURRENT_USER NOT NULL,
    archived timestamp with time zone
);


ALTER TABLE agdc.dataset_location OWNER TO agdc_admin;

--
-- Name: dataset_location_id_seq; Type: SEQUENCE; Schema: agdc; Owner: agdc_admin
--

CREATE SEQUENCE agdc.dataset_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE agdc.dataset_location_id_seq OWNER TO agdc_admin;

--
-- Name: dataset_location_id_seq; Type: SEQUENCE OWNED BY; Schema: agdc; Owner: agdc_admin
--

ALTER SEQUENCE agdc.dataset_location_id_seq OWNED BY agdc.dataset_location.id;


--
-- Name: dataset_source; Type: TABLE; Schema: agdc; Owner: agdc_admin
--

CREATE TABLE agdc.dataset_source (
    dataset_ref uuid NOT NULL,
    classifier character varying NOT NULL,
    source_dataset_ref uuid NOT NULL
);


ALTER TABLE agdc.dataset_source OWNER TO agdc_admin;

--
-- Name: dataset_type; Type: TABLE; Schema: agdc; Owner: agdc_admin
--

CREATE TABLE agdc.dataset_type (
    id smallint NOT NULL,
    name character varying NOT NULL,
    metadata jsonb NOT NULL,
    metadata_type_ref smallint NOT NULL,
    definition jsonb NOT NULL,
    added timestamp with time zone DEFAULT now() NOT NULL,
    added_by name DEFAULT CURRENT_USER NOT NULL,
    updated timestamp with time zone,
    CONSTRAINT ck_dataset_type_alphanumeric_name CHECK (((name)::text ~* '^\w+$'::text))
);


ALTER TABLE agdc.dataset_type OWNER TO agdc_admin;

--
-- Name: dataset_type_id_seq; Type: SEQUENCE; Schema: agdc; Owner: agdc_admin
--

CREATE SEQUENCE agdc.dataset_type_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE agdc.dataset_type_id_seq OWNER TO agdc_admin;

--
-- Name: dataset_type_id_seq; Type: SEQUENCE OWNED BY; Schema: agdc; Owner: agdc_admin
--

ALTER SEQUENCE agdc.dataset_type_id_seq OWNED BY agdc.dataset_type.id;


--
-- Name: metadata_type; Type: TABLE; Schema: agdc; Owner: agdc_admin
--

CREATE TABLE agdc.metadata_type (
    id smallint NOT NULL,
    name character varying NOT NULL,
    definition jsonb NOT NULL,
    added timestamp with time zone DEFAULT now() NOT NULL,
    added_by name DEFAULT CURRENT_USER NOT NULL,
    updated timestamp with time zone,
    CONSTRAINT ck_metadata_type_alphanumeric_name CHECK (((name)::text ~* '^\w+$'::text))
);


ALTER TABLE agdc.metadata_type OWNER TO agdc_admin;

--
-- Name: dv_eo3_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_eo3_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{properties,odc:processing_datetime}'::text[])) AS creation_time,
    (dataset.metadata #>> '{properties,odc:file_format}'::text[]) AS format,
    (dataset.metadata #>> '{label}'::text[]) AS label,
    agdc.float8range(((dataset.metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text) AS lat,
    agdc.float8range(((dataset.metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text) AS lon,
    tstzrange(LEAST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), '[]'::text) AS "time",
    (dataset.metadata #>> '{properties,eo:platform}'::text[]) AS platform,
    (dataset.metadata #>> '{properties,eo:instrument}'::text[]) AS instrument,
    (dataset.metadata #>> '{properties,odc:region_code}'::text[]) AS region_code,
    (dataset.metadata #>> '{properties,odc:product_family}'::text[]) AS product_family,
    (dataset.metadata #>> '{properties,dea:dataset_maturity}'::text[]) AS dataset_maturity
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.metadata_type_ref = 1));


ALTER TABLE agdc.dv_eo3_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_eo3_landsat_ard_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_eo3_landsat_ard_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{properties,odc:processing_datetime}'::text[])) AS creation_time,
    (dataset.metadata #>> '{properties,odc:file_format}'::text[]) AS format,
    (dataset.metadata #>> '{label}'::text[]) AS label,
    (dataset.metadata #>> '{properties,eo:platform}'::text[]) AS platform,
    (dataset.metadata #>> '{properties,eo:instrument}'::text[]) AS instrument,
    (dataset.metadata #>> '{properties,odc:product_family}'::text[]) AS product_family,
    (dataset.metadata #>> '{properties,odc:region_code}'::text[]) AS region_code,
    (dataset.metadata #>> '{crs}'::text[]) AS crs_raw,
    (dataset.metadata #>> '{properties,dea:dataset_maturity}'::text[]) AS dataset_maturity,
    ((dataset.metadata #>> '{properties,gqa:cep90}'::text[]))::double precision AS gqa,
    ((dataset.metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision AS cloud_cover,
    tstzrange(LEAST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), '[]'::text) AS "time",
    agdc.float8range(((dataset.metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text) AS lon,
    agdc.float8range(((dataset.metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text) AS lat,
    ((dataset.metadata #>> '{properties,eo:gsd}'::text[]))::double precision AS eo_gsd,
    ((dataset.metadata #>> '{properties,eo:sun_azimuth}'::text[]))::double precision AS eo_sun_azimuth,
    ((dataset.metadata #>> '{properties,eo:sun_elevation}'::text[]))::double precision AS eo_sun_elevation,
    ((dataset.metadata #>> '{properties,fmask:clear}'::text[]))::double precision AS fmask_clear,
    ((dataset.metadata #>> '{properties,fmask:cloud_shadow}'::text[]))::double precision AS fmask_cloud_shadow,
    ((dataset.metadata #>> '{properties,fmask:snow}'::text[]))::double precision AS fmask_snow,
    ((dataset.metadata #>> '{properties,fmask:water}'::text[]))::double precision AS fmask_water,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_x}'::text[]))::double precision AS gqa_abs_iterative_mean_x,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_xy}'::text[]))::double precision AS gqa_abs_iterative_mean_xy,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_y}'::text[]))::double precision AS gqa_abs_iterative_mean_y,
    ((dataset.metadata #>> '{properties,gqa:abs_x}'::text[]))::double precision AS gqa_abs_x,
    ((dataset.metadata #>> '{properties,gqa:abs_xy}'::text[]))::double precision AS gqa_abs_xy,
    ((dataset.metadata #>> '{properties,gqa:abs_y}'::text[]))::double precision AS gqa_abs_y,
    ((dataset.metadata #>> '{properties,gqa:cep90}'::text[]))::double precision AS gqa_cep90,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_x}'::text[]))::double precision AS gqa_iterative_mean_x,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_xy}'::text[]))::double precision AS gqa_iterative_mean_xy,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_y}'::text[]))::double precision AS gqa_iterative_mean_y,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_x}'::text[]))::double precision AS gqa_iterative_stddev_x,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_xy}'::text[]))::double precision AS gqa_iterative_stddev_xy,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_y}'::text[]))::double precision AS gqa_iterative_stddev_y,
    ((dataset.metadata #>> '{properties,gqa:mean_x}'::text[]))::double precision AS gqa_mean_x,
    ((dataset.metadata #>> '{properties,gqa:mean_xy}'::text[]))::double precision AS gqa_mean_xy,
    ((dataset.metadata #>> '{properties,gqa:mean_y}'::text[]))::double precision AS gqa_mean_y,
    ((dataset.metadata #>> '{properties,gqa:stddev_x}'::text[]))::double precision AS gqa_stddev_x,
    ((dataset.metadata #>> '{properties,gqa:stddev_xy}'::text[]))::double precision AS gqa_stddev_xy,
    ((dataset.metadata #>> '{properties,gqa:stddev_y}'::text[]))::double precision AS gqa_stddev_y,
    (dataset.metadata #>> '{properties,landsat:landsat_scene_id}'::text[]) AS landsat_scene_id
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.metadata_type_ref = 5));


ALTER TABLE agdc.dv_eo3_landsat_ard_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_eo_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_eo_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{creation_dt}'::text[])) AS creation_time,
    (dataset.metadata #>> '{format,name}'::text[]) AS format,
    (dataset.metadata #>> '{ga_label}'::text[]) AS label,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text) AS lat,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text) AS lon,
    tstzrange(LEAST(agdc.common_timestamp((dataset.metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((dataset.metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[]))), '[]'::text) AS "time",
    (dataset.metadata #>> '{platform,code}'::text[]) AS platform,
    (dataset.metadata #>> '{instrument,name}'::text[]) AS instrument,
    (dataset.metadata #>> '{product_type}'::text[]) AS product_type
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.metadata_type_ref = 2));


ALTER TABLE agdc.dv_eo_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_eo_s2_nrt_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_eo_s2_nrt_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{system_information,time_processed}'::text[])) AS creation_time,
    (dataset.metadata #>> '{format,name}'::text[]) AS format,
    (dataset.metadata #>> '{tile_id}'::text[]) AS label,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text) AS lat,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text) AS lon,
    tstzrange(agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[])), '[]'::text) AS "time",
    (dataset.metadata #>> '{platform,code}'::text[]) AS platform,
    (dataset.metadata #>> '{instrument,name}'::text[]) AS instrument,
    (dataset.metadata #>> '{product_type}'::text[]) AS product_type
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.metadata_type_ref = 4));


ALTER TABLE agdc.dv_eo_s2_nrt_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_ga_ls7e_ard_provisional_3_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_ga_ls7e_ard_provisional_3_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{properties,odc:processing_datetime}'::text[])) AS creation_time,
    (dataset.metadata #>> '{properties,odc:file_format}'::text[]) AS format,
    (dataset.metadata #>> '{label}'::text[]) AS label,
    ((dataset.metadata #>> '{properties,gqa:cep90}'::text[]))::double precision AS gqa,
    agdc.float8range(((dataset.metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text) AS lat,
    agdc.float8range(((dataset.metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text) AS lon,
    tstzrange(LEAST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), '[]'::text) AS "time",
    ((dataset.metadata #>> '{properties,eo:gsd}'::text[]))::double precision AS eo_gsd,
    (dataset.metadata #>> '{crs}'::text[]) AS crs_raw,
    (dataset.metadata #>> '{properties,eo:platform}'::text[]) AS platform,
    ((dataset.metadata #>> '{properties,gqa:abs_x}'::text[]))::double precision AS gqa_abs_x,
    ((dataset.metadata #>> '{properties,gqa:abs_y}'::text[]))::double precision AS gqa_abs_y,
    ((dataset.metadata #>> '{properties,gqa:cep90}'::text[]))::double precision AS gqa_cep90,
    ((dataset.metadata #>> '{properties,fmask:snow}'::text[]))::double precision AS fmask_snow,
    ((dataset.metadata #>> '{properties,gqa:abs_xy}'::text[]))::double precision AS gqa_abs_xy,
    ((dataset.metadata #>> '{properties,gqa:mean_x}'::text[]))::double precision AS gqa_mean_x,
    ((dataset.metadata #>> '{properties,gqa:mean_y}'::text[]))::double precision AS gqa_mean_y,
    (dataset.metadata #>> '{properties,eo:instrument}'::text[]) AS instrument,
    ((dataset.metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision AS cloud_cover,
    ((dataset.metadata #>> '{properties,fmask:clear}'::text[]))::double precision AS fmask_clear,
    ((dataset.metadata #>> '{properties,fmask:water}'::text[]))::double precision AS fmask_water,
    ((dataset.metadata #>> '{properties,gqa:mean_xy}'::text[]))::double precision AS gqa_mean_xy,
    (dataset.metadata #>> '{properties,odc:region_code}'::text[]) AS region_code,
    ((dataset.metadata #>> '{properties,gqa:stddev_x}'::text[]))::double precision AS gqa_stddev_x,
    ((dataset.metadata #>> '{properties,gqa:stddev_y}'::text[]))::double precision AS gqa_stddev_y,
    ((dataset.metadata #>> '{properties,gqa:stddev_xy}'::text[]))::double precision AS gqa_stddev_xy,
    ((dataset.metadata #>> '{properties,eo:sun_azimuth}'::text[]))::double precision AS eo_sun_azimuth,
    (dataset.metadata #>> '{properties,odc:product_family}'::text[]) AS product_family,
    (dataset.metadata #>> '{properties,dea:dataset_maturity}'::text[]) AS dataset_maturity,
    ((dataset.metadata #>> '{properties,eo:sun_elevation}'::text[]))::double precision AS eo_sun_elevation,
    (dataset.metadata #>> '{properties,landsat:landsat_scene_id}'::text[]) AS landsat_scene_id,
    ((dataset.metadata #>> '{properties,fmask:cloud_shadow}'::text[]))::double precision AS fmask_cloud_shadow,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_x}'::text[]))::double precision AS gqa_iterative_mean_x,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_y}'::text[]))::double precision AS gqa_iterative_mean_y,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_xy}'::text[]))::double precision AS gqa_iterative_mean_xy,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_x}'::text[]))::double precision AS gqa_iterative_stddev_x,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_y}'::text[]))::double precision AS gqa_iterative_stddev_y,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_xy}'::text[]))::double precision AS gqa_iterative_stddev_xy,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_x}'::text[]))::double precision AS gqa_abs_iterative_mean_x,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_y}'::text[]))::double precision AS gqa_abs_iterative_mean_y,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_xy}'::text[]))::double precision AS gqa_abs_iterative_mean_xy
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 3));


ALTER TABLE agdc.dv_ga_ls7e_ard_provisional_3_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_ga_ls8c_ard_provisional_3_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_ga_ls8c_ard_provisional_3_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{properties,odc:processing_datetime}'::text[])) AS creation_time,
    (dataset.metadata #>> '{properties,odc:file_format}'::text[]) AS format,
    (dataset.metadata #>> '{label}'::text[]) AS label,
    ((dataset.metadata #>> '{properties,gqa:cep90}'::text[]))::double precision AS gqa,
    agdc.float8range(((dataset.metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text) AS lat,
    agdc.float8range(((dataset.metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text) AS lon,
    tstzrange(LEAST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), '[]'::text) AS "time",
    ((dataset.metadata #>> '{properties,eo:gsd}'::text[]))::double precision AS eo_gsd,
    (dataset.metadata #>> '{crs}'::text[]) AS crs_raw,
    (dataset.metadata #>> '{properties,eo:platform}'::text[]) AS platform,
    ((dataset.metadata #>> '{properties,gqa:abs_x}'::text[]))::double precision AS gqa_abs_x,
    ((dataset.metadata #>> '{properties,gqa:abs_y}'::text[]))::double precision AS gqa_abs_y,
    ((dataset.metadata #>> '{properties,gqa:cep90}'::text[]))::double precision AS gqa_cep90,
    ((dataset.metadata #>> '{properties,fmask:snow}'::text[]))::double precision AS fmask_snow,
    ((dataset.metadata #>> '{properties,gqa:abs_xy}'::text[]))::double precision AS gqa_abs_xy,
    ((dataset.metadata #>> '{properties,gqa:mean_x}'::text[]))::double precision AS gqa_mean_x,
    ((dataset.metadata #>> '{properties,gqa:mean_y}'::text[]))::double precision AS gqa_mean_y,
    (dataset.metadata #>> '{properties,eo:instrument}'::text[]) AS instrument,
    ((dataset.metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision AS cloud_cover,
    ((dataset.metadata #>> '{properties,fmask:clear}'::text[]))::double precision AS fmask_clear,
    ((dataset.metadata #>> '{properties,fmask:water}'::text[]))::double precision AS fmask_water,
    ((dataset.metadata #>> '{properties,gqa:mean_xy}'::text[]))::double precision AS gqa_mean_xy,
    (dataset.metadata #>> '{properties,odc:region_code}'::text[]) AS region_code,
    ((dataset.metadata #>> '{properties,gqa:stddev_x}'::text[]))::double precision AS gqa_stddev_x,
    ((dataset.metadata #>> '{properties,gqa:stddev_y}'::text[]))::double precision AS gqa_stddev_y,
    ((dataset.metadata #>> '{properties,gqa:stddev_xy}'::text[]))::double precision AS gqa_stddev_xy,
    ((dataset.metadata #>> '{properties,eo:sun_azimuth}'::text[]))::double precision AS eo_sun_azimuth,
    (dataset.metadata #>> '{properties,odc:product_family}'::text[]) AS product_family,
    (dataset.metadata #>> '{properties,dea:dataset_maturity}'::text[]) AS dataset_maturity,
    ((dataset.metadata #>> '{properties,eo:sun_elevation}'::text[]))::double precision AS eo_sun_elevation,
    (dataset.metadata #>> '{properties,landsat:landsat_scene_id}'::text[]) AS landsat_scene_id,
    ((dataset.metadata #>> '{properties,fmask:cloud_shadow}'::text[]))::double precision AS fmask_cloud_shadow,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_x}'::text[]))::double precision AS gqa_iterative_mean_x,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_y}'::text[]))::double precision AS gqa_iterative_mean_y,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_xy}'::text[]))::double precision AS gqa_iterative_mean_xy,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_x}'::text[]))::double precision AS gqa_iterative_stddev_x,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_y}'::text[]))::double precision AS gqa_iterative_stddev_y,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_xy}'::text[]))::double precision AS gqa_iterative_stddev_xy,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_x}'::text[]))::double precision AS gqa_abs_iterative_mean_x,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_y}'::text[]))::double precision AS gqa_abs_iterative_mean_y,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_xy}'::text[]))::double precision AS gqa_abs_iterative_mean_xy
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 4));


ALTER TABLE agdc.dv_ga_ls8c_ard_provisional_3_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_ga_s2am_ard_provisional_3_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_ga_s2am_ard_provisional_3_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{properties,odc:processing_datetime}'::text[])) AS creation_time,
    (dataset.metadata #>> '{properties,odc:file_format}'::text[]) AS format,
    (dataset.metadata #>> '{label}'::text[]) AS label,
    ((dataset.metadata #>> '{properties,gqa:cep90}'::text[]))::double precision AS gqa,
    agdc.float8range(((dataset.metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text) AS lat,
    agdc.float8range(((dataset.metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text) AS lon,
    tstzrange(LEAST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), '[]'::text) AS "time",
    ((dataset.metadata #>> '{properties,eo:gsd}'::text[]))::double precision AS eo_gsd,
    (dataset.metadata #>> '{crs}'::text[]) AS crs_raw,
    (dataset.metadata #>> '{properties,eo:platform}'::text[]) AS platform,
    ((dataset.metadata #>> '{properties,gqa:abs_x}'::text[]))::double precision AS gqa_abs_x,
    ((dataset.metadata #>> '{properties,gqa:abs_y}'::text[]))::double precision AS gqa_abs_y,
    ((dataset.metadata #>> '{properties,gqa:cep90}'::text[]))::double precision AS gqa_cep90,
    ((dataset.metadata #>> '{properties,fmask:snow}'::text[]))::double precision AS fmask_snow,
    ((dataset.metadata #>> '{properties,gqa:abs_xy}'::text[]))::double precision AS gqa_abs_xy,
    ((dataset.metadata #>> '{properties,gqa:mean_x}'::text[]))::double precision AS gqa_mean_x,
    ((dataset.metadata #>> '{properties,gqa:mean_y}'::text[]))::double precision AS gqa_mean_y,
    (dataset.metadata #>> '{properties,eo:instrument}'::text[]) AS instrument,
    ((dataset.metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision AS cloud_cover,
    ((dataset.metadata #>> '{properties,fmask:clear}'::text[]))::double precision AS fmask_clear,
    ((dataset.metadata #>> '{properties,fmask:water}'::text[]))::double precision AS fmask_water,
    ((dataset.metadata #>> '{properties,gqa:mean_xy}'::text[]))::double precision AS gqa_mean_xy,
    (dataset.metadata #>> '{properties,odc:region_code}'::text[]) AS region_code,
    ((dataset.metadata #>> '{properties,gqa:stddev_x}'::text[]))::double precision AS gqa_stddev_x,
    ((dataset.metadata #>> '{properties,gqa:stddev_y}'::text[]))::double precision AS gqa_stddev_y,
    ((dataset.metadata #>> '{properties,gqa:stddev_xy}'::text[]))::double precision AS gqa_stddev_xy,
    ((dataset.metadata #>> '{properties,eo:sun_azimuth}'::text[]))::double precision AS eo_sun_azimuth,
    (dataset.metadata #>> '{properties,odc:product_family}'::text[]) AS product_family,
    (dataset.metadata #>> '{properties,dea:dataset_maturity}'::text[]) AS dataset_maturity,
    ((dataset.metadata #>> '{properties,eo:sun_elevation}'::text[]))::double precision AS eo_sun_elevation,
    (dataset.metadata #>> '{properties,landsat:landsat_scene_id}'::text[]) AS landsat_scene_id,
    ((dataset.metadata #>> '{properties,fmask:cloud_shadow}'::text[]))::double precision AS fmask_cloud_shadow,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_x}'::text[]))::double precision AS gqa_iterative_mean_x,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_y}'::text[]))::double precision AS gqa_iterative_mean_y,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_xy}'::text[]))::double precision AS gqa_iterative_mean_xy,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_x}'::text[]))::double precision AS gqa_iterative_stddev_x,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_y}'::text[]))::double precision AS gqa_iterative_stddev_y,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_xy}'::text[]))::double precision AS gqa_iterative_stddev_xy,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_x}'::text[]))::double precision AS gqa_abs_iterative_mean_x,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_y}'::text[]))::double precision AS gqa_abs_iterative_mean_y,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_xy}'::text[]))::double precision AS gqa_abs_iterative_mean_xy
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 5));


ALTER TABLE agdc.dv_ga_s2am_ard_provisional_3_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_ga_s2bm_ard_provisional_3_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_ga_s2bm_ard_provisional_3_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{properties,odc:processing_datetime}'::text[])) AS creation_time,
    (dataset.metadata #>> '{properties,odc:file_format}'::text[]) AS format,
    (dataset.metadata #>> '{label}'::text[]) AS label,
    ((dataset.metadata #>> '{properties,gqa:cep90}'::text[]))::double precision AS gqa,
    agdc.float8range(((dataset.metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text) AS lat,
    agdc.float8range(((dataset.metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((dataset.metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text) AS lon,
    tstzrange(LEAST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((dataset.metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{properties,datetime}'::text[]))), '[]'::text) AS "time",
    ((dataset.metadata #>> '{properties,eo:gsd}'::text[]))::double precision AS eo_gsd,
    (dataset.metadata #>> '{crs}'::text[]) AS crs_raw,
    (dataset.metadata #>> '{properties,eo:platform}'::text[]) AS platform,
    ((dataset.metadata #>> '{properties,gqa:abs_x}'::text[]))::double precision AS gqa_abs_x,
    ((dataset.metadata #>> '{properties,gqa:abs_y}'::text[]))::double precision AS gqa_abs_y,
    ((dataset.metadata #>> '{properties,gqa:cep90}'::text[]))::double precision AS gqa_cep90,
    ((dataset.metadata #>> '{properties,fmask:snow}'::text[]))::double precision AS fmask_snow,
    ((dataset.metadata #>> '{properties,gqa:abs_xy}'::text[]))::double precision AS gqa_abs_xy,
    ((dataset.metadata #>> '{properties,gqa:mean_x}'::text[]))::double precision AS gqa_mean_x,
    ((dataset.metadata #>> '{properties,gqa:mean_y}'::text[]))::double precision AS gqa_mean_y,
    (dataset.metadata #>> '{properties,eo:instrument}'::text[]) AS instrument,
    ((dataset.metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision AS cloud_cover,
    ((dataset.metadata #>> '{properties,fmask:clear}'::text[]))::double precision AS fmask_clear,
    ((dataset.metadata #>> '{properties,fmask:water}'::text[]))::double precision AS fmask_water,
    ((dataset.metadata #>> '{properties,gqa:mean_xy}'::text[]))::double precision AS gqa_mean_xy,
    (dataset.metadata #>> '{properties,odc:region_code}'::text[]) AS region_code,
    ((dataset.metadata #>> '{properties,gqa:stddev_x}'::text[]))::double precision AS gqa_stddev_x,
    ((dataset.metadata #>> '{properties,gqa:stddev_y}'::text[]))::double precision AS gqa_stddev_y,
    ((dataset.metadata #>> '{properties,gqa:stddev_xy}'::text[]))::double precision AS gqa_stddev_xy,
    ((dataset.metadata #>> '{properties,eo:sun_azimuth}'::text[]))::double precision AS eo_sun_azimuth,
    (dataset.metadata #>> '{properties,odc:product_family}'::text[]) AS product_family,
    (dataset.metadata #>> '{properties,dea:dataset_maturity}'::text[]) AS dataset_maturity,
    ((dataset.metadata #>> '{properties,eo:sun_elevation}'::text[]))::double precision AS eo_sun_elevation,
    (dataset.metadata #>> '{properties,landsat:landsat_scene_id}'::text[]) AS landsat_scene_id,
    ((dataset.metadata #>> '{properties,fmask:cloud_shadow}'::text[]))::double precision AS fmask_cloud_shadow,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_x}'::text[]))::double precision AS gqa_iterative_mean_x,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_y}'::text[]))::double precision AS gqa_iterative_mean_y,
    ((dataset.metadata #>> '{properties,gqa:iterative_mean_xy}'::text[]))::double precision AS gqa_iterative_mean_xy,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_x}'::text[]))::double precision AS gqa_iterative_stddev_x,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_y}'::text[]))::double precision AS gqa_iterative_stddev_y,
    ((dataset.metadata #>> '{properties,gqa:iterative_stddev_xy}'::text[]))::double precision AS gqa_iterative_stddev_xy,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_x}'::text[]))::double precision AS gqa_abs_iterative_mean_x,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_y}'::text[]))::double precision AS gqa_abs_iterative_mean_y,
    ((dataset.metadata #>> '{properties,gqa:abs_iterative_mean_xy}'::text[]))::double precision AS gqa_abs_iterative_mean_xy
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 6));


ALTER TABLE agdc.dv_ga_s2bm_ard_provisional_3_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_ls5_fc_albers_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_ls5_fc_albers_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{creation_dt}'::text[])) AS creation_time,
    (dataset.metadata #>> '{format,name}'::text[]) AS format,
    (dataset.metadata #>> '{ga_label}'::text[]) AS label,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text) AS lat,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text) AS lon,
    tstzrange(LEAST(agdc.common_timestamp((dataset.metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((dataset.metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[]))), '[]'::text) AS "time",
    (dataset.metadata #>> '{platform,code}'::text[]) AS platform,
    (dataset.metadata #>> '{instrument,name}'::text[]) AS instrument,
    (dataset.metadata #>> '{product_type}'::text[]) AS product_type
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 8));


ALTER TABLE agdc.dv_ls5_fc_albers_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_ls7_fc_albers_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_ls7_fc_albers_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{creation_dt}'::text[])) AS creation_time,
    (dataset.metadata #>> '{format,name}'::text[]) AS format,
    (dataset.metadata #>> '{ga_label}'::text[]) AS label,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text) AS lat,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text) AS lon,
    tstzrange(LEAST(agdc.common_timestamp((dataset.metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((dataset.metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[]))), '[]'::text) AS "time",
    (dataset.metadata #>> '{platform,code}'::text[]) AS platform,
    (dataset.metadata #>> '{instrument,name}'::text[]) AS instrument,
    (dataset.metadata #>> '{product_type}'::text[]) AS product_type
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 10));


ALTER TABLE agdc.dv_ls7_fc_albers_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_ls8_fc_albers_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_ls8_fc_albers_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{creation_dt}'::text[])) AS creation_time,
    (dataset.metadata #>> '{format,name}'::text[]) AS format,
    (dataset.metadata #>> '{ga_label}'::text[]) AS label,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text) AS lat,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text) AS lon,
    tstzrange(LEAST(agdc.common_timestamp((dataset.metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((dataset.metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[]))), '[]'::text) AS "time",
    (dataset.metadata #>> '{platform,code}'::text[]) AS platform,
    (dataset.metadata #>> '{instrument,name}'::text[]) AS instrument,
    (dataset.metadata #>> '{product_type}'::text[]) AS product_type
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 9));


ALTER TABLE agdc.dv_ls8_fc_albers_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_s2a_nrt_granule_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_s2a_nrt_granule_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{system_information,time_processed}'::text[])) AS creation_time,
    (dataset.metadata #>> '{format,name}'::text[]) AS format,
    (dataset.metadata #>> '{tile_id}'::text[]) AS label,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text) AS lat,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text) AS lon,
    tstzrange(agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[])), '[]'::text) AS "time",
    (dataset.metadata #>> '{platform,code}'::text[]) AS platform,
    (dataset.metadata #>> '{instrument,name}'::text[]) AS instrument,
    (dataset.metadata #>> '{product_type}'::text[]) AS product_type
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 1));


ALTER TABLE agdc.dv_s2a_nrt_granule_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_s2b_nrt_granule_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_s2b_nrt_granule_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{system_information,time_processed}'::text[])) AS creation_time,
    (dataset.metadata #>> '{format,name}'::text[]) AS format,
    (dataset.metadata #>> '{tile_id}'::text[]) AS label,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text) AS lat,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text) AS lon,
    tstzrange(agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[])), '[]'::text) AS "time",
    (dataset.metadata #>> '{platform,code}'::text[]) AS platform,
    (dataset.metadata #>> '{instrument,name}'::text[]) AS instrument,
    (dataset.metadata #>> '{product_type}'::text[]) AS product_type
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 2));


ALTER TABLE agdc.dv_s2b_nrt_granule_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_telemetry_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_telemetry_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{creation_dt}'::text[])) AS creation_time,
    (dataset.metadata #>> '{format,name}'::text[]) AS format,
    (dataset.metadata #>> '{ga_label}'::text[]) AS label,
    (dataset.metadata #>> '{acquisition,groundstation,code}'::text[]) AS gsi,
    tstzrange(agdc.common_timestamp((dataset.metadata #>> '{acquisition,aos}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{acquisition,los}'::text[])), '[]'::text) AS "time",
    ((dataset.metadata #>> '{acquisition,platform_orbit}'::text[]))::integer AS orbit,
    numrange((((dataset.metadata #>> '{image,satellite_ref_point_start,y}'::text[]))::integer)::numeric, (GREATEST(((dataset.metadata #>> '{image,satellite_ref_point_end,y}'::text[]))::integer, ((dataset.metadata #>> '{image,satellite_ref_point_start,y}'::text[]))::integer))::numeric, '[]'::text) AS sat_row,
    (dataset.metadata #>> '{platform,code}'::text[]) AS platform,
    numrange((((dataset.metadata #>> '{image,satellite_ref_point_start,x}'::text[]))::integer)::numeric, (GREATEST(((dataset.metadata #>> '{image,satellite_ref_point_end,x}'::text[]))::integer, ((dataset.metadata #>> '{image,satellite_ref_point_start,x}'::text[]))::integer))::numeric, '[]'::text) AS sat_path,
    (dataset.metadata #>> '{instrument,name}'::text[]) AS instrument,
    (dataset.metadata #>> '{product_type}'::text[]) AS product_type
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.metadata_type_ref = 3));


ALTER TABLE agdc.dv_telemetry_dataset OWNER TO opendatacubeusername;

--
-- Name: dv_wofs_albers_dataset; Type: VIEW; Schema: agdc; Owner: opendatacubeusername
--

CREATE VIEW agdc.dv_wofs_albers_dataset AS
 SELECT dataset.id,
    dataset.added AS indexed_time,
    dataset.added_by AS indexed_by,
    dataset_type.name AS product,
    dataset.dataset_type_ref AS dataset_type_id,
    metadata_type.name AS metadata_type,
    dataset.metadata_type_ref AS metadata_type_id,
    dataset.metadata AS metadata_doc,
    agdc.common_timestamp((dataset.metadata #>> '{creation_dt}'::text[])) AS creation_time,
    (dataset.metadata #>> '{format,name}'::text[]) AS format,
    (dataset.metadata #>> '{ga_label}'::text[]) AS label,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text) AS lat,
    agdc.float8range(LEAST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((dataset.metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((dataset.metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text) AS lon,
    tstzrange(LEAST(agdc.common_timestamp((dataset.metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((dataset.metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((dataset.metadata #>> '{extent,center_dt}'::text[]))), '[]'::text) AS "time",
    (dataset.metadata #>> '{platform,code}'::text[]) AS platform,
    (dataset.metadata #>> '{instrument,name}'::text[]) AS instrument,
    (dataset.metadata #>> '{product_type}'::text[]) AS product_type
   FROM ((agdc.dataset
     JOIN agdc.dataset_type ON ((dataset_type.id = dataset.dataset_type_ref)))
     JOIN agdc.metadata_type ON ((metadata_type.id = dataset_type.metadata_type_ref)))
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 7));


ALTER TABLE agdc.dv_wofs_albers_dataset OWNER TO opendatacubeusername;

--
-- Name: metadata_type_id_seq; Type: SEQUENCE; Schema: agdc; Owner: agdc_admin
--

CREATE SEQUENCE agdc.metadata_type_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE agdc.metadata_type_id_seq OWNER TO agdc_admin;

--
-- Name: metadata_type_id_seq; Type: SEQUENCE OWNED BY; Schema: agdc; Owner: agdc_admin
--

ALTER SEQUENCE agdc.metadata_type_id_seq OWNED BY agdc.metadata_type.id;


--
-- Name: dataset_spatial; Type: TABLE; Schema: cubedash; Owner: opendatacubeusername
--

CREATE TABLE cubedash.dataset_spatial (
    id uuid NOT NULL,
    dataset_type_ref smallint NOT NULL,
    center_time timestamp with time zone NOT NULL,
    creation_time timestamp with time zone NOT NULL,
    region_code character varying,
    size_bytes bigint,
    footprint public.geometry
);


ALTER TABLE cubedash.dataset_spatial OWNER TO opendatacubeusername;

--
-- Name: COLUMN dataset_spatial.id; Type: COMMENT; Schema: cubedash; Owner: opendatacubeusername
--

COMMENT ON COLUMN cubedash.dataset_spatial.id IS 'Dataset ID';


--
-- Name: COLUMN dataset_spatial.dataset_type_ref; Type: COMMENT; Schema: cubedash; Owner: opendatacubeusername
--

COMMENT ON COLUMN cubedash.dataset_spatial.dataset_type_ref IS 'The ODC dataset_type id';


--
-- Name: mv_dataset_spatial_quality; Type: MATERIALIZED VIEW; Schema: cubedash; Owner: opendatacubeusername
--

CREATE MATERIALIZED VIEW cubedash.mv_dataset_spatial_quality AS
 SELECT dataset_spatial.dataset_type_ref,
    count(*) AS count,
    count(*) FILTER (WHERE (dataset_spatial.footprint IS NULL)) AS missing_footprint,
    sum(pg_column_size(dataset_spatial.footprint)) FILTER (WHERE (dataset_spatial.footprint IS NOT NULL)) AS footprint_size,
    stddev(pg_column_size(dataset_spatial.footprint)) FILTER (WHERE (dataset_spatial.footprint IS NOT NULL)) AS footprint_stddev,
    count(*) FILTER (WHERE (public.st_srid(dataset_spatial.footprint) IS NULL)) AS missing_srid,
    count(*) FILTER (WHERE (dataset_spatial.size_bytes IS NOT NULL)) AS has_file_size,
    count(*) FILTER (WHERE (dataset_spatial.region_code IS NOT NULL)) AS has_region
   FROM cubedash.dataset_spatial
  GROUP BY dataset_spatial.dataset_type_ref
  WITH NO DATA;


ALTER TABLE cubedash.mv_dataset_spatial_quality OWNER TO opendatacubeusername;

--
-- Name: mv_spatial_ref_sys; Type: MATERIALIZED VIEW; Schema: cubedash; Owner: opendatacubeusername
--

CREATE MATERIALIZED VIEW cubedash.mv_spatial_ref_sys AS
 SELECT spatial_ref_sys.srid,
    spatial_ref_sys.auth_name,
    spatial_ref_sys.auth_srid,
    spatial_ref_sys.srtext,
    spatial_ref_sys.proj4text
   FROM public.spatial_ref_sys
  WITH NO DATA;


ALTER TABLE cubedash.mv_spatial_ref_sys OWNER TO opendatacubeusername;

--
-- Name: product; Type: TABLE; Schema: cubedash; Owner: opendatacubeusername
--

CREATE TABLE cubedash.product (
    id smallint NOT NULL,
    name character varying NOT NULL,
    dataset_count integer NOT NULL,
    last_refresh timestamp with time zone NOT NULL,
    last_successful_summary timestamp with time zone,
    source_product_refs smallint[],
    derived_product_refs smallint[],
    time_earliest timestamp with time zone,
    time_latest timestamp with time zone,
    fixed_metadata jsonb
);


ALTER TABLE cubedash.product OWNER TO opendatacubeusername;

--
-- Name: COLUMN product.last_refresh; Type: COMMENT; Schema: cubedash; Owner: opendatacubeusername
--

COMMENT ON COLUMN cubedash.product.last_refresh IS 'Last refresh of this product''s extents''';


--
-- Name: COLUMN product.last_successful_summary; Type: COMMENT; Schema: cubedash; Owner: opendatacubeusername
--

COMMENT ON COLUMN cubedash.product.last_successful_summary IS 'The `last_refresh` time that was current when summaries were last *fully* generated successfully.';


--
-- Name: product_id_seq; Type: SEQUENCE; Schema: cubedash; Owner: opendatacubeusername
--

CREATE SEQUENCE cubedash.product_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE cubedash.product_id_seq OWNER TO opendatacubeusername;

--
-- Name: product_id_seq; Type: SEQUENCE OWNED BY; Schema: cubedash; Owner: opendatacubeusername
--

ALTER SEQUENCE cubedash.product_id_seq OWNED BY cubedash.product.id;


--
-- Name: region; Type: TABLE; Schema: cubedash; Owner: opendatacubeusername
--

CREATE TABLE cubedash.region (
    dataset_type_ref smallint NOT NULL,
    region_code character varying NOT NULL,
    count integer NOT NULL,
    generation_time timestamp with time zone DEFAULT now() NOT NULL,
    footprint public.geometry(Geometry,4326)
);


ALTER TABLE cubedash.region OWNER TO opendatacubeusername;

--
-- Name: time_overview; Type: TABLE; Schema: cubedash; Owner: opendatacubeusername
--

CREATE TABLE cubedash.time_overview (
    product_ref smallint NOT NULL,
    period_type public.overviewperiod NOT NULL,
    start_day date NOT NULL,
    dataset_count integer NOT NULL,
    time_earliest timestamp with time zone,
    time_latest timestamp with time zone,
    timeline_period public.timelineperiod NOT NULL,
    timeline_dataset_start_days timestamp with time zone[] NOT NULL,
    timeline_dataset_counts integer[] NOT NULL,
    regions character varying[] NOT NULL,
    region_dataset_counts integer[] NOT NULL,
    newest_dataset_creation_time timestamp with time zone,
    generation_time timestamp with time zone DEFAULT now() NOT NULL,
    product_refresh_time timestamp with time zone NOT NULL,
    footprint_count integer NOT NULL,
    footprint_geometry public.geometry(Geometry,3577),
    crses character varying[],
    size_bytes bigint,
    CONSTRAINT timeline_lengths_equal CHECK ((array_length(timeline_dataset_start_days, 1) = array_length(timeline_dataset_counts, 1)))
);


ALTER TABLE cubedash.time_overview OWNER TO opendatacubeusername;

--
-- Name: COLUMN time_overview.product_refresh_time; Type: COMMENT; Schema: cubedash; Owner: opendatacubeusername
--

COMMENT ON COLUMN cubedash.time_overview.product_refresh_time IS 'The ''last_refresh'' timestamp of the product at the time of generation.';


--
-- Name: dataset_location id; Type: DEFAULT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_location ALTER COLUMN id SET DEFAULT nextval('agdc.dataset_location_id_seq'::regclass);


--
-- Name: dataset_type id; Type: DEFAULT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_type ALTER COLUMN id SET DEFAULT nextval('agdc.dataset_type_id_seq'::regclass);


--
-- Name: metadata_type id; Type: DEFAULT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.metadata_type ALTER COLUMN id SET DEFAULT nextval('agdc.metadata_type_id_seq'::regclass);


--
-- Name: product id; Type: DEFAULT; Schema: cubedash; Owner: opendatacubeusername
--

ALTER TABLE ONLY cubedash.product ALTER COLUMN id SET DEFAULT nextval('cubedash.product_id_seq'::regclass);


--
-- Data for Name: dataset; Type: TABLE DATA; Schema: agdc; Owner: agdc_admin
--

COPY agdc.dataset (id, metadata_type_ref, dataset_type_ref, metadata, archived, added, added_by, updated) FROM stdin;
f0298262-f75f-46b0-ac96-2ee2cc54b887	2	7	{"id": "f0298262-f75f-46b0-ac96-2ee2cc54b887", "image": {"bands": {"water": {"path": "LS_WATER_3577_6_-29_20040503003241500000_v1526732475_water.tif", "layer": "1"}}}, "extent": {"coord": {"ll": {"lat": -26.633117872794404, "lon": 138.10214993521586}, "lr": {"lat": -26.58701097230756, "lon": 139.11722174862368}, "ul": {"lat": -25.74238576895223, "lon": 138.05399228622116}, "ur": {"lat": -25.69662207732709, "lon": 139.06108367522793}}, "to_dt": "2004-05-03T00:32:41.500000", "from_dt": "2004-05-03T00:32:41.500000", "center_dt": "2004-05-03T00:32:41.500000"}, "format": {"name": "GeoTIFF"}, "lineage": {"source_datasets": {}}, "platform": {"code": "LANDSAT_7"}, "instrument": {"name": "ETM"}, "creation_dt": "2018-05-20T08:30:52.436405", "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[600000.0, -2900000.0], [600000.0, -2800000.0], [700000.0, -2800000.0], [700000.0, -2852570.2414837102], [692582.7675296998, -2880061.0703851306], [687199.1863652642, -2900000.0], [600000.0, -2900000.0]]]}, "geo_ref_points": {"ll": {"x": 600000.0, "y": -2900000.0}, "lr": {"x": 700000.0, "y": -2900000.0}, "ul": {"x": 600000.0, "y": -2800000.0}, "ur": {"x": 700000.0, "y": -2800000.0}}, "spatial_reference": "EPSG:3577"}}, "product_type": "wofs"}	\N	2021-08-27 06:08:28.814926+00	opendatacubeusername	\N
830ca898-2874-45ae-afe5-575dbf52f1ec	2	8	{"id": "830ca898-2874-45ae-afe5-575dbf52f1ec", "image": {"bands": {"BS": {"path": "LS5_TM_FC_3577_6_-29_20040511002356_BS.tif"}, "PV": {"path": "LS5_TM_FC_3577_6_-29_20040511002356_PV.tif"}, "UE": {"path": "LS5_TM_FC_3577_6_-29_20040511002356_UE.tif"}, "NPV": {"path": "LS5_TM_FC_3577_6_-29_20040511002356_NPV.tif"}}}, "extent": {"coord": {"ll": {"lat": -26.633117872794404, "lon": 138.10214993521586}, "lr": {"lat": -26.58701097230756, "lon": 139.11722174862368}, "ul": {"lat": -25.74238576895223, "lon": 138.05399228622116}, "ur": {"lat": -25.69662207732709, "lon": 139.06108367522793}}, "to_dt": "2004-05-11T00:23:56.500000", "from_dt": "2004-05-11T00:23:56.500000", "center_dt": "2004-05-11T00:23:56.500000"}, "format": {"name": "GeoTIFF"}, "lineage": {"source_datasets": {}}, "platform": {"code": "LANDSAT_5"}, "instrument": {"name": "TM"}, "creation_dt": "2017-10-24T10:01:27.946578", "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[600000.0, -2900000.0], [600000.0, -2800000.0], [700000.0, -2800000.0], [700000.0, -2881829.4147167434], [695085.2947384067, -2900000.0], [600000.0, -2900000.0]]]}, "geo_ref_points": {"ll": {"x": 600000.0, "y": -2900000.0}, "lr": {"x": 700000.0, "y": -2900000.0}, "ul": {"x": 600000.0, "y": -2800000.0}, "ur": {"x": 700000.0, "y": -2800000.0}}, "spatial_reference": "EPSG:3577"}}, "product_type": "fractional_cover"}	\N	2021-08-27 06:08:31.252026+00	opendatacubeusername	\N
8f27ae72-ed82-461d-ac05-771f772a988e	2	10	{"id": "8f27ae72-ed82-461d-ac05-771f772a988e", "image": {"bands": {"BS": {"path": "LS7_ETM_FC_3577_6_-29_20040519003242_BS.tif"}, "PV": {"path": "LS7_ETM_FC_3577_6_-29_20040519003242_PV.tif"}, "UE": {"path": "LS7_ETM_FC_3577_6_-29_20040519003242_UE.tif"}, "NPV": {"path": "LS7_ETM_FC_3577_6_-29_20040519003242_NPV.tif"}}}, "extent": {"coord": {"ll": {"lat": -26.633117872794404, "lon": 138.10214993521586}, "lr": {"lat": -26.58701097230756, "lon": 139.11722174862368}, "ul": {"lat": -25.74238576895223, "lon": 138.05399228622116}, "ur": {"lat": -25.69662207732709, "lon": 139.06108367522793}}, "to_dt": "2004-05-19T00:32:42.500000", "from_dt": "2004-05-19T00:32:42.500000", "center_dt": "2004-05-19T00:32:42.500000"}, "format": {"name": "GeoTIFF"}, "lineage": {"source_datasets": {}}, "platform": {"code": "LANDSAT_7"}, "instrument": {"name": "ETM"}, "creation_dt": "2017-10-21T15:03:14.340143", "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[600000.0, -2900000.0], [600000.0, -2800000.0], [700000.0, -2800000.0], [700000.0, -2865577.4448543955], [690725.0803638548, -2900000.0], [600000.0, -2900000.0]]]}, "geo_ref_points": {"ll": {"x": 600000.0, "y": -2900000.0}, "lr": {"x": 700000.0, "y": -2900000.0}, "ul": {"x": 600000.0, "y": -2800000.0}, "ur": {"x": 700000.0, "y": -2800000.0}}, "spatial_reference": "EPSG:3577"}}, "product_type": "fractional_cover"}	\N	2021-08-27 06:08:33.718978+00	opendatacubeusername	\N
345aff57-ae5b-4b41-bf6c-b5b2a327861a	2	9	{"id": "345aff57-ae5b-4b41-bf6c-b5b2a327861a", "image": {"bands": {"BS": {"path": "LS8_OLI_FC_3577_6_-29_20180527003612_BS.tif"}, "PV": {"path": "LS8_OLI_FC_3577_6_-29_20180527003612_PV.tif"}, "UE": {"path": "LS8_OLI_FC_3577_6_-29_20180527003612_UE.tif"}, "NPV": {"path": "LS8_OLI_FC_3577_6_-29_20180527003612_NPV.tif"}}}, "extent": {"coord": {"ll": {"lat": -26.610678986675257, "lon": 138.61572818003324}, "lr": {"lat": -26.58701097230756, "lon": 139.11722174862368}, "ul": {"lat": -25.720114016315517, "lon": 138.56353118741364}, "ur": {"lat": -25.69662207732709, "lon": 139.06108367522793}}, "to_dt": "2018-05-27T00:36:12", "from_dt": "2018-05-27T00:36:12", "center_dt": "2018-05-27T00:36:12"}, "format": {"name": "GeoTIFF"}, "lineage": {"source_datasets": {}}, "platform": {"code": "LANDSAT_8"}, "instrument": {"name": "OLI_TIRS"}, "creation_dt": "2018-08-04T01:00:38.077435", "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[700000.0, -2900000.0], [650584.9744319875, -2900000.0], [656822.1892229056, -2877834.362400513], [676071.0769201876, -2809553.3614070467], [678771.6215446597, -2800000.0], [700000.0, -2800000.0], [700000.0, -2900000.0]]]}, "geo_ref_points": {"ll": {"x": 600000.0, "y": -2900000.0}, "lr": {"x": 700000.0, "y": -2900000.0}, "ul": {"x": 600000.0, "y": -2800000.0}, "ur": {"x": 700000.0, "y": -2800000.0}}, "spatial_reference": "EPSG:3577"}}, "product_type": "fractional_cover"}	\N	2021-08-27 06:08:36.170463+00	opendatacubeusername	\N
e6e62140-b8d7-46cd-8530-ad9d682f82f5	4	1	{"id": "e6e62140-b8d7-46cd-8530-ad9d682f82f5", "image": {"bands": {"fmask": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_FMASK.TIF", "layer": 1}, "exiting": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_EXITING.TIF", "layer": 1}, "incident": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_INCIDENT.TIF", "layer": 1}, "nbar_red": {"path": "NBAR/NBAR_B04.TIF", "layer": 1}, "nbar_blue": {"path": "NBAR/NBAR_B02.TIF", "layer": 1}, "nbart_red": {"path": "NBART/NBART_B04.TIF", "layer": 1}, "timedelta": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_TIMEDELTA.TIF", "layer": 1}, "nbar_green": {"path": "NBAR/NBAR_B03.TIF", "layer": 1}, "nbar_nir_1": {"path": "NBAR/NBAR_B08.TIF", "layer": 1}, "nbar_nir_2": {"path": "NBAR/NBAR_B8A.TIF", "layer": 1}, "nbart_blue": {"path": "NBART/NBART_B02.TIF", "layer": 1}, "nbar_swir_2": {"path": "NBAR/NBAR_B11.TIF", "layer": 1}, "nbar_swir_3": {"path": "NBAR/NBAR_B12.TIF", "layer": 1}, "nbart_green": {"path": "NBART/NBART_B03.TIF", "layer": 1}, "nbart_nir_1": {"path": "NBART/NBART_B08.TIF", "layer": 1}, "nbart_nir_2": {"path": "NBART/NBART_B8A.TIF", "layer": 1}, "nbart_swir_2": {"path": "NBART/NBART_B11.TIF", "layer": 1}, "nbart_swir_3": {"path": "NBART/NBART_B12.TIF", "layer": 1}, "solar_zenith": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_SOLAR_ZENITH.TIF", "layer": 1}, "solar_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_SOLAR_AZIMUTH.TIF", "layer": 1}, "lambertian_red": {"path": "LAMBERTIAN/LAMBERTIAN_B04.TIF", "layer": 1}, "relative_slope": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_RELATIVE_SLOPE.TIF", "layer": 1}, "satellite_view": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_SATELLITE_VIEW.TIF", "layer": 1}, "terrain_shadow": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_COMBINED_TERRAIN_SHADOW.TIF", "layer": 1}, "lambertian_blue": {"path": "LAMBERTIAN/LAMBERTIAN_B02.TIF", "layer": 1}, "nbar_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_NBAR_CONTIGUITY.TIF", "layer": 1}, "nbar_red_edge_1": {"path": "NBAR/NBAR_B05.TIF", "layer": 1}, "nbar_red_edge_2": {"path": "NBAR/NBAR_B06.TIF", "layer": 1}, "nbar_red_edge_3": {"path": "NBAR/NBAR_B07.TIF", "layer": 1}, "lambertian_green": {"path": "LAMBERTIAN/LAMBERTIAN_B03.TIF", "layer": 1}, "lambertian_nir_1": {"path": "LAMBERTIAN/LAMBERTIAN_B08.TIF", "layer": 1}, "lambertian_nir_2": {"path": "LAMBERTIAN/LAMBERTIAN_B8A.TIF", "layer": 1}, "nbart_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_NBART_CONTIGUITY.TIF", "layer": 1}, "nbart_red_edge_1": {"path": "NBART/NBART_B05.TIF", "layer": 1}, "nbart_red_edge_2": {"path": "NBART/NBART_B06.TIF", "layer": 1}, "nbart_red_edge_3": {"path": "NBART/NBART_B07.TIF", "layer": 1}, "relative_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_RELATIVE_AZIMUTH.TIF", "layer": 1}, "azimuthal_exiting": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_AZIMUTHAL_EXITING.TIF", "layer": 1}, "lambertian_swir_2": {"path": "LAMBERTIAN/LAMBERTIAN_B11.TIF", "layer": 1}, "lambertian_swir_3": {"path": "LAMBERTIAN/LAMBERTIAN_B12.TIF", "layer": 1}, "satellite_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_SATELLITE_AZIMUTH.TIF", "layer": 1}, "azimuthal_incident": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_AZIMUTHAL_INCIDENT.TIF", "layer": 1}, "nbar_coastal_aerosol": {"path": "NBAR/NBAR_B01.TIF", "layer": 1}, "lambertian_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00_LAMBERTIAN_CONTIGUITY.TIF", "layer": 1}, "lambertian_red_edge_1": {"path": "LAMBERTIAN/LAMBERTIAN_B05.TIF", "layer": 1}, "lambertian_red_edge_2": {"path": "LAMBERTIAN/LAMBERTIAN_B06.TIF", "layer": 1}, "lambertian_red_edge_3": {"path": "LAMBERTIAN/LAMBERTIAN_B07.TIF", "layer": 1}, "nbart_coastal_aerosol": {"path": "NBART/NBART_B01.TIF", "layer": 1}, "lambertian_coastal_aerosol": {"path": "LAMBERTIAN/LAMBERTIAN_B01.TIF", "layer": 1}}}, "extent": {"coord": {"ll": {"lat": -29.012092805437124, "lon": 154.02678497014153}, "lr": {"lat": -28.99875640887199, "lon": 155.15370903939606}, "ul": {"lat": -28.021128917258025, "lon": 154.01722938139588}, "ur": {"lat": -28.008328690055933, "lon": 155.1336803191767}}, "center_dt": "2021-06-29T23:54:36.819617Z"}, "format": {"name": "GeoTiff"}, "lineage": {"ancillary": {"ozone": {"url": "file:///ancillary/ozone/jun.tif", "atime": "2021-06-30T03:05:25.247072", "ctime": "2021-06-30T02:50:06.148023", "mtime": "2017-05-31T06:32:41", "owner": ",,,", "value": 0.28}, "aerosol": {"value": 0.06}, "elevation": {"url": "file:///ancillary/elevation/world_1deg/DEM_one_deg.tif", "atime": "2021-06-30T03:05:25.275070", "ctime": "2021-06-30T02:50:06.148023", "mtime": "2017-05-31T08:03:53", "owner": ",,,", "value": 0.0}, "water_vapour": {"url": "file:///ancillary/water_vapour/pr_wtr.eatm.2021.tif", "atime": "2021-06-30T03:05:25.071078", "ctime": "2021-06-30T02:51:36.751386", "mtime": "2021-06-30T02:20:39", "owner": ",,,", "value": 1.4100000381469728}, "brdf_geo_band_2": {"type": "brdf_geo_band_2", "value": 0.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}, "brdf_geo_band_3": {"type": "brdf_geo_band_3", "value": 0.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}, "brdf_geo_band_4": {"type": "brdf_geo_band_4", "value": 0.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}, "brdf_geo_band_8": {"type": "brdf_geo_band_8", "value": 0.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}, "brdf_iso_band_2": {"type": "brdf_iso_band_2", "value": 1.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}, "brdf_iso_band_3": {"type": "brdf_iso_band_3", "value": 1.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}, "brdf_iso_band_4": {"type": "brdf_iso_band_4", "value": 1.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}, "brdf_iso_band_8": {"type": "brdf_iso_band_8", "value": 1.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}, "brdf_vol_band_2": {"type": "brdf_vol_band_2", "value": 0.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}, "brdf_vol_band_3": {"type": "brdf_vol_band_3", "value": 0.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}, "brdf_vol_band_4": {"type": "brdf_vol_band_4", "value": 0.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}, "brdf_vol_band_8": {"type": "brdf_vol_band_8", "value": 0.0, "extents": "POLYGON ((154.0172293813958788 -28.0211289172580251, 155.1537090393960625 -28.0211289172580251, 155.1537090393960625 -28.9987564088719907, 154.0172293813958788 -28.9987564088719907, 154.0172293813958788 -28.0211289172580251))"}}, "source_datasets": {}}, "tile_id": "S2A_OPER_MSI_L1C_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00", "platform": {"code": "SENTINEL_2A"}, "instrument": {"name": "MSI"}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[709800.0, 6900040.0], [600000.0, 6900040.0], [600000.0, 6790240.0], [709800.0, 6790240.0], [709800.0, 6900040.0]]]}, "geo_ref_points": {"ll": {"x": 600000, "y": 6790240}, "lr": {"x": 709800, "y": 6790240}, "ul": {"x": 600000, "y": 6900040}, "ur": {"x": 709800, "y": 6900040}}, "spatial_reference": "PROJCS[\\"WGS 84 / UTM zone 56S\\",GEOGCS[\\"WGS 84\\",DATUM[\\"WGS_1984\\",SPHEROID[\\"WGS 84\\",6378137,298.257223563,AUTHORITY[\\"EPSG\\",\\"7030\\"]],AUTHORITY[\\"EPSG\\",\\"6326\\"]],PRIMEM[\\"Greenwich\\",0,AUTHORITY[\\"EPSG\\",\\"8901\\"]],UNIT[\\"degree\\",0.0174532925199433,AUTHORITY[\\"EPSG\\",\\"9122\\"]],AUTHORITY[\\"EPSG\\",\\"4326\\"]],PROJECTION[\\"Transverse_Mercator\\"],PARAMETER[\\"latitude_of_origin\\",0],PARAMETER[\\"central_meridian\\",153],PARAMETER[\\"scale_factor\\",0.9996],PARAMETER[\\"false_easting\\",500000],PARAMETER[\\"false_northing\\",10000000],UNIT[\\"metre\\",1,AUTHORITY[\\"EPSG\\",\\"9001\\"]],AXIS[\\"Easting\\",EAST],AXIS[\\"Northing\\",NORTH],AUTHORITY[\\"EPSG\\",\\"32756\\"]]"}}, "product_type": "ard", "processing_level": "Level-2", "software_versions": {"wagl": {"version": "5.0.5+33.g94f1105.dirty", "repo_url": "https://github.com/GeoscienceAustralia/wagl.git"}, "modtran": {"version": "5.2.1", "repo_url": "http://www.ontar.com/software/productdetails.aspx?item=modtran"}}, "system_information": {"uname": "Linux ip-10-0-11-39.ap-southeast-2.compute.internal 4.14.186-146.268.amzn2.x86_64 #1 SMP Tue Jul 14 18:16:52 UTC 2020 x86_64", "hostname": "ip-10-0-11-39.ap-southeast-2.compute.internal", "runtime_id": "561e72b4-d957-11eb-a493-024b24434e70", "time_processed": "2021-06-30T03:57:49.515075"}, "algorithm_information": {"nbar_doi": "http://dx.doi.org/10.1109/JSTARS.2010.2042281", "arg25_doi": "http://dx.doi.org/10.4225/25/5487CC0D4F40B", "algorithm_version": 2.0, "nbar_terrain_corrected_doi": "http://dx.doi.org/10.1016/j.rse.2012.06.018"}}	\N	2021-08-29 22:59:43.133788+00	opendatacubeusername	\N
6621a608-9c61-4c9b-aa5d-312f6a32866f	4	1	{"id": "6621a608-9c61-4c9b-aa5d-312f6a32866f", "image": {"bands": {"fmask": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_FMASK.TIF", "layer": 1}, "exiting": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_EXITING.TIF", "layer": 1}, "incident": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_INCIDENT.TIF", "layer": 1}, "nbar_red": {"path": "NBAR/NBAR_B04.TIF", "layer": 1}, "nbar_blue": {"path": "NBAR/NBAR_B02.TIF", "layer": 1}, "nbart_red": {"path": "NBART/NBART_B04.TIF", "layer": 1}, "timedelta": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_TIMEDELTA.TIF", "layer": 1}, "nbar_green": {"path": "NBAR/NBAR_B03.TIF", "layer": 1}, "nbar_nir_1": {"path": "NBAR/NBAR_B08.TIF", "layer": 1}, "nbar_nir_2": {"path": "NBAR/NBAR_B8A.TIF", "layer": 1}, "nbart_blue": {"path": "NBART/NBART_B02.TIF", "layer": 1}, "nbar_swir_2": {"path": "NBAR/NBAR_B11.TIF", "layer": 1}, "nbar_swir_3": {"path": "NBAR/NBAR_B12.TIF", "layer": 1}, "nbart_green": {"path": "NBART/NBART_B03.TIF", "layer": 1}, "nbart_nir_1": {"path": "NBART/NBART_B08.TIF", "layer": 1}, "nbart_nir_2": {"path": "NBART/NBART_B8A.TIF", "layer": 1}, "nbart_swir_2": {"path": "NBART/NBART_B11.TIF", "layer": 1}, "nbart_swir_3": {"path": "NBART/NBART_B12.TIF", "layer": 1}, "solar_zenith": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_SOLAR_ZENITH.TIF", "layer": 1}, "solar_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_SOLAR_AZIMUTH.TIF", "layer": 1}, "lambertian_red": {"path": "LAMBERTIAN/LAMBERTIAN_B04.TIF", "layer": 1}, "relative_slope": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_RELATIVE_SLOPE.TIF", "layer": 1}, "satellite_view": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_SATELLITE_VIEW.TIF", "layer": 1}, "terrain_shadow": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_COMBINED_TERRAIN_SHADOW.TIF", "layer": 1}, "lambertian_blue": {"path": "LAMBERTIAN/LAMBERTIAN_B02.TIF", "layer": 1}, "nbar_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_NBAR_CONTIGUITY.TIF", "layer": 1}, "nbar_red_edge_1": {"path": "NBAR/NBAR_B05.TIF", "layer": 1}, "nbar_red_edge_2": {"path": "NBAR/NBAR_B06.TIF", "layer": 1}, "nbar_red_edge_3": {"path": "NBAR/NBAR_B07.TIF", "layer": 1}, "lambertian_green": {"path": "LAMBERTIAN/LAMBERTIAN_B03.TIF", "layer": 1}, "lambertian_nir_1": {"path": "LAMBERTIAN/LAMBERTIAN_B08.TIF", "layer": 1}, "lambertian_nir_2": {"path": "LAMBERTIAN/LAMBERTIAN_B8A.TIF", "layer": 1}, "nbart_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_NBART_CONTIGUITY.TIF", "layer": 1}, "nbart_red_edge_1": {"path": "NBART/NBART_B05.TIF", "layer": 1}, "nbart_red_edge_2": {"path": "NBART/NBART_B06.TIF", "layer": 1}, "nbart_red_edge_3": {"path": "NBART/NBART_B07.TIF", "layer": 1}, "relative_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_RELATIVE_AZIMUTH.TIF", "layer": 1}, "azimuthal_exiting": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_AZIMUTHAL_EXITING.TIF", "layer": 1}, "lambertian_swir_2": {"path": "LAMBERTIAN/LAMBERTIAN_B11.TIF", "layer": 1}, "lambertian_swir_3": {"path": "LAMBERTIAN/LAMBERTIAN_B12.TIF", "layer": 1}, "satellite_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_SATELLITE_AZIMUTH.TIF", "layer": 1}, "azimuthal_incident": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_AZIMUTHAL_INCIDENT.TIF", "layer": 1}, "nbar_coastal_aerosol": {"path": "NBAR/NBAR_B01.TIF", "layer": 1}, "lambertian_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01_LAMBERTIAN_CONTIGUITY.TIF", "layer": 1}, "lambertian_red_edge_1": {"path": "LAMBERTIAN/LAMBERTIAN_B05.TIF", "layer": 1}, "lambertian_red_edge_2": {"path": "LAMBERTIAN/LAMBERTIAN_B06.TIF", "layer": 1}, "lambertian_red_edge_3": {"path": "LAMBERTIAN/LAMBERTIAN_B07.TIF", "layer": 1}, "nbart_coastal_aerosol": {"path": "NBART/NBART_B01.TIF", "layer": 1}, "lambertian_coastal_aerosol": {"path": "LAMBERTIAN/LAMBERTIAN_B01.TIF", "layer": 1}}}, "extent": {"coord": {"ll": {"lat": -22.692427357900442, "lon": 153.9735606070099}, "lr": {"lat": -22.682359869340228, "lon": 155.04214455242328}, "ul": {"lat": -21.70059872460509, "lon": 153.9667468166053}, "ur": {"lat": -21.691015824552036, "lon": 155.0278611731415}}, "center_dt": "2021-08-28T23:52:57.049593Z"}, "format": {"name": "GeoTiff"}, "lineage": {"ancillary": {"ozone": {"url": "file:///ancillary/ozone/aug.tif", "atime": "2021-08-29T02:46:29.098255", "ctime": "2021-08-29T02:31:29.369903", "mtime": "2017-05-31T06:32:41", "owner": ",,,", "value": 0.27500001}, "aerosol": {"value": 0.06}, "elevation": {"url": "file:///ancillary/elevation/world_1deg/DEM_one_deg.tif", "atime": "2021-08-29T02:46:29.126254", "ctime": "2021-08-29T02:31:29.369903", "mtime": "2017-05-31T08:03:53", "owner": ",,,", "value": 0.0}, "water_vapour": {"url": "file:///ancillary/water_vapour/pr_wtr.eatm.2021.tif", "atime": "2021-08-29T02:46:28.974257", "ctime": "2021-08-29T02:32:39.450303", "mtime": "2021-08-29T00:42:49", "owner": ",,,", "value": 1.8600000381469728}, "brdf_geo_band_2": {"type": "brdf_geo_band_2", "value": 0.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}, "brdf_geo_band_3": {"type": "brdf_geo_band_3", "value": 0.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}, "brdf_geo_band_4": {"type": "brdf_geo_band_4", "value": 0.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}, "brdf_geo_band_8": {"type": "brdf_geo_band_8", "value": 0.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}, "brdf_iso_band_2": {"type": "brdf_iso_band_2", "value": 1.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}, "brdf_iso_band_3": {"type": "brdf_iso_band_3", "value": 1.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}, "brdf_iso_band_4": {"type": "brdf_iso_band_4", "value": 1.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}, "brdf_iso_band_8": {"type": "brdf_iso_band_8", "value": 1.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}, "brdf_vol_band_2": {"type": "brdf_vol_band_2", "value": 0.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}, "brdf_vol_band_3": {"type": "brdf_vol_band_3", "value": 0.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}, "brdf_vol_band_4": {"type": "brdf_vol_band_4", "value": 0.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}, "brdf_vol_band_8": {"type": "brdf_vol_band_8", "value": 0.0, "extents": "POLYGON ((153.9667468166053084 -21.7005987246050900, 155.0421445524232809 -21.7005987246050900, 155.0421445524232809 -22.6823598693402282, 153.9667468166053084 -22.6823598693402282, 153.9667468166053084 -21.7005987246050900))"}}, "source_datasets": {}}, "tile_id": "S2A_OPER_MSI_L1C_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01", "platform": {"code": "SENTINEL_2A"}, "instrument": {"name": "MSI"}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[646740.0, 7577380.0], [646441.7914499913, 7577274.5521375025], [624720.0, 7490200.0], [709800.0, 7490200.0], [709800.0, 7564301.229824136], [696072.1563362421, 7567418.755625171], [646740.0, 7577380.0]]]}, "geo_ref_points": {"ll": {"x": 600000, "y": 7490200}, "lr": {"x": 709800, "y": 7490200}, "ul": {"x": 600000, "y": 7600000}, "ur": {"x": 709800, "y": 7600000}}, "spatial_reference": "PROJCS[\\"WGS 84 / UTM zone 56S\\",GEOGCS[\\"WGS 84\\",DATUM[\\"WGS_1984\\",SPHEROID[\\"WGS 84\\",6378137,298.257223563,AUTHORITY[\\"EPSG\\",\\"7030\\"]],AUTHORITY[\\"EPSG\\",\\"6326\\"]],PRIMEM[\\"Greenwich\\",0,AUTHORITY[\\"EPSG\\",\\"8901\\"]],UNIT[\\"degree\\",0.0174532925199433,AUTHORITY[\\"EPSG\\",\\"9122\\"]],AUTHORITY[\\"EPSG\\",\\"4326\\"]],PROJECTION[\\"Transverse_Mercator\\"],PARAMETER[\\"latitude_of_origin\\",0],PARAMETER[\\"central_meridian\\",153],PARAMETER[\\"scale_factor\\",0.9996],PARAMETER[\\"false_easting\\",500000],PARAMETER[\\"false_northing\\",10000000],UNIT[\\"metre\\",1,AUTHORITY[\\"EPSG\\",\\"9001\\"]],AXIS[\\"Easting\\",EAST],AXIS[\\"Northing\\",NORTH],AUTHORITY[\\"EPSG\\",\\"32756\\"]]"}}, "product_type": "ard", "processing_level": "Level-2", "software_versions": {"wagl": {"version": "5.0.5+33.g94f1105.dirty", "repo_url": "https://github.com/GeoscienceAustralia/wagl.git"}, "modtran": {"version": "5.2.1", "repo_url": "http://www.ontar.com/software/productdetails.aspx?item=modtran"}}, "system_information": {"uname": "Linux ip-10-0-10-98.ap-southeast-2.compute.internal 4.14.186-146.268.amzn2.x86_64 #1 SMP Tue Jul 14 18:16:52 UTC 2020 x86_64", "hostname": "ip-10-0-10-98.ap-southeast-2.compute.internal", "runtime_id": "56acd354-087a-11ec-85f5-06e1bf61f272", "time_processed": "2021-08-29T03:36:47.484233"}, "algorithm_information": {"nbar_doi": "http://dx.doi.org/10.1109/JSTARS.2010.2042281", "arg25_doi": "http://dx.doi.org/10.4225/25/5487CC0D4F40B", "algorithm_version": 2.0, "nbar_terrain_corrected_doi": "http://dx.doi.org/10.1016/j.rse.2012.06.018"}}	\N	2021-08-29 23:02:35.86439+00	opendatacubeusername	\N
ccf58424-a33f-4cb1-9841-a5f5cf652ea9	4	1	{"id": "ccf58424-a33f-4cb1-9841-a5f5cf652ea9", "image": {"bands": {"fmask": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_FMASK.TIF", "layer": 1}, "exiting": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_EXITING.TIF", "layer": 1}, "incident": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_INCIDENT.TIF", "layer": 1}, "nbar_red": {"path": "NBAR/NBAR_B04.TIF", "layer": 1}, "nbar_blue": {"path": "NBAR/NBAR_B02.TIF", "layer": 1}, "nbart_red": {"path": "NBART/NBART_B04.TIF", "layer": 1}, "timedelta": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_TIMEDELTA.TIF", "layer": 1}, "nbar_green": {"path": "NBAR/NBAR_B03.TIF", "layer": 1}, "nbar_nir_1": {"path": "NBAR/NBAR_B08.TIF", "layer": 1}, "nbar_nir_2": {"path": "NBAR/NBAR_B8A.TIF", "layer": 1}, "nbart_blue": {"path": "NBART/NBART_B02.TIF", "layer": 1}, "nbar_swir_2": {"path": "NBAR/NBAR_B11.TIF", "layer": 1}, "nbar_swir_3": {"path": "NBAR/NBAR_B12.TIF", "layer": 1}, "nbart_green": {"path": "NBART/NBART_B03.TIF", "layer": 1}, "nbart_nir_1": {"path": "NBART/NBART_B08.TIF", "layer": 1}, "nbart_nir_2": {"path": "NBART/NBART_B8A.TIF", "layer": 1}, "nbart_swir_2": {"path": "NBART/NBART_B11.TIF", "layer": 1}, "nbart_swir_3": {"path": "NBART/NBART_B12.TIF", "layer": 1}, "solar_zenith": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_SOLAR_ZENITH.TIF", "layer": 1}, "solar_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_SOLAR_AZIMUTH.TIF", "layer": 1}, "lambertian_red": {"path": "LAMBERTIAN/LAMBERTIAN_B04.TIF", "layer": 1}, "relative_slope": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_RELATIVE_SLOPE.TIF", "layer": 1}, "satellite_view": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_SATELLITE_VIEW.TIF", "layer": 1}, "terrain_shadow": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_COMBINED_TERRAIN_SHADOW.TIF", "layer": 1}, "lambertian_blue": {"path": "LAMBERTIAN/LAMBERTIAN_B02.TIF", "layer": 1}, "nbar_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_NBAR_CONTIGUITY.TIF", "layer": 1}, "nbar_red_edge_1": {"path": "NBAR/NBAR_B05.TIF", "layer": 1}, "nbar_red_edge_2": {"path": "NBAR/NBAR_B06.TIF", "layer": 1}, "nbar_red_edge_3": {"path": "NBAR/NBAR_B07.TIF", "layer": 1}, "lambertian_green": {"path": "LAMBERTIAN/LAMBERTIAN_B03.TIF", "layer": 1}, "lambertian_nir_1": {"path": "LAMBERTIAN/LAMBERTIAN_B08.TIF", "layer": 1}, "lambertian_nir_2": {"path": "LAMBERTIAN/LAMBERTIAN_B8A.TIF", "layer": 1}, "nbart_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_NBART_CONTIGUITY.TIF", "layer": 1}, "nbart_red_edge_1": {"path": "NBART/NBART_B05.TIF", "layer": 1}, "nbart_red_edge_2": {"path": "NBART/NBART_B06.TIF", "layer": 1}, "nbart_red_edge_3": {"path": "NBART/NBART_B07.TIF", "layer": 1}, "relative_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_RELATIVE_AZIMUTH.TIF", "layer": 1}, "azimuthal_exiting": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_AZIMUTHAL_EXITING.TIF", "layer": 1}, "lambertian_swir_2": {"path": "LAMBERTIAN/LAMBERTIAN_B11.TIF", "layer": 1}, "lambertian_swir_3": {"path": "LAMBERTIAN/LAMBERTIAN_B12.TIF", "layer": 1}, "satellite_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_SATELLITE_AZIMUTH.TIF", "layer": 1}, "azimuthal_incident": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_AZIMUTHAL_INCIDENT.TIF", "layer": 1}, "nbar_coastal_aerosol": {"path": "NBAR/NBAR_B01.TIF", "layer": 1}, "lambertian_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01_LAMBERTIAN_CONTIGUITY.TIF", "layer": 1}, "lambertian_red_edge_1": {"path": "LAMBERTIAN/LAMBERTIAN_B05.TIF", "layer": 1}, "lambertian_red_edge_2": {"path": "LAMBERTIAN/LAMBERTIAN_B06.TIF", "layer": 1}, "lambertian_red_edge_3": {"path": "LAMBERTIAN/LAMBERTIAN_B07.TIF", "layer": 1}, "nbart_coastal_aerosol": {"path": "NBART/NBART_B01.TIF", "layer": 1}, "lambertian_coastal_aerosol": {"path": "LAMBERTIAN/LAMBERTIAN_B01.TIF", "layer": 1}}}, "extent": {"coord": {"ll": {"lat": -31.723243569066117, "lon": 152.99978889138296}, "lr": {"lat": -31.717977927487997, "lon": 154.15867410019217}, "ul": {"lat": -30.73252861587539, "lon": 152.99979108230477}, "ur": {"lat": -30.727463361500085, "lon": 154.14665240689393}}, "center_dt": "2021-08-28T23:55:23.726121Z"}, "format": {"name": "GeoTiff"}, "lineage": {"ancillary": {"ozone": {"url": "file:///ancillary/ozone/aug.tif", "atime": "2021-08-29T02:43:48.804466", "ctime": "2021-08-29T02:29:12.708233", "mtime": "2017-05-31T06:32:41", "owner": ",,,", "value": 0.30599999}, "aerosol": {"value": 0.06}, "elevation": {"url": "file:///ancillary/elevation/world_1deg/DEM_one_deg.tif", "atime": "2021-08-29T02:43:48.904464", "ctime": "2021-08-29T02:29:12.704233", "mtime": "2017-05-31T08:03:53", "owner": ",,,", "value": 0.003}, "water_vapour": {"url": "file:///ancillary/water_vapour/pr_wtr.eatm.2021.tif", "atime": "2021-08-29T02:43:48.680466", "ctime": "2021-08-29T02:30:27.819049", "mtime": "2021-08-29T00:42:49", "owner": ",,,", "value": 0.8699999809265138}, "brdf_geo_band_2": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b09.500m_0459_0479nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_2", "atime": "2021-08-29T02:51:45.620606", "ctime": "2021-08-29T02:30:16.531143", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.007370202020202021, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}, "brdf_geo_band_3": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b12.500m_0545_0565nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_3", "atime": "2021-08-29T02:51:48.428583", "ctime": "2021-08-29T02:30:22.307096", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.013550168350168349, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}, "brdf_geo_band_4": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b03.500m_0620_0670nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_4", "atime": "2021-08-29T02:51:52.488551", "ctime": "2021-08-29T02:30:11.023185", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.013882828282828283, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}, "brdf_geo_band_8": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b06.500m_0841_0876nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_8", "atime": "2021-08-29T02:51:56.468518", "ctime": "2021-08-29T02:30:15.687149", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.02993872053872054, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}, "brdf_iso_band_2": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b07.500m_0459_0479nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_2", "atime": "2021-08-29T02:43:48.912465", "ctime": "2021-08-29T02:30:16.587142", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.038781144781144784, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}, "brdf_iso_band_3": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b10.500m_0545_0565nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_3", "atime": "2021-08-29T02:51:46.564599", "ctime": "2021-08-29T02:30:17.919132", "mtime": "2017-05-31T23:49:36", "owner": ",,,", "value": 0.07207609427609428, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}, "brdf_iso_band_4": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b01.500m_0620_0670nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_4", "atime": "2021-08-29T02:51:49.804572", "ctime": "2021-08-29T02:30:10.775187", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.06914882154882156, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}, "brdf_iso_band_8": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b04.500m_0841_0876nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_8", "atime": "2021-08-29T02:51:53.768540", "ctime": "2021-08-29T02:30:11.063185", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.25223905723905726, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}, "brdf_vol_band_2": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b08.500m_0459_0479nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_2", "atime": "2021-08-29T02:51:44.756613", "ctime": "2021-08-29T02:30:16.539143", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.015471548821548824, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}, "brdf_vol_band_3": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b11.500m_0545_0565nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_3", "atime": "2021-08-29T02:51:47.500591", "ctime": "2021-08-29T02:30:21.303105", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.03458939393939394, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}, "brdf_vol_band_4": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b02.500m_0620_0670nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_4", "atime": "2021-08-29T02:51:51.292560", "ctime": "2021-08-29T02:30:10.779187", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.031962457912457914, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}, "brdf_vol_band_8": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b05.500m_0841_0876nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_8", "atime": "2021-08-29T02:51:55.168529", "ctime": "2021-08-29T02:30:12.831171", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.15019208754208757, "extents": "POLYGON ((152.9997910823047675 -30.7325286158753883, 154.1586741001921723 -30.7325286158753883, 154.1586741001921723 -31.7179779274879969, 152.9997910823047675 -31.7179779274879969, 152.9997910823047675 -30.7325286158753883))"}}, "source_datasets": {}}, "tile_id": "S2A_OPER_MSI_L1C_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01", "platform": {"code": "SENTINEL_2A"}, "instrument": {"name": "MSI"}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[609780.0, 6600040.0], [499980.0, 6600040.0], [499980.0, 6490240.0], [609780.0, 6490240.0], [609780.0, 6600040.0]]]}, "geo_ref_points": {"ll": {"x": 499980, "y": 6490240}, "lr": {"x": 609780, "y": 6490240}, "ul": {"x": 499980, "y": 6600040}, "ur": {"x": 609780, "y": 6600040}}, "spatial_reference": "PROJCS[\\"WGS 84 / UTM zone 56S\\",GEOGCS[\\"WGS 84\\",DATUM[\\"WGS_1984\\",SPHEROID[\\"WGS 84\\",6378137,298.257223563,AUTHORITY[\\"EPSG\\",\\"7030\\"]],AUTHORITY[\\"EPSG\\",\\"6326\\"]],PRIMEM[\\"Greenwich\\",0,AUTHORITY[\\"EPSG\\",\\"8901\\"]],UNIT[\\"degree\\",0.0174532925199433,AUTHORITY[\\"EPSG\\",\\"9122\\"]],AUTHORITY[\\"EPSG\\",\\"4326\\"]],PROJECTION[\\"Transverse_Mercator\\"],PARAMETER[\\"latitude_of_origin\\",0],PARAMETER[\\"central_meridian\\",153],PARAMETER[\\"scale_factor\\",0.9996],PARAMETER[\\"false_easting\\",500000],PARAMETER[\\"false_northing\\",10000000],UNIT[\\"metre\\",1,AUTHORITY[\\"EPSG\\",\\"9001\\"]],AXIS[\\"Easting\\",EAST],AXIS[\\"Northing\\",NORTH],AUTHORITY[\\"EPSG\\",\\"32756\\"]]"}}, "product_type": "ard", "processing_level": "Level-2", "software_versions": {"wagl": {"version": "5.0.5+33.g94f1105.dirty", "repo_url": "https://github.com/GeoscienceAustralia/wagl.git"}, "modtran": {"version": "5.2.1", "repo_url": "http://www.ontar.com/software/productdetails.aspx?item=modtran"}}, "system_information": {"uname": "Linux ip-10-0-11-70.ap-southeast-2.compute.internal 4.14.186-146.268.amzn2.x86_64 #1 SMP Tue Jul 14 18:16:52 UTC 2020 x86_64", "hostname": "ip-10-0-11-70.ap-southeast-2.compute.internal", "runtime_id": "e14ca978-087d-11ec-affa-029afcbc2626", "time_processed": "2021-08-29T04:02:08.547514"}, "algorithm_information": {"nbar_doi": "http://dx.doi.org/10.1109/JSTARS.2010.2042281", "arg25_doi": "http://dx.doi.org/10.4225/25/5487CC0D4F40B", "algorithm_version": 2.0, "nbar_terrain_corrected_doi": "http://dx.doi.org/10.1016/j.rse.2012.06.018"}}	\N	2021-08-29 23:02:39.495699+00	opendatacubeusername	\N
0cfbd2fc-a5db-4ae2-9ff1-e4266ad46a5f	4	1	{"id": "0cfbd2fc-a5db-4ae2-9ff1-e4266ad46a5f", "image": {"bands": {"fmask": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_FMASK.TIF", "layer": 1}, "exiting": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_EXITING.TIF", "layer": 1}, "incident": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_INCIDENT.TIF", "layer": 1}, "nbar_red": {"path": "NBAR/NBAR_B04.TIF", "layer": 1}, "nbar_blue": {"path": "NBAR/NBAR_B02.TIF", "layer": 1}, "nbart_red": {"path": "NBART/NBART_B04.TIF", "layer": 1}, "timedelta": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_TIMEDELTA.TIF", "layer": 1}, "nbar_green": {"path": "NBAR/NBAR_B03.TIF", "layer": 1}, "nbar_nir_1": {"path": "NBAR/NBAR_B08.TIF", "layer": 1}, "nbar_nir_2": {"path": "NBAR/NBAR_B8A.TIF", "layer": 1}, "nbart_blue": {"path": "NBART/NBART_B02.TIF", "layer": 1}, "nbar_swir_2": {"path": "NBAR/NBAR_B11.TIF", "layer": 1}, "nbar_swir_3": {"path": "NBAR/NBAR_B12.TIF", "layer": 1}, "nbart_green": {"path": "NBART/NBART_B03.TIF", "layer": 1}, "nbart_nir_1": {"path": "NBART/NBART_B08.TIF", "layer": 1}, "nbart_nir_2": {"path": "NBART/NBART_B8A.TIF", "layer": 1}, "nbart_swir_2": {"path": "NBART/NBART_B11.TIF", "layer": 1}, "nbart_swir_3": {"path": "NBART/NBART_B12.TIF", "layer": 1}, "solar_zenith": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_SOLAR_ZENITH.TIF", "layer": 1}, "solar_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_SOLAR_AZIMUTH.TIF", "layer": 1}, "lambertian_red": {"path": "LAMBERTIAN/LAMBERTIAN_B04.TIF", "layer": 1}, "relative_slope": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_RELATIVE_SLOPE.TIF", "layer": 1}, "satellite_view": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_SATELLITE_VIEW.TIF", "layer": 1}, "terrain_shadow": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_COMBINED_TERRAIN_SHADOW.TIF", "layer": 1}, "lambertian_blue": {"path": "LAMBERTIAN/LAMBERTIAN_B02.TIF", "layer": 1}, "nbar_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_NBAR_CONTIGUITY.TIF", "layer": 1}, "nbar_red_edge_1": {"path": "NBAR/NBAR_B05.TIF", "layer": 1}, "nbar_red_edge_2": {"path": "NBAR/NBAR_B06.TIF", "layer": 1}, "nbar_red_edge_3": {"path": "NBAR/NBAR_B07.TIF", "layer": 1}, "lambertian_green": {"path": "LAMBERTIAN/LAMBERTIAN_B03.TIF", "layer": 1}, "lambertian_nir_1": {"path": "LAMBERTIAN/LAMBERTIAN_B08.TIF", "layer": 1}, "lambertian_nir_2": {"path": "LAMBERTIAN/LAMBERTIAN_B8A.TIF", "layer": 1}, "nbart_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_NBART_CONTIGUITY.TIF", "layer": 1}, "nbart_red_edge_1": {"path": "NBART/NBART_B05.TIF", "layer": 1}, "nbart_red_edge_2": {"path": "NBART/NBART_B06.TIF", "layer": 1}, "nbart_red_edge_3": {"path": "NBART/NBART_B07.TIF", "layer": 1}, "relative_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_RELATIVE_AZIMUTH.TIF", "layer": 1}, "azimuthal_exiting": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_AZIMUTHAL_EXITING.TIF", "layer": 1}, "lambertian_swir_2": {"path": "LAMBERTIAN/LAMBERTIAN_B11.TIF", "layer": 1}, "lambertian_swir_3": {"path": "LAMBERTIAN/LAMBERTIAN_B12.TIF", "layer": 1}, "satellite_azimuth": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_SATELLITE_AZIMUTH.TIF", "layer": 1}, "azimuthal_incident": {"path": "SUPPLEMENTARY/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_AZIMUTHAL_INCIDENT.TIF", "layer": 1}, "nbar_coastal_aerosol": {"path": "NBAR/NBAR_B01.TIF", "layer": 1}, "lambertian_contiguity": {"path": "QA/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01_LAMBERTIAN_CONTIGUITY.TIF", "layer": 1}, "lambertian_red_edge_1": {"path": "LAMBERTIAN/LAMBERTIAN_B05.TIF", "layer": 1}, "lambertian_red_edge_2": {"path": "LAMBERTIAN/LAMBERTIAN_B06.TIF", "layer": 1}, "lambertian_red_edge_3": {"path": "LAMBERTIAN/LAMBERTIAN_B07.TIF", "layer": 1}, "nbart_coastal_aerosol": {"path": "NBART/NBART_B01.TIF", "layer": 1}, "lambertian_coastal_aerosol": {"path": "LAMBERTIAN/LAMBERTIAN_B01.TIF", "layer": 1}}}, "extent": {"coord": {"ll": {"lat": -27.196228082525234, "lon": 131.01868847804525}, "lr": {"lat": -27.175900164763846, "lon": 132.12607222519557}, "ul": {"lat": -26.205459050947727, "lon": 131.00129268177622}, "ur": {"lat": -26.185984543101256, "lon": 132.0991644527323}}, "center_dt": "2021-08-29T01:34:37.59306Z"}, "format": {"name": "GeoTiff"}, "lineage": {"ancillary": {"ozone": {"url": "file:///ancillary/ozone/aug.tif", "atime": "2021-08-29T04:54:01.759673", "ctime": "2021-08-29T04:39:16.261231", "mtime": "2017-05-31T06:32:41", "owner": ",,,", "value": 0.28799999}, "aerosol": {"url": "file:///ancillary/aerosol/aerosol.h5", "atime": "2021-08-29T04:54:00.855697", "ctime": "2021-08-29T04:39:16.261231", "mtime": "2017-05-31T06:31:42", "owner": ",,,", "value": 0.047273789, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.0991644527323103 -26.1859845431012559, 132.1260722251955713 -27.1759001647638456, 131.0186884780452488 -27.1962280825252343, 131.0012926817762207 -26.2054590509477272))", "dataset_pathname": "/cmp/aot_mean_Aug_All_Aerosols"}, "elevation": {"url": "file:///ancillary/elevation/world_1deg/DEM_one_deg.tif", "atime": "2021-08-29T04:54:01.791672", "ctime": "2021-08-29T04:39:16.261231", "mtime": "2017-05-31T08:03:53", "owner": ",,,", "value": 0.722}, "water_vapour": {"url": "file:///ancillary/water_vapour/pr_wtr.eatm.2021.tif", "atime": "2021-08-29T04:54:01.435682", "ctime": "2021-08-29T04:40:26.745437", "mtime": "2021-08-29T03:20:34", "owner": ",,,", "value": 0.9500000000000001}, "brdf_geo_band_2": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b09.500m_0459_0479nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_2", "atime": "2021-08-29T04:59:19.643219", "ctime": "2021-08-29T04:40:16.629729", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.0023688357804021705, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}, "brdf_geo_band_3": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b12.500m_0545_0565nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_3", "atime": "2021-08-29T04:59:22.807135", "ctime": "2021-08-29T04:40:20.369617", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.008622999122247049, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}, "brdf_geo_band_4": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b03.500m_0620_0670nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_4", "atime": "2021-08-29T04:59:25.939052", "ctime": "2021-08-29T04:40:11.693878", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.02520520068624322, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}, "brdf_geo_band_8": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b06.500m_0841_0876nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_8", "atime": "2021-08-29T04:59:29.266963", "ctime": "2021-08-29T04:40:14.693788", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.02305952760932014, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}, "brdf_iso_band_2": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b07.500m_0459_0479nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_2", "atime": "2021-08-29T04:54:01.935668", "ctime": "2021-08-29T04:40:13.685818", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.05112053343440792, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}, "brdf_iso_band_3": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b10.500m_0545_0565nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_3", "atime": "2021-08-29T04:59:20.751189", "ctime": "2021-08-29T04:40:17.721697", "mtime": "2017-05-31T23:49:36", "owner": ",,,", "value": 0.08858365384615385, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}, "brdf_iso_band_4": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b01.500m_0620_0670nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_4", "atime": "2021-08-29T04:59:23.867107", "ctime": "2021-08-29T04:40:11.013898", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.17450199688796683, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}, "brdf_iso_band_8": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b04.500m_0841_0876nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_8", "atime": "2021-08-29T04:59:27.075022", "ctime": "2021-08-29T04:40:12.257861", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.24916000239387168, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}, "brdf_vol_band_2": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b08.500m_0459_0479nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_2", "atime": "2021-08-29T04:59:18.595247", "ctime": "2021-08-29T04:40:17.661698", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.030440219039259496, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}, "brdf_vol_band_3": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b11.500m_0545_0565nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_3", "atime": "2021-08-29T04:59:21.767163", "ctime": "2021-08-29T04:40:17.857692", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.0578930817108203, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}, "brdf_vol_band_4": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b02.500m_0620_0670nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_4", "atime": "2021-08-29T04:59:24.879080", "ctime": "2021-08-29T04:40:11.213892", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.05559107085860199, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}, "brdf_vol_band_8": {"url": "file:///ancillary/brdf-jl/241/MCD43A1.JLWKAV.241.aust.005.b05.500m_0841_0876nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_8", "atime": "2021-08-29T04:59:28.142993", "ctime": "2021-08-29T04:40:12.245861", "mtime": "2017-05-31T23:49:13", "owner": ",,,", "value": 0.1323908494254708, "extents": "POLYGON ((131.0012926817762207 -26.2054590509477272, 132.1260722251955713 -26.2054590509477272, 132.1260722251955713 -27.1759001647638456, 131.0012926817762207 -27.1759001647638456, 131.0012926817762207 -26.2054590509477272))"}}, "source_datasets": {}}, "tile_id": "S2A_OPER_MSI_L1C_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01", "platform": {"code": "SENTINEL_2A"}, "instrument": {"name": "MSI"}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[699960.0, 7033270.0], [700020.0, 7033240.0], [700138.2085500087, 7033345.4478624975], [701638.3929476233, 7039646.206390325], [713818.3971655389, 7091246.224258386], [715800.0, 7100020.0], [699960.0, 7100020.0], [699960.0, 7033270.0]]]}, "geo_ref_points": {"ll": {"x": 699960, "y": 6990220}, "lr": {"x": 809760, "y": 6990220}, "ul": {"x": 699960, "y": 7100020}, "ur": {"x": 809760, "y": 7100020}}, "spatial_reference": "PROJCS[\\"WGS 84 / UTM zone 52S\\",GEOGCS[\\"WGS 84\\",DATUM[\\"WGS_1984\\",SPHEROID[\\"WGS 84\\",6378137,298.257223563,AUTHORITY[\\"EPSG\\",\\"7030\\"]],AUTHORITY[\\"EPSG\\",\\"6326\\"]],PRIMEM[\\"Greenwich\\",0,AUTHORITY[\\"EPSG\\",\\"8901\\"]],UNIT[\\"degree\\",0.0174532925199433,AUTHORITY[\\"EPSG\\",\\"9122\\"]],AUTHORITY[\\"EPSG\\",\\"4326\\"]],PROJECTION[\\"Transverse_Mercator\\"],PARAMETER[\\"latitude_of_origin\\",0],PARAMETER[\\"central_meridian\\",129],PARAMETER[\\"scale_factor\\",0.9996],PARAMETER[\\"false_easting\\",500000],PARAMETER[\\"false_northing\\",10000000],UNIT[\\"metre\\",1,AUTHORITY[\\"EPSG\\",\\"9001\\"]],AXIS[\\"Easting\\",EAST],AXIS[\\"Northing\\",NORTH],AUTHORITY[\\"EPSG\\",\\"32752\\"]]"}}, "product_type": "ard", "processing_level": "Level-2", "software_versions": {"wagl": {"version": "5.0.5+33.g94f1105.dirty", "repo_url": "https://github.com/GeoscienceAustralia/wagl.git"}, "modtran": {"version": "5.2.1", "repo_url": "http://www.ontar.com/software/productdetails.aspx?item=modtran"}}, "system_information": {"uname": "Linux ip-10-0-10-174.ap-southeast-2.compute.internal 4.14.186-146.268.amzn2.x86_64 #1 SMP Tue Jul 14 18:16:52 UTC 2020 x86_64", "hostname": "ip-10-0-10-174.ap-southeast-2.compute.internal", "runtime_id": "484811aa-0890-11ec-a45c-062d6b9abbe2", "time_processed": "2021-08-29T06:13:52.263865"}, "algorithm_information": {"nbar_doi": "http://dx.doi.org/10.1109/JSTARS.2010.2042281", "arg25_doi": "http://dx.doi.org/10.4225/25/5487CC0D4F40B", "algorithm_version": 2.0, "nbar_terrain_corrected_doi": "http://dx.doi.org/10.1016/j.rse.2012.06.018"}}	\N	2021-08-29 23:02:42.664449+00	opendatacubeusername	\N
ffa8b91f-22a3-45b4-8439-c80fc4d83140	5	3	{"id": "ffa8b91f-22a3-45b4-8439-c80fc4d83140", "crs": "epsg:32653", "grids": {"default": {"shape": [6921, 8101], "transform": [30.0, 0.0, 154785.0, 0.0, -30.0, -2454585.0, 0.0, 0.0, 1.0]}, "panchromatic": {"shape": [13841, 16201], "transform": [15.0, 0.0, 154792.5, 0.0, -15.0, -2454592.5, 0.0, 0.0, 1.0]}}, "label": "ga_ls7e_ard_provisional_3-2-1_103076_2021-08-18_nrt", "extent": {"lat": {"end": -22.17200265045818, "begin": -24.061609994263712}, "lon": {"end": 133.99974889997355, "begin": 131.61582650066538}}, "$schema": "https://schemas.opendatacube.org/dataset", "lineage": {"source_datasets": {}}, "product": {"href": "https://collections.dea.ga.gov.au/product/ga_ls7e_ard_provisional_3", "name": "ga_ls7e_ard_provisional_3"}, "geometry": {"type": "Polygon", "coordinates": [[[155087.19313657994, -2633599.353858312], [155063.7867965644, -2633586.2132034358], [160575.58455239635, -2605839.1066611945], [173625.60010471215, -2540829.0295597264], [183525.60010471215, -2492079.0295597264], [190995.6190008234, -2455808.9372541383], [191003.38860279758, -2455802.467157996], [191198.08928725737, -2455128.3369052075], [191289.083592135, -2454945.7917960677], [191452.5, -2454907.5], [390564.6213203436, -2482177.650757595], [390767.65584796236, -2482211.4610348237], [390787.28116107563, -2482229.516322888], [393529.24264068715, -2482605.3015151904], [395960.8834840541, -2482965.582579729], [397084.96844540874, -2483962.611136966], [395954.4105274478, -2489750.9178438], [362174.4105274478, -2657630.9178438], [361370.8834840541, -2661464.417420271], [359890.98246311996, -2661734.7297729123], [160090.946603858, -2634704.7249050415], [156647.48959552628, -2634220.0903970804], [155175.7917960675, -2634020.916407865], [155087.19313657994, -2633599.353858312]]]}, "properties": {"eo:gsd": 15.0, "datetime": "2021-08-18 00:07:21.268815Z", "gqa:abs_x": "NaN", "gqa:abs_y": "NaN", "gqa:cep90": "NaN", "fmask:snow": 0.00008182077003228549, "gqa:abs_xy": "NaN", "gqa:mean_x": "NaN", "gqa:mean_y": "NaN", "eo:platform": "landsat-7", "fmask:clear": 99.50066747747776, "fmask:cloud": 0.3768730124303096, "fmask:water": 0.11604148889058857, "gqa:mean_xy": "NaN", "gqa:stddev_x": "NaN", "gqa:stddev_y": "NaN", "odc:producer": "ga.gov.au", "eo:instrument": "ETM", "gqa:stddev_xy": "NaN", "eo:cloud_cover": 0.3768730124303096, "eo:sun_azimuth": 56.15238434, "landsat:wrs_row": 76, "odc:file_format": "GeoTIFF", "odc:region_code": "103076", "dtr:end_datetime": "2021-08-18 00:07:34.831040Z", "eo:sun_elevation": 31.98188606, "landsat:wrs_path": 103, "dtr:start_datetime": "2021-08-18 00:07:07.641067Z", "fmask:cloud_shadow": 0.0063362004313001884, "odc:product_family": "ard", "odc:dataset_version": "3.2.1", "dea:dataset_maturity": "nrt", "dea:product_maturity": "provisional", "gqa:iterative_mean_x": "NaN", "gqa:iterative_mean_y": "NaN", "gqa:iterative_mean_xy": "NaN", "gqa:iterative_stddev_x": "NaN", "gqa:iterative_stddev_y": "NaN", "gqa:iterative_stddev_xy": "NaN", "odc:processing_datetime": "2021-08-18 19:24:39.526240Z", "gqa:abs_iterative_mean_x": "NaN", "gqa:abs_iterative_mean_y": "NaN", "landsat:landsat_scene_id": "LE71030762021230ASA00", "gqa:abs_iterative_mean_xy": "NaN", "landsat:collection_number": 2, "landsat:landsat_product_id": "LE07_L1TP_103076_20210818_20210818_02_RT", "landsat:collection_category": "RT"}, "accessories": {"checksum:sha1": {"path": "ga_ls7e_ard_provisional_3-2-1_103076_2021-08-18_nrt.sha1"}, "thumbnail:nbar": {"path": "ga_ls7e_nbar_provisional_3-2-1_103076_2021-08-18_nrt_thumbnail.jpg"}, "thumbnail:nbart": {"path": "ga_ls7e_nbart_provisional_3-2-1_103076_2021-08-18_nrt_thumbnail.jpg"}, "metadata:processor": {"path": "ga_ls7e_ard_provisional_3-2-1_103076_2021-08-18_nrt.proc-info.yaml"}}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[155087.19313657994, -2633599.353858312], [155063.7867965644, -2633586.2132034358], [160575.58455239635, -2605839.1066611945], [173625.60010471215, -2540829.0295597264], [183525.60010471215, -2492079.0295597264], [190995.6190008234, -2455808.9372541383], [191003.38860279758, -2455802.467157996], [191198.08928725737, -2455128.3369052075], [191289.083592135, -2454945.7917960677], [191452.5, -2454907.5], [390564.6213203436, -2482177.650757595], [390767.65584796236, -2482211.4610348237], [390787.28116107563, -2482229.516322888], [393529.24264068715, -2482605.3015151904], [395960.8834840541, -2482965.582579729], [397084.96844540874, -2483962.611136966], [395954.4105274478, -2489750.9178438], [362174.4105274478, -2657630.9178438], [361370.8834840541, -2661464.417420271], [359890.98246311996, -2661734.7297729123], [160090.946603858, -2634704.7249050415], [156647.48959552628, -2634220.0903970804], [155175.7917960675, -2634020.916407865], [155087.19313657994, -2633599.353858312]]]}, "geo_ref_points": {"ll": {"x": 154785.0, "y": -2662215.0}, "lr": {"x": 397815.0, "y": -2662215.0}, "ul": {"x": 154785.0, "y": -2454585.0}, "ur": {"x": 397815.0, "y": -2454585.0}}, "spatial_reference": "epsg:32653"}}, "measurements": {"nbar_nir": {"path": "ga_ls7e_nbar_provisional_3-2-1_103076_2021-08-18_nrt_band04.tif"}, "nbar_red": {"path": "ga_ls7e_nbar_provisional_3-2-1_103076_2021-08-18_nrt_band03.tif"}, "oa_fmask": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_fmask.tif"}, "nbar_blue": {"path": "ga_ls7e_nbar_provisional_3-2-1_103076_2021-08-18_nrt_band01.tif"}, "nbart_nir": {"path": "ga_ls7e_nbart_provisional_3-2-1_103076_2021-08-18_nrt_band04.tif"}, "nbart_red": {"path": "ga_ls7e_nbart_provisional_3-2-1_103076_2021-08-18_nrt_band03.tif"}, "nbar_green": {"path": "ga_ls7e_nbar_provisional_3-2-1_103076_2021-08-18_nrt_band02.tif"}, "nbart_blue": {"path": "ga_ls7e_nbart_provisional_3-2-1_103076_2021-08-18_nrt_band01.tif"}, "nbar_swir_1": {"path": "ga_ls7e_nbar_provisional_3-2-1_103076_2021-08-18_nrt_band05.tif"}, "nbar_swir_2": {"path": "ga_ls7e_nbar_provisional_3-2-1_103076_2021-08-18_nrt_band07.tif"}, "nbart_green": {"path": "ga_ls7e_nbart_provisional_3-2-1_103076_2021-08-18_nrt_band02.tif"}, "nbart_swir_1": {"path": "ga_ls7e_nbart_provisional_3-2-1_103076_2021-08-18_nrt_band05.tif"}, "nbart_swir_2": {"path": "ga_ls7e_nbart_provisional_3-2-1_103076_2021-08-18_nrt_band07.tif"}, "oa_time_delta": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_time-delta.tif"}, "oa_solar_zenith": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_solar-zenith.tif"}, "oa_exiting_angle": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_exiting-angle.tif"}, "oa_solar_azimuth": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_solar-azimuth.tif"}, "nbar_panchromatic": {"grid": "panchromatic", "path": "ga_ls7e_nbar_provisional_3-2-1_103076_2021-08-18_nrt_band08.tif"}, "oa_incident_angle": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_incident-angle.tif"}, "oa_relative_slope": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_relative-slope.tif"}, "oa_satellite_view": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_satellite-view.tif"}, "nbart_panchromatic": {"grid": "panchromatic", "path": "ga_ls7e_nbart_provisional_3-2-1_103076_2021-08-18_nrt_band08.tif"}, "oa_nbar_contiguity": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_nbar-contiguity.tif"}, "oa_nbart_contiguity": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_nbart-contiguity.tif"}, "oa_relative_azimuth": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_relative-azimuth.tif"}, "oa_azimuthal_exiting": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_azimuthal-exiting.tif"}, "oa_satellite_azimuth": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_satellite-azimuth.tif"}, "oa_azimuthal_incident": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_azimuthal-incident.tif"}, "oa_combined_terrain_shadow": {"path": "ga_ls7e_oa_provisional_3-2-1_103076_2021-08-18_nrt_combined-terrain-shadow.tif"}}}	\N	2021-08-29 23:02:56.893126+00	opendatacubeusername	\N
301c66d3-a49c-4937-8be0-3f96d01ecc38	5	4	{"id": "301c66d3-a49c-4937-8be0-3f96d01ecc38", "crs": "epsg:32652", "grids": {"default": {"shape": [7711, 7611], "transform": [30.0, 0.0, 233385.0, 0.0, -30.0, -1962585.0, 0.0, 0.0, 1.0]}, "panchromatic": {"shape": [15421, 15221], "transform": [15.0, 0.0, 233392.5, 0.0, -15.0, -1962592.5, 0.0, 0.0, 1.0]}}, "label": "ga_ls8c_ard_provisional_3-2-1_107073_2021-08-22_nrt", "extent": {"lat": {"end": -17.739437861293645, "begin": -19.838853864594537}, "lon": {"end": 128.6353289591475, "begin": 126.46396611911705}}, "$schema": "https://schemas.opendatacube.org/dataset", "lineage": {"source_datasets": {}}, "product": {"href": "https://collections.dea.ga.gov.au/product/ga_ls8c_ard_provisional_3", "name": "ga_ls8c_ard_provisional_3"}, "geometry": {"type": "Polygon", "coordinates": [[[274243.6302756969, -1962651.4240416484], [274245.0, -1962645.0], [461325.0, -2002035.0], [461323.5366984469, -2002041.9812588277], [461418.10660171777, -2002061.8933982821], [461392.1809780474, -2002285.57715511], [421233.10660171777, -2193813.106601718], [421144.55825797294, -2193817.2087101354], [421127.38642540755, -2193813.6146137086], [421125.0, -2193825.0], [233851.583592135, -2154461.83281573], [233852.5352858295, -2154445.376340814], [233767.5, -2154427.5], [238987.82019755096, -2129479.417241486], [256507.822507017, -2046124.406264437], [268732.8251716727, -1988224.3936494782], [274012.82728731405, -1963324.3836716418], [274177.5, -1962637.5], [274243.6302756969, -1962651.4240416484]]]}, "properties": {"eo:gsd": 15.0, "datetime": "2021-08-22 01:31:09.039337Z", "gqa:abs_x": "NaN", "gqa:abs_y": "NaN", "gqa:cep90": "NaN", "fmask:snow": 0.0, "gqa:abs_xy": "NaN", "gqa:mean_x": "NaN", "gqa:mean_y": "NaN", "eo:platform": "landsat-8", "fmask:clear": 99.98017042291667, "fmask:cloud": 0.0012691125714388253, "fmask:water": 0.017725845025840924, "gqa:mean_xy": "NaN", "gqa:stddev_x": "NaN", "gqa:stddev_y": "NaN", "odc:producer": "ga.gov.au", "eo:instrument": "OLI_TIRS", "gqa:stddev_xy": "NaN", "eo:cloud_cover": 0.0012691125714388253, "eo:sun_azimuth": 46.81969064, "landsat:wrs_row": 73, "odc:file_format": "GeoTIFF", "odc:region_code": "107073", "dtr:end_datetime": "2021-08-22 01:31:24.165068Z", "eo:sun_elevation": 47.21169755, "landsat:wrs_path": 107, "dtr:start_datetime": "2021-08-22 01:30:53.848465Z", "fmask:cloud_shadow": 0.0008346194860526124, "odc:product_family": "ard", "odc:dataset_version": "3.2.1", "dea:dataset_maturity": "nrt", "dea:product_maturity": "provisional", "gqa:iterative_mean_x": "NaN", "gqa:iterative_mean_y": "NaN", "gqa:iterative_mean_xy": "NaN", "gqa:iterative_stddev_x": "NaN", "gqa:iterative_stddev_y": "NaN", "gqa:iterative_stddev_xy": "NaN", "odc:processing_datetime": "2021-08-22 04:58:58.982968Z", "gqa:abs_iterative_mean_x": "NaN", "gqa:abs_iterative_mean_y": "NaN", "landsat:landsat_scene_id": "LC81070732021234LGN00", "gqa:abs_iterative_mean_xy": "NaN", "landsat:collection_number": 2, "landsat:landsat_product_id": "LC08_L1TP_107073_20210822_20210822_02_RT", "landsat:collection_category": "RT"}, "accessories": {"checksum:sha1": {"path": "ga_ls8c_ard_provisional_3-2-1_107073_2021-08-22_nrt.sha1"}, "thumbnail:nbar": {"path": "ga_ls8c_nbar_provisional_3-2-1_107073_2021-08-22_nrt_thumbnail.jpg"}, "thumbnail:nbart": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2021-08-22_nrt_thumbnail.jpg"}, "metadata:processor": {"path": "ga_ls8c_ard_provisional_3-2-1_107073_2021-08-22_nrt.proc-info.yaml"}}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[274243.6302756969, -1962651.4240416484], [274245.0, -1962645.0], [461325.0, -2002035.0], [461323.5366984469, -2002041.9812588277], [461418.10660171777, -2002061.8933982821], [461392.1809780474, -2002285.57715511], [421233.10660171777, -2193813.106601718], [421144.55825797294, -2193817.2087101354], [421127.38642540755, -2193813.6146137086], [421125.0, -2193825.0], [233851.583592135, -2154461.83281573], [233852.5352858295, -2154445.376340814], [233767.5, -2154427.5], [238987.82019755096, -2129479.417241486], [256507.822507017, -2046124.406264437], [268732.8251716727, -1988224.3936494782], [274012.82728731405, -1963324.3836716418], [274177.5, -1962637.5], [274243.6302756969, -1962651.4240416484]]]}, "geo_ref_points": {"ll": {"x": 233385.0, "y": -2193915.0}, "lr": {"x": 461715.0, "y": -2193915.0}, "ul": {"x": 233385.0, "y": -1962585.0}, "ur": {"x": 461715.0, "y": -1962585.0}}, "spatial_reference": "epsg:32652"}}, "measurements": {"nbar_nir": {"path": "ga_ls8c_nbar_provisional_3-2-1_107073_2021-08-22_nrt_band05.tif"}, "nbar_red": {"path": "ga_ls8c_nbar_provisional_3-2-1_107073_2021-08-22_nrt_band04.tif"}, "oa_fmask": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_fmask.tif"}, "nbar_blue": {"path": "ga_ls8c_nbar_provisional_3-2-1_107073_2021-08-22_nrt_band02.tif"}, "nbart_nir": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2021-08-22_nrt_band05.tif"}, "nbart_red": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2021-08-22_nrt_band04.tif"}, "nbar_green": {"path": "ga_ls8c_nbar_provisional_3-2-1_107073_2021-08-22_nrt_band03.tif"}, "nbart_blue": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2021-08-22_nrt_band02.tif"}, "nbar_swir_1": {"path": "ga_ls8c_nbar_provisional_3-2-1_107073_2021-08-22_nrt_band06.tif"}, "nbar_swir_2": {"path": "ga_ls8c_nbar_provisional_3-2-1_107073_2021-08-22_nrt_band07.tif"}, "nbart_green": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2021-08-22_nrt_band03.tif"}, "nbart_swir_1": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2021-08-22_nrt_band06.tif"}, "nbart_swir_2": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2021-08-22_nrt_band07.tif"}, "oa_time_delta": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_time-delta.tif"}, "oa_solar_zenith": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_solar-zenith.tif"}, "oa_exiting_angle": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_exiting-angle.tif"}, "oa_solar_azimuth": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_solar-azimuth.tif"}, "nbar_panchromatic": {"grid": "panchromatic", "path": "ga_ls8c_nbar_provisional_3-2-1_107073_2021-08-22_nrt_band08.tif"}, "oa_incident_angle": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_incident-angle.tif"}, "oa_relative_slope": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_relative-slope.tif"}, "oa_satellite_view": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_satellite-view.tif"}, "nbart_panchromatic": {"grid": "panchromatic", "path": "ga_ls8c_nbart_provisional_3-2-1_107073_2021-08-22_nrt_band08.tif"}, "oa_nbar_contiguity": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_nbar-contiguity.tif"}, "oa_nbart_contiguity": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_nbart-contiguity.tif"}, "oa_relative_azimuth": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_relative-azimuth.tif"}, "nbar_coastal_aerosol": {"path": "ga_ls8c_nbar_provisional_3-2-1_107073_2021-08-22_nrt_band01.tif"}, "oa_azimuthal_exiting": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_azimuthal-exiting.tif"}, "oa_satellite_azimuth": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_satellite-azimuth.tif"}, "nbart_coastal_aerosol": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2021-08-22_nrt_band01.tif"}, "oa_azimuthal_incident": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_azimuthal-incident.tif"}, "oa_combined_terrain_shadow": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2021-08-22_nrt_combined-terrain-shadow.tif"}}}	\N	2021-08-29 23:03:02.714775+00	opendatacubeusername	\N
828b51ac-6e76-4cb1-a95a-65d01dc6ef69	5	5	{"id": "828b51ac-6e76-4cb1-a95a-65d01dc6ef69", "crs": "epsg:32752", "grids": {"20": {"shape": [5490, 5490], "transform": [20.0, 0.0, 799980.0, 0.0, -20.0, 8600020.0, 0.0, 0.0, 1.0]}, "60": {"shape": [1830, 1830], "transform": [60.0, 0.0, 799980.0, 0.0, -60.0, 8600020.0, 0.0, 0.0, 1.0]}, "default": {"shape": [10980, 10980], "transform": [10.0, 0.0, 799980.0, 0.0, -10.0, 8600020.0, 0.0, 0.0, 1.0]}}, "label": "ga_s2am_ard_provisional_3-2-1_52LHL_2021-08-29_nrt", "extent": {"lat": {"end": -12.637300069246542, "begin": -13.641397347306768}, "lon": {"end": 132.78610048463833, "begin": 131.7614908089947}}, "$schema": "https://schemas.opendatacube.org/dataset", "lineage": {"source_datasets": {}}, "product": {"href": "https://collections.dea.ga.gov.au/product/ga_s2am_ard_provisional_3", "name": "ga_s2am_ard_provisional_3"}, "geometry": {"type": "Polygon", "coordinates": [[[799980.0, 8600020.0], [909780.0, 8600020.0], [909780.0, 8490220.0], [799980.0, 8490220.0], [799980.0, 8600020.0]]]}, "properties": {"eo:gsd": 10.0, "datetime": "2021-08-29 01:31:01.246989Z", "gqa:abs_x": "NaN", "gqa:abs_y": "NaN", "gqa:cep90": "NaN", "fmask:snow": 0.07106147623929583, "gqa:abs_xy": "NaN", "gqa:mean_x": "NaN", "gqa:mean_y": "NaN", "eo:platform": "sentinel-2a", "fmask:clear": 98.87364010072959, "fmask:cloud": 0.8212381511673817, "fmask:water": 0.0866951337255019, "gqa:mean_xy": "NaN", "gqa:stddev_x": "NaN", "gqa:stddev_y": "NaN", "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "gqa:stddev_xy": "NaN", "eo:cloud_cover": 0.8212381511673817, "eo:sun_azimuth": 49.3627516258236, "odc:file_format": "GeoTIFF", "odc:region_code": "52LHL", "eo:constellation": "sentinel-2", "eo:sun_elevation": 33.6443175558024, "sentinel:utm_zone": 52, "fmask:cloud_shadow": 0.1473651381382278, "odc:product_family": "ard", "odc:dataset_version": "3.2.1", "dea:dataset_maturity": "nrt", "dea:product_maturity": "provisional", "gqa:iterative_mean_x": "NaN", "gqa:iterative_mean_y": "NaN", "sentinel:grid_square": "HL", "gqa:iterative_mean_xy": "NaN", "sentinel:datastrip_id": "S2A_OPER_MSI_L1C_DS_VGS1_20210829T030536_S20210829T012718_N03.01", "gqa:iterative_stddev_x": "NaN", "gqa:iterative_stddev_y": "NaN", "sentinel:latitude_band": "L", "gqa:iterative_stddev_xy": "NaN", "odc:processing_datetime": "2021-08-29 08:26:20.045536Z", "gqa:abs_iterative_mean_x": "NaN", "gqa:abs_iterative_mean_y": "NaN", "gqa:abs_iterative_mean_xy": "NaN", "sentinel:sentinel_tile_id": "S2A_OPER_MSI_L1C_TL_VGS1_20210829T030536_A032303_T52LHL_N03.01", "sentinel:datatake_start_datetime": "2021-08-29 03:05:36Z"}, "accessories": {"checksum:sha1": {"path": "ga_s2am_ard_provisional_3-2-1_52LHL_2021-08-29_nrt.sha1"}, "thumbnail:nbart": {"path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_thumbnail.jpg"}, "metadata:processor": {"path": "ga_s2am_ard_provisional_3-2-1_52LHL_2021-08-29_nrt.proc-info.yaml"}}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[799980.0, 8600020.0], [909780.0, 8600020.0], [909780.0, 8490220.0], [799980.0, 8490220.0], [799980.0, 8600020.0]]]}, "geo_ref_points": {"ll": {"x": 799980.0, "y": 8490220.0}, "lr": {"x": 909780.0, "y": 8490220.0}, "ul": {"x": 799980.0, "y": 8600020.0}, "ur": {"x": 909780.0, "y": 8600020.0}}, "spatial_reference": "epsg:32752"}}, "measurements": {"oa_fmask": {"grid": "20", "path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_fmask.tif"}, "nbart_red": {"path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_band04.tif"}, "nbart_blue": {"path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_band02.tif"}, "nbart_green": {"path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_band03.tif"}, "nbart_nir_1": {"path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_band08.tif"}, "nbart_nir_2": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_band08a.tif"}, "nbart_swir_2": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_band11.tif"}, "nbart_swir_3": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_band12.tif"}, "oa_time_delta": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_time-delta.tif"}, "oa_solar_zenith": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_solar-zenith.tif"}, "nbart_red_edge_1": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_band05.tif"}, "nbart_red_edge_2": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_band06.tif"}, "nbart_red_edge_3": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_band07.tif"}, "oa_exiting_angle": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_exiting-angle.tif"}, "oa_solar_azimuth": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_solar-azimuth.tif"}, "oa_incident_angle": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_incident-angle.tif"}, "oa_relative_slope": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_relative-slope.tif"}, "oa_satellite_view": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_satellite-view.tif"}, "oa_nbart_contiguity": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_nbart-contiguity.tif"}, "oa_relative_azimuth": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_relative-azimuth.tif"}, "oa_azimuthal_exiting": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_azimuthal-exiting.tif"}, "oa_satellite_azimuth": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_satellite-azimuth.tif"}, "nbart_coastal_aerosol": {"grid": "60", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2021-08-29_nrt_band01.tif"}, "oa_azimuthal_incident": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_azimuthal-incident.tif"}, "oa_combined_terrain_shadow": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2021-08-29_nrt_combined-terrain-shadow.tif"}}}	\N	2021-08-29 23:09:18.929449+00	opendatacubeusername	\N
f1917c8f-8937-45e6-9202-f828a09b172c	5	6	{"id": "f1917c8f-8937-45e6-9202-f828a09b172c", "crs": "epsg:32755", "grids": {"20": {"shape": [5490, 5490], "transform": [20.0, 0.0, 399960.0, 0.0, -20.0, 8500000.0, 0.0, 0.0, 1.0]}, "60": {"shape": [1830, 1830], "transform": [60.0, 0.0, 399960.0, 0.0, -60.0, 8500000.0, 0.0, 0.0, 1.0]}, "default": {"shape": [10980, 10980], "transform": [10.0, 0.0, 399960.0, 0.0, -10.0, 8500000.0, 0.0, 0.0, 1.0]}}, "label": "ga_s2bm_ard_provisional_3-2-1_55LDE_2021-08-29_nrt", "extent": {"lat": {"end": -13.566738958793351, "begin": -14.560614866186768}, "lon": {"end": 146.67261261349867, "begin": 146.0713699237233}}, "$schema": "https://schemas.opendatacube.org/dataset", "lineage": {"source_datasets": {}}, "product": {"href": "https://collections.dea.ga.gov.au/product/ga_s2bm_ard_provisional_3", "name": "ga_s2bm_ard_provisional_3"}, "geometry": {"type": "Polygon", "coordinates": [[[464500.0, 8500000.0], [464580.0, 8500000.0], [464218.66814484465, 8498007.428254677], [442078.6448499264, 8395227.320032448], [440998.6305818354, 8390247.25422134], [440946.3641469882, 8390200.0], [440922.1661243539, 8390200.0], [440772.18018139247, 8390200.0], [399960.0, 8390200.0], [399960.0, 8500000.0], [464430.0, 8500000.0], [464500.0, 8500000.0]]]}, "properties": {"eo:gsd": 10.0, "datetime": "2021-08-29 00:40:45.064194Z", "gqa:abs_x": "NaN", "gqa:abs_y": "NaN", "gqa:cep90": "NaN", "fmask:snow": 0.005133749456492932, "gqa:abs_xy": "NaN", "gqa:mean_x": "NaN", "gqa:mean_y": "NaN", "eo:platform": "sentinel-2b", "fmask:clear": 0.023973706866518413, "fmask:cloud": 95.73379167967182, "fmask:water": 4.10925035656634, "gqa:mean_xy": "NaN", "gqa:stddev_x": "NaN", "gqa:stddev_y": "NaN", "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "gqa:stddev_xy": "NaN", "eo:cloud_cover": 95.73379167967182, "eo:sun_azimuth": 46.1603385068743, "odc:file_format": "GeoTIFF", "odc:region_code": "55LDE", "eo:constellation": "sentinel-2", "eo:sun_elevation": 33.0185676410833, "sentinel:utm_zone": 55, "fmask:cloud_shadow": 0.12785050743883075, "odc:product_family": "ard", "odc:dataset_version": "3.2.1", "dea:dataset_maturity": "nrt", "dea:product_maturity": "provisional", "gqa:iterative_mean_x": "NaN", "gqa:iterative_mean_y": "NaN", "sentinel:grid_square": "DE", "gqa:iterative_mean_xy": "NaN", "sentinel:datastrip_id": "S2B_OPER_MSI_L1C_DS_VGS4_20210829T015117_S20210829T003702_N03.01", "gqa:iterative_stddev_x": "NaN", "gqa:iterative_stddev_y": "NaN", "sentinel:latitude_band": "L", "gqa:iterative_stddev_xy": "NaN", "odc:processing_datetime": "2021-08-29 05:41:02.750914Z", "gqa:abs_iterative_mean_x": "NaN", "gqa:abs_iterative_mean_y": "NaN", "gqa:abs_iterative_mean_xy": "NaN", "sentinel:sentinel_tile_id": "S2B_OPER_MSI_L1C_TL_VGS4_20210829T015117_A023394_T55LDE_N03.01", "sentinel:datatake_start_datetime": "2021-08-29 01:51:17Z"}, "accessories": {"checksum:sha1": {"path": "ga_s2bm_ard_provisional_3-2-1_55LDE_2021-08-29_nrt.sha1"}, "thumbnail:nbart": {"path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_thumbnail.jpg"}, "metadata:processor": {"path": "ga_s2bm_ard_provisional_3-2-1_55LDE_2021-08-29_nrt.proc-info.yaml"}}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[464500.0, 8500000.0], [464580.0, 8500000.0], [464218.66814484465, 8498007.428254677], [442078.6448499264, 8395227.320032448], [440998.6305818354, 8390247.25422134], [440946.3641469882, 8390200.0], [440922.1661243539, 8390200.0], [440772.18018139247, 8390200.0], [399960.0, 8390200.0], [399960.0, 8500000.0], [464430.0, 8500000.0], [464500.0, 8500000.0]]]}, "geo_ref_points": {"ll": {"x": 399960.0, "y": 8390200.0}, "lr": {"x": 509760.0, "y": 8390200.0}, "ul": {"x": 399960.0, "y": 8500000.0}, "ur": {"x": 509760.0, "y": 8500000.0}}, "spatial_reference": "epsg:32755"}}, "measurements": {"oa_fmask": {"grid": "20", "path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_fmask.tif"}, "nbart_red": {"path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_band04.tif"}, "nbart_blue": {"path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_band02.tif"}, "nbart_green": {"path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_band03.tif"}, "nbart_nir_1": {"path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_band08.tif"}, "nbart_nir_2": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_band08a.tif"}, "nbart_swir_2": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_band11.tif"}, "nbart_swir_3": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_band12.tif"}, "oa_time_delta": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_time-delta.tif"}, "oa_solar_zenith": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_solar-zenith.tif"}, "nbart_red_edge_1": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_band05.tif"}, "nbart_red_edge_2": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_band06.tif"}, "nbart_red_edge_3": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_band07.tif"}, "oa_exiting_angle": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_exiting-angle.tif"}, "oa_solar_azimuth": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_solar-azimuth.tif"}, "oa_incident_angle": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_incident-angle.tif"}, "oa_relative_slope": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_relative-slope.tif"}, "oa_satellite_view": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_satellite-view.tif"}, "oa_nbart_contiguity": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_nbart-contiguity.tif"}, "oa_relative_azimuth": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_relative-azimuth.tif"}, "oa_azimuthal_exiting": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_azimuthal-exiting.tif"}, "oa_satellite_azimuth": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_satellite-azimuth.tif"}, "nbart_coastal_aerosol": {"grid": "60", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2021-08-29_nrt_band01.tif"}, "oa_azimuthal_incident": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_azimuthal-incident.tif"}, "oa_combined_terrain_shadow": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2021-08-29_nrt_combined-terrain-shadow.tif"}}}	\N	2021-08-29 23:09:22.23775+00	opendatacubeusername	\N
48103f0f-7d1f-4be8-b8ff-20e88cd5522d	4	2	{"id": "48103f0f-7d1f-4be8-b8ff-20e88cd5522d", "image": {"bands": {"fmask": {"path": "QA/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_FMASK.TIF", "layer": 1}, "exiting": {"path": "SUPPLEMENTARY/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_EXITING.TIF", "layer": 1}, "incident": {"path": "SUPPLEMENTARY/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_INCIDENT.TIF", "layer": 1}, "nbar_red": {"path": "NBAR/NBAR_B04.TIF", "layer": 1}, "nbar_blue": {"path": "NBAR/NBAR_B02.TIF", "layer": 1}, "nbart_red": {"path": "NBART/NBART_B04.TIF", "layer": 1}, "timedelta": {"path": "SUPPLEMENTARY/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_TIMEDELTA.TIF", "layer": 1}, "nbar_green": {"path": "NBAR/NBAR_B03.TIF", "layer": 1}, "nbar_nir_1": {"path": "NBAR/NBAR_B08.TIF", "layer": 1}, "nbar_nir_2": {"path": "NBAR/NBAR_B8A.TIF", "layer": 1}, "nbart_blue": {"path": "NBART/NBART_B02.TIF", "layer": 1}, "nbar_swir_2": {"path": "NBAR/NBAR_B11.TIF", "layer": 1}, "nbar_swir_3": {"path": "NBAR/NBAR_B12.TIF", "layer": 1}, "nbart_green": {"path": "NBART/NBART_B03.TIF", "layer": 1}, "nbart_nir_1": {"path": "NBART/NBART_B08.TIF", "layer": 1}, "nbart_nir_2": {"path": "NBART/NBART_B8A.TIF", "layer": 1}, "nbart_swir_2": {"path": "NBART/NBART_B11.TIF", "layer": 1}, "nbart_swir_3": {"path": "NBART/NBART_B12.TIF", "layer": 1}, "solar_zenith": {"path": "SUPPLEMENTARY/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_SOLAR_ZENITH.TIF", "layer": 1}, "solar_azimuth": {"path": "SUPPLEMENTARY/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_SOLAR_AZIMUTH.TIF", "layer": 1}, "lambertian_red": {"path": "LAMBERTIAN/LAMBERTIAN_B04.TIF", "layer": 1}, "relative_slope": {"path": "SUPPLEMENTARY/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_RELATIVE_SLOPE.TIF", "layer": 1}, "satellite_view": {"path": "SUPPLEMENTARY/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_SATELLITE_VIEW.TIF", "layer": 1}, "terrain_shadow": {"path": "QA/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_COMBINED_TERRAIN_SHADOW.TIF", "layer": 1}, "lambertian_blue": {"path": "LAMBERTIAN/LAMBERTIAN_B02.TIF", "layer": 1}, "nbar_contiguity": {"path": "QA/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_NBAR_CONTIGUITY.TIF", "layer": 1}, "nbar_red_edge_1": {"path": "NBAR/NBAR_B05.TIF", "layer": 1}, "nbar_red_edge_2": {"path": "NBAR/NBAR_B06.TIF", "layer": 1}, "nbar_red_edge_3": {"path": "NBAR/NBAR_B07.TIF", "layer": 1}, "lambertian_green": {"path": "LAMBERTIAN/LAMBERTIAN_B03.TIF", "layer": 1}, "lambertian_nir_1": {"path": "LAMBERTIAN/LAMBERTIAN_B08.TIF", "layer": 1}, "lambertian_nir_2": {"path": "LAMBERTIAN/LAMBERTIAN_B8A.TIF", "layer": 1}, "nbart_contiguity": {"path": "QA/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_NBART_CONTIGUITY.TIF", "layer": 1}, "nbart_red_edge_1": {"path": "NBART/NBART_B05.TIF", "layer": 1}, "nbart_red_edge_2": {"path": "NBART/NBART_B06.TIF", "layer": 1}, "nbart_red_edge_3": {"path": "NBART/NBART_B07.TIF", "layer": 1}, "relative_azimuth": {"path": "SUPPLEMENTARY/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_RELATIVE_AZIMUTH.TIF", "layer": 1}, "azimuthal_exiting": {"path": "SUPPLEMENTARY/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_AZIMUTHAL_EXITING.TIF", "layer": 1}, "lambertian_swir_2": {"path": "LAMBERTIAN/LAMBERTIAN_B11.TIF", "layer": 1}, "lambertian_swir_3": {"path": "LAMBERTIAN/LAMBERTIAN_B12.TIF", "layer": 1}, "satellite_azimuth": {"path": "SUPPLEMENTARY/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_SATELLITE_AZIMUTH.TIF", "layer": 1}, "azimuthal_incident": {"path": "SUPPLEMENTARY/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_AZIMUTHAL_INCIDENT.TIF", "layer": 1}, "nbar_coastal_aerosol": {"path": "NBAR/NBAR_B01.TIF", "layer": 1}, "lambertian_contiguity": {"path": "QA/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01_LAMBERTIAN_CONTIGUITY.TIF", "layer": 1}, "lambertian_red_edge_1": {"path": "LAMBERTIAN/LAMBERTIAN_B05.TIF", "layer": 1}, "lambertian_red_edge_2": {"path": "LAMBERTIAN/LAMBERTIAN_B06.TIF", "layer": 1}, "lambertian_red_edge_3": {"path": "LAMBERTIAN/LAMBERTIAN_B07.TIF", "layer": 1}, "nbart_coastal_aerosol": {"path": "NBART/NBART_B01.TIF", "layer": 1}, "lambertian_coastal_aerosol": {"path": "LAMBERTIAN/LAMBERTIAN_B01.TIF", "layer": 1}}}, "extent": {"coord": {"ll": {"lat": -24.472755339293354, "lon": 125.95937872772778}, "lr": {"lat": -24.447686475074978, "lon": 127.04075394649263}, "ul": {"lat": -23.482325981770927, "lon": 125.93681914885613}, "ur": {"lat": -23.458393265956225, "lon": 127.00999778236634}}, "center_dt": "2021-09-06T01:44:05.821265Z"}, "format": {"name": "GeoTiff"}, "lineage": {"ancillary": {"ozone": {"url": "file:///ancillary/ozone/sep.tif", "atime": "2021-09-06T05:27:43.777172", "ctime": "2021-09-06T05:04:10.225142", "mtime": "2017-05-31T06:32:42", "owner": ",,,", "value": 0.28999999}, "aerosol": {"url": "file:///ancillary/aerosol/aerosol.h5", "atime": "2021-09-06T05:27:41.969199", "ctime": "2021-09-06T05:04:10.225142", "mtime": "2017-05-31T06:31:42", "owner": ",,,", "value": 0.085704558, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0099977823663409 -23.4583932659562251, 127.0407539464926288 -24.4476864750749776, 125.9593787277277812 -24.4727553392933537, 125.9368191488561308 -23.4823259817709271))", "dataset_pathname": "/cmp/aot_mean_Sep_All_Aerosols"}, "elevation": {"url": "file:///ancillary/elevation/world_1deg/DEM_one_deg.tif", "atime": "2021-09-06T05:27:43.809171", "ctime": "2021-09-06T05:04:10.225142", "mtime": "2017-05-31T08:03:53", "owner": ",,,", "value": 0.385}, "water_vapour": {"url": "file:///ancillary/water_vapour/pr_wtr.eatm.2021.tif", "atime": "2021-09-06T05:27:43.537175", "ctime": "2021-09-06T05:05:20.613618", "mtime": "2021-09-06T03:53:01", "owner": ",,,", "value": 0.9800000190734863}, "brdf_geo_band_2": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b09.500m_0459_0479nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_2", "atime": "2021-09-06T05:27:45.821140", "ctime": "2021-09-06T05:05:09.873791", "mtime": "2017-05-31T23:49:36", "owner": ",,,", "value": 0.001154436810926444, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}, "brdf_geo_band_3": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b12.500m_0545_0565nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_3", "atime": "2021-09-06T05:27:48.757095", "ctime": "2021-09-06T05:05:14.485716", "mtime": "2017-05-31T23:50:03", "owner": ",,,", "value": 0.0073407335033733746, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}, "brdf_geo_band_4": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b03.500m_0620_0670nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_4", "atime": "2021-09-06T05:27:52.053044", "ctime": "2021-09-06T05:05:03.981886", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.030181808458120782, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}, "brdf_geo_band_8": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b06.500m_0841_0876nm_brdf_par_fgeo.hdf", "type": "brdf_geo_band_8", "atime": "2021-09-06T05:27:55.488991", "ctime": "2021-09-06T05:05:09.625795", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.026414602188579894, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}, "brdf_iso_band_2": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b07.500m_0459_0479nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_2", "atime": "2021-09-06T05:27:43.829171", "ctime": "2021-09-06T05:05:08.581812", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.05437458655586638, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}, "brdf_iso_band_3": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b10.500m_0545_0565nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_3", "atime": "2021-09-06T05:27:46.817125", "ctime": "2021-09-06T05:05:10.365783", "mtime": "2017-05-31T23:50:03", "owner": ",,,", "value": 0.09652240003291099, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}, "brdf_iso_band_4": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b01.500m_0620_0670nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_4", "atime": "2021-09-06T05:27:49.789079", "ctime": "2021-09-06T05:05:02.629908", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.195285766002962, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}, "brdf_iso_band_8": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b04.500m_0841_0876nm_brdf_par_fiso.hdf", "type": "brdf_iso_band_8", "atime": "2021-09-06T05:27:53.225026", "ctime": "2021-09-06T05:05:04.493878", "mtime": "2017-05-31T23:49:36", "owner": ",,,", "value": 0.275838372140859, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}, "brdf_vol_band_2": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b08.500m_0459_0479nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_2", "atime": "2021-09-06T05:27:44.825155", "ctime": "2021-09-06T05:05:09.037804", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.0357515982392628, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}, "brdf_vol_band_3": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b11.500m_0545_0565nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_3", "atime": "2021-09-06T05:27:47.785110", "ctime": "2021-09-06T05:05:13.597731", "mtime": "2017-05-31T23:50:03", "owner": ",,,", "value": 0.07358546157643574, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}, "brdf_vol_band_4": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b02.500m_0620_0670nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_4", "atime": "2021-09-06T05:27:50.901062", "ctime": "2021-09-06T05:05:03.909888", "mtime": "2017-05-31T23:49:37", "owner": ",,,", "value": 0.06102163485272338, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}, "brdf_vol_band_8": {"url": "file:///ancillary/brdf-jl/249/MCD43A1.JLWKAV.249.aust.005.b05.500m_0841_0876nm_brdf_par_fvol.hdf", "type": "brdf_vol_band_8", "atime": "2021-09-06T05:27:54.337009", "ctime": "2021-09-06T05:05:05.317865", "mtime": "2017-05-31T23:49:36", "owner": ",,,", "value": 0.14832378023695905, "extents": "POLYGON ((125.9368191488561308 -23.4823259817709271, 127.0407539464926288 -23.4823259817709271, 127.0407539464926288 -24.4476864750749776, 125.9368191488561308 -24.4476864750749776, 125.9368191488561308 -23.4823259817709271))"}}, "source_datasets": {}}, "tile_id": "S2B_OPER_MSI_L1C_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01", "platform": {"code": "SENTINEL_2B"}, "instrument": {"name": "MSI"}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[839800.776182381, 7400020.0], [839402.0093971741, 7398775.397726581], [810600.0, 7290220.0], [909780.0, 7290220.0], [909780.0, 7400020.0], [839800.776182381, 7400020.0]]]}, "geo_ref_points": {"ll": {"x": 799980, "y": 7290220}, "lr": {"x": 909780, "y": 7290220}, "ul": {"x": 799980, "y": 7400020}, "ur": {"x": 909780, "y": 7400020}}, "spatial_reference": "PROJCS[\\"WGS 84 / UTM zone 51S\\",GEOGCS[\\"WGS 84\\",DATUM[\\"WGS_1984\\",SPHEROID[\\"WGS 84\\",6378137,298.257223563,AUTHORITY[\\"EPSG\\",\\"7030\\"]],AUTHORITY[\\"EPSG\\",\\"6326\\"]],PRIMEM[\\"Greenwich\\",0,AUTHORITY[\\"EPSG\\",\\"8901\\"]],UNIT[\\"degree\\",0.0174532925199433,AUTHORITY[\\"EPSG\\",\\"9122\\"]],AUTHORITY[\\"EPSG\\",\\"4326\\"]],PROJECTION[\\"Transverse_Mercator\\"],PARAMETER[\\"latitude_of_origin\\",0],PARAMETER[\\"central_meridian\\",123],PARAMETER[\\"scale_factor\\",0.9996],PARAMETER[\\"false_easting\\",500000],PARAMETER[\\"false_northing\\",10000000],UNIT[\\"metre\\",1,AUTHORITY[\\"EPSG\\",\\"9001\\"]],AXIS[\\"Easting\\",EAST],AXIS[\\"Northing\\",NORTH],AUTHORITY[\\"EPSG\\",\\"32751\\"]]"}}, "product_type": "ard", "processing_level": "Level-2", "software_versions": {"wagl": {"version": "5.0.5+33.g94f1105.dirty", "repo_url": "https://github.com/GeoscienceAustralia/wagl.git"}, "modtran": {"version": "5.2.1", "repo_url": "http://www.ontar.com/software/productdetails.aspx?item=modtran"}}, "system_information": {"uname": "Linux ip-10-0-10-48.ap-southeast-2.compute.internal 4.14.186-146.268.amzn2.x86_64 #1 SMP Tue Jul 14 18:16:52 UTC 2020 x86_64", "hostname": "ip-10-0-10-48.ap-southeast-2.compute.internal", "runtime_id": "9de11964-0ed9-11ec-90dd-0646397c2b5e", "time_processed": "2021-09-06T06:13:56.111029"}, "algorithm_information": {"nbar_doi": "http://dx.doi.org/10.1109/JSTARS.2010.2042281", "arg25_doi": "http://dx.doi.org/10.4225/25/5487CC0D4F40B", "algorithm_version": 2.0, "nbar_terrain_corrected_doi": "http://dx.doi.org/10.1016/j.rse.2012.06.018"}}	\N	2021-09-06 22:15:28.974262+00	opendatacubeusername	\N
\.


--
-- Data for Name: dataset_location; Type: TABLE DATA; Schema: agdc; Owner: agdc_admin
--

COPY agdc.dataset_location (id, dataset_ref, uri_scheme, uri_body, added, added_by, archived) FROM stdin;
1	f0298262-f75f-46b0-ac96-2ee2cc54b887	https	//data.dea.ga.gov.au/WOfS/WOFLs/v2.1.5/combined/x_6/y_-29/2004/05/03/LS_WATER_3577_6_-29_20040503003241500000_v1526732475.yaml	2021-08-27 06:08:28.814926+00	opendatacubeusername	\N
2	830ca898-2874-45ae-afe5-575dbf52f1ec	https	//data.dea.ga.gov.au/fractional-cover/fc/v2.2.1/ls5/x_6/y_-29/2004/05/11/LS5_TM_FC_3577_6_-29_20040511002356.yaml	2021-08-27 06:08:31.252026+00	opendatacubeusername	\N
3	8f27ae72-ed82-461d-ac05-771f772a988e	https	//data.dea.ga.gov.au/fractional-cover/fc/v2.2.1/ls7/x_6/y_-29/2004/05/19/LS7_ETM_FC_3577_6_-29_20040519003242.yaml	2021-08-27 06:08:33.718978+00	opendatacubeusername	\N
4	345aff57-ae5b-4b41-bf6c-b5b2a327861a	https	//data.dea.ga.gov.au/fractional-cover/fc/v2.2.1/ls8/x_6/y_-29/2018/05/27/LS8_OLI_FC_3577_6_-29_20180527003612.yaml	2021-08-27 06:08:36.170463+00	opendatacubeusername	\N
5	e6e62140-b8d7-46cd-8530-ad9d682f82f5	https	//data.dea.ga.gov.au/L2/sentinel-2-nrt/S2MSIARD/2021-06-29/S2A_OPER_MSI_ARD_TL_VGS4_20210630T012010_A031444_T56JPP_N03.00/ARD-METADATA.yaml	2021-08-29 22:59:43.133788+00	opendatacubeusername	\N
6	6621a608-9c61-4c9b-aa5d-312f6a32866f	https	//data.dea.ga.gov.au/L2/sentinel-2-nrt/S2MSIARD/2021-08-28/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56KPA_N03.01/ARD-METADATA.yaml	2021-08-29 23:02:35.86439+00	opendatacubeusername	\N
7	ccf58424-a33f-4cb1-9841-a5f5cf652ea9	https	//data.dea.ga.gov.au/L2/sentinel-2-nrt/S2MSIARD/2021-08-28/S2A_OPER_MSI_ARD_TL_VGS4_20210829T011308_A032302_T56JNL_N03.01/ARD-METADATA.yaml	2021-08-29 23:02:39.495699+00	opendatacubeusername	\N
8	0cfbd2fc-a5db-4ae2-9ff1-e4266ad46a5f	https	//data.dea.ga.gov.au/L2/sentinel-2-nrt/S2MSIARD/2021-08-29/S2A_OPER_MSI_ARD_TL_VGS4_20210829T035557_A032303_T52JGR_N03.01/ARD-METADATA.yaml	2021-08-29 23:02:42.664449+00	opendatacubeusername	\N
9	ffa8b91f-22a3-45b4-8439-c80fc4d83140	https	//data.dea.ga.gov.au/baseline/ga_ls7e_ard_provisional_3/103/076/2021/08/18_nrt/ga_ls7e_ard_provisional_3-2-1_103076_2021-08-18_nrt.odc-metadata.yaml	2021-08-29 23:02:56.893126+00	opendatacubeusername	\N
10	301c66d3-a49c-4937-8be0-3f96d01ecc38	https	//data.dea.ga.gov.au/baseline/ga_ls8c_ard_provisional_3/107/073/2021/08/22_nrt/ga_ls8c_ard_provisional_3-2-1_107073_2021-08-22_nrt.odc-metadata.yaml	2021-08-29 23:03:02.714775+00	opendatacubeusername	\N
11	828b51ac-6e76-4cb1-a95a-65d01dc6ef69	https	//data.dea.ga.gov.au/baseline/ga_s2am_ard_provisional_3/52/LHL/2021/08/29_nrt/20210829T030536/ga_s2am_ard_provisional_3-2-1_52LHL_2021-08-29_nrt.odc-metadata.yaml	2021-08-29 23:09:18.929449+00	opendatacubeusername	\N
12	f1917c8f-8937-45e6-9202-f828a09b172c	https	//data.dea.ga.gov.au/baseline/ga_s2bm_ard_provisional_3/55/LDE/2021/08/29_nrt/20210829T015117/ga_s2bm_ard_provisional_3-2-1_55LDE_2021-08-29_nrt.odc-metadata.yaml	2021-08-29 23:09:22.23775+00	opendatacubeusername	\N
13	48103f0f-7d1f-4be8-b8ff-20e88cd5522d	https	//data.dea.ga.gov.au/L2/sentinel-2-nrt/S2MSIARD/2021-09-06/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01/ARD-METADATA.yaml	2021-09-06 22:15:28.974262+00	opendatacubeusername	\N
14	48103f0f-7d1f-4be8-b8ff-20e88cd5522d	s3	//dea-public-data/L2/sentinel-2-nrt/S2MSIARD/2021-09-06/S2B_OPER_MSI_ARD_TL_VGS1_20210906T031504_A023509_T51KZP_N03.01/ARD-METADATA.yaml	2021-09-06 22:19:46.033146+00	opendatacubeusername	\N
\.


--
-- Data for Name: dataset_source; Type: TABLE DATA; Schema: agdc; Owner: agdc_admin
--

COPY agdc.dataset_source (dataset_ref, classifier, source_dataset_ref) FROM stdin;
\.


--
-- Data for Name: dataset_type; Type: TABLE DATA; Schema: agdc; Owner: agdc_admin
--

COPY agdc.dataset_type (id, name, metadata, metadata_type_ref, definition, added, added_by, updated) FROM stdin;
1	s2a_nrt_granule	{"format": {"name": "GeoTiff"}, "platform": {"code": "SENTINEL_2A"}, "instrument": {"name": "MSI"}, "product_type": "ard", "processing_level": "Level-2"}	4	{"name": "s2a_nrt_granule", "metadata": {"format": {"name": "GeoTiff"}, "platform": {"code": "SENTINEL_2A"}, "instrument": {"name": "MSI"}, "product_type": "ard", "processing_level": "Level-2"}, "description": "Sentinel-2A MSI ARD NRT - NBAR NBART and Pixel Quality", "measurements": [{"name": "azimuthal_exiting", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["azimuthal_exiting"]}, {"name": "azimuthal_incident", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["azimuthal_incident"]}, {"name": "exiting", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["exiting"]}, {"name": "incident", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["incident"]}, {"name": "relative_azimuth", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["relative_azimuth"]}, {"name": "relative_slope", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["relative_slope"]}, {"name": "satellite_azimuth", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["satellite_azimuth"]}, {"name": "satellite_view", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["satellite_view"]}, {"name": "solar_azimuth", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["solar_azimuth"]}, {"name": "solar_zenith", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["solar_zenith"]}, {"name": "terrain_shadow", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["terrain_shadow"]}, {"name": "fmask", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["mask", "Fmask"], "flags_definition": {"fmask": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "nodata", "1": "valid", "2": "cloud", "3": "shadow", "4": "snow", "5": "water"}, "description": "Fmask"}}}, {"name": "nbar_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "flags_definition": {"contiguity": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "not_contiguous", "1": "contiguous"}, "description": "Pixel contiguity in band stack"}}}, {"name": "nbar_coastal_aerosol", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_01", "nbar_B01", "nbar_Band1"], "spectral_definition": {"response": [0.015297, 0.067133, 0.19593, 0.357242, 0.460571, 0.511598, 0.551051, 0.587385, 0.613478, 0.650014, 0.699199, 0.74543, 0.792047, 0.862824, 0.947307, 0.993878, 1.0, 0.990178, 0.972897, 0.957042, 0.956726, 0.922389, 0.723933, 0.388302, 0.14596, 0.051814, 0.017459, 0.000303], "wavelength": [430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457]}}, {"name": "nbar_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_02", "nbar_B02", "nbar_Band2"], "spectral_definition": {"response": [0.001206, 0.00204, 0.002623, 0.002738, 0.002746, 0.002076, 0.003246, 0.002224, 0.002789, 0.003127, 0.002377, 0.003776, 0.002856, 0.003063, 0.00607, 0.009028, 0.019547, 0.038955, 0.084088, 0.176255, 0.292197, 0.364612, 0.382418, 0.385789, 0.393447, 0.400158, 0.410291, 0.424686, 0.449286, 0.481594, 0.505323, 0.523406, 0.529543, 0.534688, 0.533786, 0.534656, 0.5381, 0.543691, 0.557717, 0.578585, 0.601967, 0.616037, 0.621092, 0.613597, 0.596062, 0.575863, 0.558063, 0.546131, 0.542099, 0.553602, 0.571684, 0.598269, 0.633236, 0.67337, 0.711752, 0.738396, 0.758249, 0.768325, 0.773367, 0.780468, 0.788363, 0.795449, 0.809151, 0.824011, 0.837709, 0.844983, 0.847328, 0.840111, 0.825797, 0.804778, 0.78694, 0.771578, 0.761923, 0.765487, 0.781682, 0.810031, 0.850586, 0.901671, 0.95467, 0.987257, 1.0, 0.986389, 0.908308, 0.724, 0.478913, 0.286992, 0.169976, 0.102833, 0.065163, 0.04116, 0.02508, 0.013112, 0.002585, 0.001095, 0.000308, 0.000441, 0.0, 0.0, 0.000443], "wavelength": [440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538]}}, {"name": "nbar_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_03", "nbar_B03", "nbar_Band3"], "spectral_definition": {"response": [0.00084, 0.016372, 0.037688, 0.080665, 0.169509, 0.341374, 0.573031, 0.746711, 0.828036, 0.868228, 0.888565, 0.891572, 0.87815, 0.860271, 0.843698, 0.834035, 0.832617, 0.844968, 0.867734, 0.897361, 0.933938, 0.966923, 0.990762, 1.0, 0.997812, 0.981107, 0.947088, 0.907183, 0.868656, 0.837622, 0.81291, 0.792434, 0.7851, 0.789606, 0.807011, 0.830458, 0.846433, 0.858402, 0.85799, 0.799824, 0.62498, 0.386994, 0.200179, 0.098293, 0.042844, 0.016512], "wavelength": [537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582]}}, {"name": "nbar_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_04", "nbar_B04", "nbar_Band4"], "spectral_definition": {"response": [0.002584, 0.034529, 0.14997, 0.464826, 0.817746, 0.965324, 0.983869, 0.9969, 1.0, 0.995449, 0.991334, 0.977215, 0.936802, 0.873776, 0.814166, 0.776669, 0.764864, 0.775091, 0.801359, 0.830828, 0.857112, 0.883581, 0.90895, 0.934759, 0.955931, 0.96811, 0.973219, 0.971572, 0.969003, 0.965712, 0.960481, 0.944811, 0.884152, 0.706167, 0.422967, 0.189853, 0.063172, 0.020615, 0.002034], "wavelength": [646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684]}}, {"name": "nbar_red_edge_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_05", "nbar_B05", "nbar_Band5"], "spectral_definition": {"response": [0.001187, 0.04126, 0.167712, 0.478496, 0.833878, 0.985479, 1.0, 0.999265, 0.993239, 0.982416, 0.965583, 0.945953, 0.924699, 0.902399, 0.885582, 0.861231, 0.757197, 0.521268, 0.196706, 0.036825], "wavelength": [694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713]}}, {"name": "nbar_red_edge_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_06", "nbar_B06", "nbar_Band6"], "spectral_definition": {"response": [0.005331, 0.085006, 0.345714, 0.750598, 0.920265, 0.917917, 0.934211, 0.957861, 0.975829, 0.981932, 0.981518, 0.993406, 1.0, 0.982579, 0.962584, 0.854908, 0.506722, 0.135357, 0.013438], "wavelength": [731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749]}}, {"name": "nbar_red_edge_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_07", "nbar_B07", "nbar_Band7"], "spectral_definition": {"response": [0.001595, 0.014731, 0.067032, 0.199495, 0.422803, 0.694015, 0.898494, 0.983173, 0.994759, 1.0, 0.994913, 0.964657, 0.908117, 0.846898, 0.802091, 0.778839, 0.777241, 0.789523, 0.800984, 0.802916, 0.791711, 0.757695, 0.677951, 0.536855, 0.364033, 0.193498, 0.077219, 0.019707, 0.003152], "wavelength": [769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797]}}, {"name": "nbar_nir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_08", "nbar_B08", "nbar_Band8"], "spectral_definition": {"response": [0.000451, 0.007614, 0.019072, 0.033498, 0.056536, 0.087148, 0.13246, 0.203436, 0.314068, 0.450085, 0.587433, 0.714518, 0.81829, 0.902932, 0.960732, 0.993723, 1.0, 0.985213, 0.958376, 0.93655, 0.925816, 0.930376, 0.941281, 0.953344, 0.962183, 0.965631, 0.963105, 0.959009, 0.951205, 0.945147, 0.943136, 0.945814, 0.945357, 0.943762, 0.937084, 0.92789, 0.915897, 0.900979, 0.881577, 0.86216, 0.8432, 0.822684, 0.801819, 0.776911, 0.755632, 0.737893, 0.722217, 0.708669, 0.698416, 0.690211, 0.682257, 0.681494, 0.682649, 0.678491, 0.67595, 0.671304, 0.665538, 0.660812, 0.658739, 0.65831, 0.66407, 0.672731, 0.685501, 0.701159, 0.720686, 0.742292, 0.75953, 0.776608, 0.784061, 0.78772, 0.787693, 0.783525, 0.776161, 0.768339, 0.759264, 0.745943, 0.733022, 0.720589, 0.706663, 0.69087, 0.675896, 0.661558, 0.649339, 0.638008, 0.627424, 0.618963, 0.610945, 0.604322, 0.597408, 0.591724, 0.586961, 0.582746, 0.581202, 0.57948, 0.580197, 0.582505, 0.585308, 0.589481, 0.592827, 0.596749, 0.601372, 0.603234, 0.605476, 0.608972, 0.613463, 0.618715, 0.626841, 0.637436, 0.648791, 0.659233, 0.66734, 0.668624, 0.659924, 0.641666, 0.615841, 0.583567, 0.552076, 0.526407, 0.507116, 0.49653, 0.499119, 0.512088, 0.529093, 0.542739, 0.537964, 0.495953, 0.419305, 0.326791, 0.231085, 0.14854, 0.089683, 0.054977, 0.033246, 0.019774, 0.007848, 0.001286], "wavelength": [773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885, 886, 887, 888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 907, 908]}}, {"name": "nbar_nir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_8A", "nbar_B8A", "nbar_Band8A"], "spectral_definition": {"response": [0.001651, 0.013242, 0.02471, 0.051379, 0.104944, 0.216577, 0.384865, 0.585731, 0.774481, 0.87843, 0.914944, 0.922574, 0.926043, 0.929676, 0.935962, 0.946583, 0.955792, 0.965458, 0.974461, 0.97988, 0.983325, 0.982881, 0.988474, 1.0, 0.999626, 0.921005, 0.728632, 0.472189, 0.238082, 0.106955, 0.046096, 0.022226, 0.008819, 0.000455], "wavelength": [848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881]}}, {"name": "nbar_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_11", "nbar_B11", "nbar_Band11"], "spectral_definition": {"response": [0.000007, 0.000007, 0.000008, 0.000028, 0.000038, 0.000091, 0.000147, 0.000251, 0.00048, 0.00057, 0.000662, 0.000911, 0.001166, 0.001684, 0.002458, 0.003567, 0.005345, 0.008318, 0.012628, 0.018996, 0.027781, 0.039584, 0.054865, 0.07493, 0.10107, 0.135476, 0.182597, 0.247276, 0.330736, 0.429691, 0.537634, 0.647173, 0.743528, 0.815215, 0.859202, 0.879669, 0.88703, 0.889098, 0.891417, 0.897586, 0.906631, 0.916528, 0.926579, 0.935322, 0.942394, 0.947507, 0.951416, 0.954254, 0.956429, 0.958205, 0.960688, 0.96348, 0.965797, 0.96818, 0.971012, 0.97338, 0.975915, 0.978581, 0.979878, 0.980589, 0.980912, 0.981412, 0.981244, 0.980705, 0.980377, 0.981066, 0.982736, 0.985122, 0.987807, 0.990376, 0.992016, 0.993288, 0.992536, 0.990405, 0.987128, 0.983502, 0.980023, 0.976174, 0.972568, 0.969828, 0.967709, 0.966371, 0.965849, 0.96605, 0.967427, 0.96987, 0.973463, 0.978683, 0.983472, 0.987635, 0.991875, 0.995476, 0.997586, 0.998568, 0.999328, 0.999234, 0.998804, 0.999111, 0.99973, 0.999745, 1.0, 0.999814, 0.996693, 0.99162, 0.985702, 0.978569, 0.969903, 0.960896, 0.953287, 0.946546, 0.941712, 0.938586, 0.935489, 0.928114, 0.912102, 0.880598, 0.82498, 0.743118, 0.641891, 0.534002, 0.426963, 0.32371, 0.234284, 0.163972, 0.110211, 0.072478, 0.046194, 0.029401, 0.019359, 0.013308, 0.009317, 0.006523, 0.004864, 0.003409, 0.002491, 0.001958, 0.001423, 0.001055, 0.000498, 0.000228, 0.000159, 0.000034, 0.000045, 0.000013], "wavelength": [1539, 1540, 1541, 1542, 1543, 1544, 1545, 1546, 1547, 1548, 1549, 1550, 1551, 1552, 1553, 1554, 1555, 1556, 1557, 1558, 1559, 1560, 1561, 1562, 1563, 1564, 1565, 1566, 1567, 1568, 1569, 1570, 1571, 1572, 1573, 1574, 1575, 1576, 1577, 1578, 1579, 1580, 1581, 1582, 1583, 1584, 1585, 1586, 1587, 1588, 1589, 1590, 1591, 1592, 1593, 1594, 1595, 1596, 1597, 1598, 1599, 1600, 1601, 1602, 1603, 1604, 1605, 1606, 1607, 1608, 1609, 1610, 1611, 1612, 1613, 1614, 1615, 1616, 1617, 1618, 1619, 1620, 1621, 1622, 1623, 1624, 1625, 1626, 1627, 1628, 1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636, 1637, 1638, 1639, 1640, 1641, 1642, 1643, 1644, 1645, 1646, 1647, 1648, 1649, 1650, 1651, 1652, 1653, 1654, 1655, 1656, 1657, 1658, 1659, 1660, 1661, 1662, 1663, 1664, 1665, 1666, 1667, 1668, 1669, 1670, 1671, 1672, 1673, 1674, 1675, 1676, 1677, 1678, 1679, 1680, 1681, 1682]}}, {"name": "nbar_swir_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_12", "nbar_B12", "nbar_Band12"], "spectral_definition": {"response": [0.000639, 0.001023, 0.002885, 0.003997, 0.006597, 0.00766, 0.008004, 0.00854, 0.0093, 0.010002, 0.010972, 0.012089, 0.013364, 0.015017, 0.017126, 0.01978, 0.023336, 0.027668, 0.033216, 0.040217, 0.048883, 0.059642, 0.073175, 0.090535, 0.11147, 0.136903, 0.167811, 0.203461, 0.242871, 0.284898, 0.327178, 0.368404, 0.408003, 0.444778, 0.476537, 0.503107, 0.525318, 0.543352, 0.557253, 0.568634, 0.57903, 0.588684, 0.598891, 0.609981, 0.621362, 0.634283, 0.648546, 0.663707, 0.680046, 0.696165, 0.711964, 0.727011, 0.741301, 0.757405, 0.772071, 0.785581, 0.798238, 0.809677, 0.819702, 0.828599, 0.836722, 0.844443, 0.851107, 0.853252, 0.854746, 0.856174, 0.857821, 0.859532, 0.86146, 0.863257, 0.865139, 0.867319, 0.869696, 0.874302, 0.878588, 0.882439, 0.885929, 0.889473, 0.893226, 0.896696, 0.899897, 0.902596, 0.904831, 0.905525, 0.905665, 0.905503, 0.905158, 0.904783, 0.904082, 0.903347, 0.902761, 0.902377, 0.901983, 0.903424, 0.904313, 0.905315, 0.906446, 0.908092, 0.910123, 0.91295, 0.915585, 0.918444, 0.921302, 0.924337, 0.927219, 0.92974, 0.931922, 0.934142, 0.935906, 0.937086, 0.937641, 0.938301, 0.937652, 0.940441, 0.942518, 0.943259, 0.943031, 0.942117, 0.940632, 0.938428, 0.93666, 0.935256, 0.933022, 0.92688, 0.921057, 0.915483, 0.91102, 0.908293, 0.907283, 0.908191, 0.911169, 0.916189, 0.922855, 0.920605, 0.919482, 0.919489, 0.921276, 0.924526, 0.927733, 0.931974, 0.93677, 0.941483, 0.946802, 0.951203, 0.954437, 0.957047, 0.959729, 0.962539, 0.964858, 0.966042, 0.966647, 0.96631, 0.96546, 0.964841, 0.963656, 0.961698, 0.959454, 0.957327, 0.95514, 0.953558, 0.952732, 0.952181, 0.951731, 0.952146, 0.952641, 0.954057, 0.957078, 0.960639, 0.964222, 0.968307, 0.972691, 0.977423, 0.982898, 0.987144, 0.990734, 0.993983, 0.996787, 0.998753, 1.0, 0.999927, 0.999152, 0.997129, 0.993884, 0.989686, 0.983735, 0.976213, 0.967813, 0.958343, 0.94844, 0.938203, 0.927725, 0.917039, 0.905999, 0.893868, 0.881683, 0.868647, 0.854635, 0.84062, 0.826016, 0.809516, 0.791867, 0.772443, 0.749107, 0.720346, 0.688185, 0.651283, 0.61005, 0.566031, 0.52097, 0.474659, 0.429259, 0.385857, 0.342092, 0.30068, 0.263176, 0.227704, 0.195721, 0.16809, 0.14468, 0.124831, 0.108237, 0.094401, 0.082363, 0.0715, 0.062691, 0.054985, 0.048195, 0.042864, 0.038598, 0.034947, 0.031999, 0.029588, 0.027418, 0.025577, 0.023959, 0.021672, 0.019148, 0.016331, 0.010989, 0.007379, 0.006511, 0.00471, 0.002065], "wavelength": [2078, 2079, 2080, 2081, 2082, 2083, 2084, 2085, 2086, 2087, 2088, 2089, 2090, 2091, 2092, 2093, 2094, 2095, 2096, 2097, 2098, 2099, 2100, 2101, 2102, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2111, 2112, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2121, 2122, 2123, 2124, 2125, 2126, 2127, 2128, 2129, 2130, 2131, 2132, 2133, 2134, 2135, 2136, 2137, 2138, 2139, 2140, 2141, 2142, 2143, 2144, 2145, 2146, 2147, 2148, 2149, 2150, 2151, 2152, 2153, 2154, 2155, 2156, 2157, 2158, 2159, 2160, 2161, 2162, 2163, 2164, 2165, 2166, 2167, 2168, 2169, 2170, 2171, 2172, 2173, 2174, 2175, 2176, 2177, 2178, 2179, 2180, 2181, 2182, 2183, 2184, 2185, 2186, 2187, 2188, 2189, 2190, 2191, 2192, 2193, 2194, 2195, 2196, 2197, 2198, 2199, 2200, 2201, 2202, 2203, 2204, 2205, 2206, 2207, 2208, 2209, 2210, 2211, 2212, 2213, 2214, 2215, 2216, 2217, 2218, 2219, 2220, 2221, 2222, 2223, 2224, 2225, 2226, 2227, 2228, 2229, 2230, 2231, 2232, 2233, 2234, 2235, 2236, 2237, 2238, 2239, 2240, 2241, 2242, 2243, 2244, 2245, 2246, 2247, 2248, 2249, 2250, 2251, 2252, 2253, 2254, 2255, 2256, 2257, 2258, 2259, 2260, 2261, 2262, 2263, 2264, 2265, 2266, 2267, 2268, 2269, 2270, 2271, 2272, 2273, 2274, 2275, 2276, 2277, 2278, 2279, 2280, 2281, 2282, 2283, 2284, 2285, 2286, 2287, 2288, 2289, 2290, 2291, 2292, 2293, 2294, 2295, 2296, 2297, 2298, 2299, 2300, 2301, 2302, 2303, 2304, 2305, 2306, 2307, 2308, 2309, 2310, 2311, 2312, 2313, 2314, 2315, 2316, 2317, 2318, 2319, 2320]}}, {"name": "nbart_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "flags_definition": {"contiguity": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "not_contiguous", "1": "contiguous"}, "description": "Pixel contiguity in band stack"}}}, {"name": "nbart_coastal_aerosol", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_01", "nbart_B01", "nbart_Band1"], "spectral_definition": {"response": [0.015297, 0.067133, 0.19593, 0.357242, 0.460571, 0.511598, 0.551051, 0.587385, 0.613478, 0.650014, 0.699199, 0.74543, 0.792047, 0.862824, 0.947307, 0.993878, 1.0, 0.990178, 0.972897, 0.957042, 0.956726, 0.922389, 0.723933, 0.388302, 0.14596, 0.051814, 0.017459, 0.000303], "wavelength": [430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457]}}, {"name": "nbart_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_02", "nbart_B02", "nbart_Band2"], "spectral_definition": {"response": [0.001206, 0.00204, 0.002623, 0.002738, 0.002746, 0.002076, 0.003246, 0.002224, 0.002789, 0.003127, 0.002377, 0.003776, 0.002856, 0.003063, 0.00607, 0.009028, 0.019547, 0.038955, 0.084088, 0.176255, 0.292197, 0.364612, 0.382418, 0.385789, 0.393447, 0.400158, 0.410291, 0.424686, 0.449286, 0.481594, 0.505323, 0.523406, 0.529543, 0.534688, 0.533786, 0.534656, 0.5381, 0.543691, 0.557717, 0.578585, 0.601967, 0.616037, 0.621092, 0.613597, 0.596062, 0.575863, 0.558063, 0.546131, 0.542099, 0.553602, 0.571684, 0.598269, 0.633236, 0.67337, 0.711752, 0.738396, 0.758249, 0.768325, 0.773367, 0.780468, 0.788363, 0.795449, 0.809151, 0.824011, 0.837709, 0.844983, 0.847328, 0.840111, 0.825797, 0.804778, 0.78694, 0.771578, 0.761923, 0.765487, 0.781682, 0.810031, 0.850586, 0.901671, 0.95467, 0.987257, 1.0, 0.986389, 0.908308, 0.724, 0.478913, 0.286992, 0.169976, 0.102833, 0.065163, 0.04116, 0.02508, 0.013112, 0.002585, 0.001095, 0.000308, 0.000441, 0.0, 0.0, 0.000443], "wavelength": [440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538]}}, {"name": "nbart_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_03", "nbart_B03", "nbart_Band3"], "spectral_definition": {"response": [0.00084, 0.016372, 0.037688, 0.080665, 0.169509, 0.341374, 0.573031, 0.746711, 0.828036, 0.868228, 0.888565, 0.891572, 0.87815, 0.860271, 0.843698, 0.834035, 0.832617, 0.844968, 0.867734, 0.897361, 0.933938, 0.966923, 0.990762, 1.0, 0.997812, 0.981107, 0.947088, 0.907183, 0.868656, 0.837622, 0.81291, 0.792434, 0.7851, 0.789606, 0.807011, 0.830458, 0.846433, 0.858402, 0.85799, 0.799824, 0.62498, 0.386994, 0.200179, 0.098293, 0.042844, 0.016512], "wavelength": [537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582]}}, {"name": "nbart_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_04", "nbart_B04", "nbart_Band4"], "spectral_definition": {"response": [0.002584, 0.034529, 0.14997, 0.464826, 0.817746, 0.965324, 0.983869, 0.9969, 1.0, 0.995449, 0.991334, 0.977215, 0.936802, 0.873776, 0.814166, 0.776669, 0.764864, 0.775091, 0.801359, 0.830828, 0.857112, 0.883581, 0.90895, 0.934759, 0.955931, 0.96811, 0.973219, 0.971572, 0.969003, 0.965712, 0.960481, 0.944811, 0.884152, 0.706167, 0.422967, 0.189853, 0.063172, 0.020615, 0.002034], "wavelength": [646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684]}}, {"name": "nbart_red_edge_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_05", "nbart_B05", "nbart_Band5"], "spectral_definition": {"response": [0.001187, 0.04126, 0.167712, 0.478496, 0.833878, 0.985479, 1.0, 0.999265, 0.993239, 0.982416, 0.965583, 0.945953, 0.924699, 0.902399, 0.885582, 0.861231, 0.757197, 0.521268, 0.196706, 0.036825], "wavelength": [694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713]}}, {"name": "nbart_red_edge_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_06", "nbart_B06", "nbart_Band6"], "spectral_definition": {"response": [0.005331, 0.085006, 0.345714, 0.750598, 0.920265, 0.917917, 0.934211, 0.957861, 0.975829, 0.981932, 0.981518, 0.993406, 1.0, 0.982579, 0.962584, 0.854908, 0.506722, 0.135357, 0.013438], "wavelength": [731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749]}}, {"name": "nbart_red_edge_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_07", "nbart_B07", "nbart_Band7"], "spectral_definition": {"response": [0.001595, 0.014731, 0.067032, 0.199495, 0.422803, 0.694015, 0.898494, 0.983173, 0.994759, 1.0, 0.994913, 0.964657, 0.908117, 0.846898, 0.802091, 0.778839, 0.777241, 0.789523, 0.800984, 0.802916, 0.791711, 0.757695, 0.677951, 0.536855, 0.364033, 0.193498, 0.077219, 0.019707, 0.003152], "wavelength": [769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797]}}, {"name": "nbart_nir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_08", "nbart_B08", "nbart_Band8"], "spectral_definition": {"response": [0.000451, 0.007614, 0.019072, 0.033498, 0.056536, 0.087148, 0.13246, 0.203436, 0.314068, 0.450085, 0.587433, 0.714518, 0.81829, 0.902932, 0.960732, 0.993723, 1.0, 0.985213, 0.958376, 0.93655, 0.925816, 0.930376, 0.941281, 0.953344, 0.962183, 0.965631, 0.963105, 0.959009, 0.951205, 0.945147, 0.943136, 0.945814, 0.945357, 0.943762, 0.937084, 0.92789, 0.915897, 0.900979, 0.881577, 0.86216, 0.8432, 0.822684, 0.801819, 0.776911, 0.755632, 0.737893, 0.722217, 0.708669, 0.698416, 0.690211, 0.682257, 0.681494, 0.682649, 0.678491, 0.67595, 0.671304, 0.665538, 0.660812, 0.658739, 0.65831, 0.66407, 0.672731, 0.685501, 0.701159, 0.720686, 0.742292, 0.75953, 0.776608, 0.784061, 0.78772, 0.787693, 0.783525, 0.776161, 0.768339, 0.759264, 0.745943, 0.733022, 0.720589, 0.706663, 0.69087, 0.675896, 0.661558, 0.649339, 0.638008, 0.627424, 0.618963, 0.610945, 0.604322, 0.597408, 0.591724, 0.586961, 0.582746, 0.581202, 0.57948, 0.580197, 0.582505, 0.585308, 0.589481, 0.592827, 0.596749, 0.601372, 0.603234, 0.605476, 0.608972, 0.613463, 0.618715, 0.626841, 0.637436, 0.648791, 0.659233, 0.66734, 0.668624, 0.659924, 0.641666, 0.615841, 0.583567, 0.552076, 0.526407, 0.507116, 0.49653, 0.499119, 0.512088, 0.529093, 0.542739, 0.537964, 0.495953, 0.419305, 0.326791, 0.231085, 0.14854, 0.089683, 0.054977, 0.033246, 0.019774, 0.007848, 0.001286], "wavelength": [773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885, 886, 887, 888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 907, 908]}}, {"name": "nbart_nir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_8A", "nbart_B8A", "nbart_Band8A"], "spectral_definition": {"response": [0.001651, 0.013242, 0.02471, 0.051379, 0.104944, 0.216577, 0.384865, 0.585731, 0.774481, 0.87843, 0.914944, 0.922574, 0.926043, 0.929676, 0.935962, 0.946583, 0.955792, 0.965458, 0.974461, 0.97988, 0.983325, 0.982881, 0.988474, 1.0, 0.999626, 0.921005, 0.728632, 0.472189, 0.238082, 0.106955, 0.046096, 0.022226, 0.008819, 0.000455], "wavelength": [848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881]}}, {"name": "nbart_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_11", "nbart_B11", "nbart_Band11"], "spectral_definition": {"response": [0.000007, 0.000007, 0.000008, 0.000028, 0.000038, 0.000091, 0.000147, 0.000251, 0.00048, 0.00057, 0.000662, 0.000911, 0.001166, 0.001684, 0.002458, 0.003567, 0.005345, 0.008318, 0.012628, 0.018996, 0.027781, 0.039584, 0.054865, 0.07493, 0.10107, 0.135476, 0.182597, 0.247276, 0.330736, 0.429691, 0.537634, 0.647173, 0.743528, 0.815215, 0.859202, 0.879669, 0.88703, 0.889098, 0.891417, 0.897586, 0.906631, 0.916528, 0.926579, 0.935322, 0.942394, 0.947507, 0.951416, 0.954254, 0.956429, 0.958205, 0.960688, 0.96348, 0.965797, 0.96818, 0.971012, 0.97338, 0.975915, 0.978581, 0.979878, 0.980589, 0.980912, 0.981412, 0.981244, 0.980705, 0.980377, 0.981066, 0.982736, 0.985122, 0.987807, 0.990376, 0.992016, 0.993288, 0.992536, 0.990405, 0.987128, 0.983502, 0.980023, 0.976174, 0.972568, 0.969828, 0.967709, 0.966371, 0.965849, 0.96605, 0.967427, 0.96987, 0.973463, 0.978683, 0.983472, 0.987635, 0.991875, 0.995476, 0.997586, 0.998568, 0.999328, 0.999234, 0.998804, 0.999111, 0.99973, 0.999745, 1.0, 0.999814, 0.996693, 0.99162, 0.985702, 0.978569, 0.969903, 0.960896, 0.953287, 0.946546, 0.941712, 0.938586, 0.935489, 0.928114, 0.912102, 0.880598, 0.82498, 0.743118, 0.641891, 0.534002, 0.426963, 0.32371, 0.234284, 0.163972, 0.110211, 0.072478, 0.046194, 0.029401, 0.019359, 0.013308, 0.009317, 0.006523, 0.004864, 0.003409, 0.002491, 0.001958, 0.001423, 0.001055, 0.000498, 0.000228, 0.000159, 0.000034, 0.000045, 0.000013], "wavelength": [1539, 1540, 1541, 1542, 1543, 1544, 1545, 1546, 1547, 1548, 1549, 1550, 1551, 1552, 1553, 1554, 1555, 1556, 1557, 1558, 1559, 1560, 1561, 1562, 1563, 1564, 1565, 1566, 1567, 1568, 1569, 1570, 1571, 1572, 1573, 1574, 1575, 1576, 1577, 1578, 1579, 1580, 1581, 1582, 1583, 1584, 1585, 1586, 1587, 1588, 1589, 1590, 1591, 1592, 1593, 1594, 1595, 1596, 1597, 1598, 1599, 1600, 1601, 1602, 1603, 1604, 1605, 1606, 1607, 1608, 1609, 1610, 1611, 1612, 1613, 1614, 1615, 1616, 1617, 1618, 1619, 1620, 1621, 1622, 1623, 1624, 1625, 1626, 1627, 1628, 1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636, 1637, 1638, 1639, 1640, 1641, 1642, 1643, 1644, 1645, 1646, 1647, 1648, 1649, 1650, 1651, 1652, 1653, 1654, 1655, 1656, 1657, 1658, 1659, 1660, 1661, 1662, 1663, 1664, 1665, 1666, 1667, 1668, 1669, 1670, 1671, 1672, 1673, 1674, 1675, 1676, 1677, 1678, 1679, 1680, 1681, 1682]}}, {"name": "nbart_swir_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_12", "nbart_B12", "nbart_Band12"], "spectral_definition": {"response": [0.000639, 0.001023, 0.002885, 0.003997, 0.006597, 0.00766, 0.008004, 0.00854, 0.0093, 0.010002, 0.010972, 0.012089, 0.013364, 0.015017, 0.017126, 0.01978, 0.023336, 0.027668, 0.033216, 0.040217, 0.048883, 0.059642, 0.073175, 0.090535, 0.11147, 0.136903, 0.167811, 0.203461, 0.242871, 0.284898, 0.327178, 0.368404, 0.408003, 0.444778, 0.476537, 0.503107, 0.525318, 0.543352, 0.557253, 0.568634, 0.57903, 0.588684, 0.598891, 0.609981, 0.621362, 0.634283, 0.648546, 0.663707, 0.680046, 0.696165, 0.711964, 0.727011, 0.741301, 0.757405, 0.772071, 0.785581, 0.798238, 0.809677, 0.819702, 0.828599, 0.836722, 0.844443, 0.851107, 0.853252, 0.854746, 0.856174, 0.857821, 0.859532, 0.86146, 0.863257, 0.865139, 0.867319, 0.869696, 0.874302, 0.878588, 0.882439, 0.885929, 0.889473, 0.893226, 0.896696, 0.899897, 0.902596, 0.904831, 0.905525, 0.905665, 0.905503, 0.905158, 0.904783, 0.904082, 0.903347, 0.902761, 0.902377, 0.901983, 0.903424, 0.904313, 0.905315, 0.906446, 0.908092, 0.910123, 0.91295, 0.915585, 0.918444, 0.921302, 0.924337, 0.927219, 0.92974, 0.931922, 0.934142, 0.935906, 0.937086, 0.937641, 0.938301, 0.937652, 0.940441, 0.942518, 0.943259, 0.943031, 0.942117, 0.940632, 0.938428, 0.93666, 0.935256, 0.933022, 0.92688, 0.921057, 0.915483, 0.91102, 0.908293, 0.907283, 0.908191, 0.911169, 0.916189, 0.922855, 0.920605, 0.919482, 0.919489, 0.921276, 0.924526, 0.927733, 0.931974, 0.93677, 0.941483, 0.946802, 0.951203, 0.954437, 0.957047, 0.959729, 0.962539, 0.964858, 0.966042, 0.966647, 0.96631, 0.96546, 0.964841, 0.963656, 0.961698, 0.959454, 0.957327, 0.95514, 0.953558, 0.952732, 0.952181, 0.951731, 0.952146, 0.952641, 0.954057, 0.957078, 0.960639, 0.964222, 0.968307, 0.972691, 0.977423, 0.982898, 0.987144, 0.990734, 0.993983, 0.996787, 0.998753, 1.0, 0.999927, 0.999152, 0.997129, 0.993884, 0.989686, 0.983735, 0.976213, 0.967813, 0.958343, 0.94844, 0.938203, 0.927725, 0.917039, 0.905999, 0.893868, 0.881683, 0.868647, 0.854635, 0.84062, 0.826016, 0.809516, 0.791867, 0.772443, 0.749107, 0.720346, 0.688185, 0.651283, 0.61005, 0.566031, 0.52097, 0.474659, 0.429259, 0.385857, 0.342092, 0.30068, 0.263176, 0.227704, 0.195721, 0.16809, 0.14468, 0.124831, 0.108237, 0.094401, 0.082363, 0.0715, 0.062691, 0.054985, 0.048195, 0.042864, 0.038598, 0.034947, 0.031999, 0.029588, 0.027418, 0.025577, 0.023959, 0.021672, 0.019148, 0.016331, 0.010989, 0.007379, 0.006511, 0.00471, 0.002065], "wavelength": [2078, 2079, 2080, 2081, 2082, 2083, 2084, 2085, 2086, 2087, 2088, 2089, 2090, 2091, 2092, 2093, 2094, 2095, 2096, 2097, 2098, 2099, 2100, 2101, 2102, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2111, 2112, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2121, 2122, 2123, 2124, 2125, 2126, 2127, 2128, 2129, 2130, 2131, 2132, 2133, 2134, 2135, 2136, 2137, 2138, 2139, 2140, 2141, 2142, 2143, 2144, 2145, 2146, 2147, 2148, 2149, 2150, 2151, 2152, 2153, 2154, 2155, 2156, 2157, 2158, 2159, 2160, 2161, 2162, 2163, 2164, 2165, 2166, 2167, 2168, 2169, 2170, 2171, 2172, 2173, 2174, 2175, 2176, 2177, 2178, 2179, 2180, 2181, 2182, 2183, 2184, 2185, 2186, 2187, 2188, 2189, 2190, 2191, 2192, 2193, 2194, 2195, 2196, 2197, 2198, 2199, 2200, 2201, 2202, 2203, 2204, 2205, 2206, 2207, 2208, 2209, 2210, 2211, 2212, 2213, 2214, 2215, 2216, 2217, 2218, 2219, 2220, 2221, 2222, 2223, 2224, 2225, 2226, 2227, 2228, 2229, 2230, 2231, 2232, 2233, 2234, 2235, 2236, 2237, 2238, 2239, 2240, 2241, 2242, 2243, 2244, 2245, 2246, 2247, 2248, 2249, 2250, 2251, 2252, 2253, 2254, 2255, 2256, 2257, 2258, 2259, 2260, 2261, 2262, 2263, 2264, 2265, 2266, 2267, 2268, 2269, 2270, 2271, 2272, 2273, 2274, 2275, 2276, 2277, 2278, 2279, 2280, 2281, 2282, 2283, 2284, 2285, 2286, 2287, 2288, 2289, 2290, 2291, 2292, 2293, 2294, 2295, 2296, 2297, 2298, 2299, 2300, 2301, 2302, 2303, 2304, 2305, 2306, 2307, 2308, 2309, 2310, 2311, 2312, 2313, 2314, 2315, 2316, 2317, 2318, 2319, 2320]}}], "metadata_type": "eo_s2_nrt"}	2021-08-27 05:57:10.951689+00	opendatacubeusername	\N
2	s2b_nrt_granule	{"format": {"name": "GeoTiff"}, "platform": {"code": "SENTINEL_2B"}, "instrument": {"name": "MSI"}, "product_type": "ard", "processing_level": "Level-2"}	4	{"name": "s2b_nrt_granule", "metadata": {"format": {"name": "GeoTiff"}, "platform": {"code": "SENTINEL_2B"}, "instrument": {"name": "MSI"}, "product_type": "ard", "processing_level": "Level-2"}, "description": "Sentinel-2B MSI ARD NRT - NBAR NBART and Pixel Quality", "measurements": [{"name": "azimuthal_exiting", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["azimuthal_exiting"]}, {"name": "azimuthal_incident", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["azimuthal_incident"]}, {"name": "exiting", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["exiting"]}, {"name": "incident", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["incident"]}, {"name": "relative_azimuth", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["relative_azimuth"]}, {"name": "relative_slope", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["relative_slope"]}, {"name": "satellite_azimuth", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["satellite_azimuth"]}, {"name": "satellite_view", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["satellite_view"]}, {"name": "solar_azimuth", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["solar_azimuth"]}, {"name": "solar_zenith", "dtype": "float32", "units": "1", "nodata": -999, "aliases": ["solar_zenith"]}, {"name": "terrain_shadow", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["terrain_shadow"]}, {"name": "fmask", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["mask", "Fmask"], "flags_definition": {"fmask": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "nodata", "1": "valid", "2": "cloud", "3": "shadow", "4": "snow", "5": "water"}, "description": "Fmask"}}}, {"name": "nbar_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "flags_definition": {"contiguity": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "not_contiguous", "1": "contiguous"}, "description": "Pixel contiguity in band stack"}}}, {"name": "nbar_coastal_aerosol", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_01", "nbar_B01", "nbar_Band1"], "spectral_definition": {"response": [0.006797798, 0.01099643, 0.004208363, 0.006568034, 0.005883123, 0.00713011, 0.004333651, 0.006263537, 0.004393687, 0.00253157, 0.000621707, 0.002117729, 0.003175796, 0.005213085, 0.003387375, 0.00258671, 0.002384167, 0.004595227, 0.012990945, 0.050622293, 0.18872241, 0.459106539, 0.730160597, 0.847259495, 0.871235903, 0.881448354, 0.899392736, 0.918669431, 0.933420754, 0.94596319, 0.95041031, 0.953972339, 0.96903168, 0.999546173, 1, 0.976368067, 0.96404957, 0.95417544, 0.923744832, 0.88548879, 0.809016274, 0.601561144, 0.306766029, 0.108527711, 0.030542088, 0.008935131], "wavelength": [411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456]}}, {"name": "nbar_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_02", "nbar_B02", "nbar_Band2"], "spectral_definition": {"response": [0.001893306, 0.019440751, 0.020059028, 0.014109631, 0.015612858, 0.015448868, 0.017034152, 0.013311359, 0.014462036, 0.009592091, 0.014500694, 0.011159264, 0.013332524, 0.01355731, 0.01426, 0.014717634, 0.015989541, 0.030654247, 0.055432753, 0.120228972, 0.252260953, 0.462862499, 0.65241169, 0.77750832, 0.824333103, 0.832077099, 0.835037767, 0.838761115, 0.864126031, 0.883293587, 0.90569382, 0.921186621, 0.936616967, 0.931024626, 0.927547539, 0.916622744, 0.9060165, 0.897870416, 0.903146598, 0.908994286, 0.920859439, 0.924523699, 0.918843658, 0.907981319, 0.898032665, 0.88735796, 0.873065866, 0.857761622, 0.846132814, 0.843382711, 0.857924772, 0.879320632, 0.903975503, 0.919580552, 0.946712663, 0.969406608, 0.993636046, 0.999320649, 1, 0.995107621, 0.984163047, 0.979509527, 0.978185449, 0.972278886, 0.96293492, 0.95355824, 0.938134944, 0.924777929, 0.909590075, 0.902313691, 0.892251397, 0.890060534, 0.891851681, 0.899164865, 0.910901434, 0.924636296, 0.938626228, 0.953526854, 0.971831245, 0.987690608, 0.996791216, 0.993851876, 0.9816383, 0.958970396, 0.893259218, 0.736063596, 0.52101528, 0.332578748, 0.195080476, 0.117429222, 0.075138809, 0.050991983, 0.032154822, 0.015134166, 0.004477169], "wavelength": [438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532]}}, {"name": "nbar_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_03", "nbar_B03", "nbar_Band3"], "spectral_definition": {"response": [0.005090312, 0.026897029, 0.12087986, 0.33742273, 0.603624689, 0.810967523, 0.91573833, 0.92605288, 0.92083242, 0.911237119, 0.902005739, 0.897081513, 0.899066029, 0.900672338, 0.902488081, 0.906886173, 0.915610562, 0.927756371, 0.941055569, 0.954196504, 0.966908428, 0.981390028, 0.991619278, 1, 0.999754078, 0.994046577, 0.981792818, 0.968692612, 0.957607907, 0.945644641, 0.92580977, 0.897152993, 0.838534201, 0.698446797, 0.493502787, 0.276900547, 0.107781358, 0.029913795, 0.007336673, 0.000838123], "wavelength": [536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582]}}, {"name": "nbar_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_04", "nbar_B04", "nbar_Band4"], "spectral_definition": {"response": [0.002584, 0.034529, 0.14997, 0.464826, 0.817746, 0.965324, 0.983869, 0.9969, 1.0, 0.995449, 0.991334, 0.977215, 0.936802, 0.873776, 0.814166, 0.776669, 0.764864, 0.775091, 0.801359, 0.830828, 0.857112, 0.883581, 0.90895, 0.934759, 0.955931, 0.96811, 0.973219, 0.971572, 0.969003, 0.965712, 0.960481, 0.944811, 0.884152, 0.706167, 0.422967, 0.189853, 0.063172, 0.020615, 0.002034], "wavelength": [646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685]}}, {"name": "nbar_red_edge_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_05", "nbar_B05", "nbar_Band5"], "spectral_definition": {"response": [0.010471827, 0.057252544, 0.214724996, 0.547189415, 0.871043978, 0.968446586, 0.99124182, 1, 0.99509331, 0.987602081, 0.979408704, 0.970910946, 0.959528083, 0.94236861, 0.926720132, 0.894557475, 0.767248071, 0.504134435, 0.180610636, 0.034019737, 0.002436944], "wavelength": [694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714]}}, {"name": "nbar_red_edge_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_06", "nbar_B06", "nbar_Band6"], "spectral_definition": {"response": [0.017433807, 0.105812957, 0.386050533, 0.782313159, 0.905953099, 0.916416606, 0.92333441, 0.932013378, 0.947550036, 0.965839591, 0.978552758, 0.991319723, 1, 0.999955845, 0.971267313, 0.81917496, 0.467395748, 0.094120897, 0.009834009], "wavelength": [730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748]}}, {"name": "nbar_red_edge_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_07", "nbar_B07", "nbar_Band7"], "spectral_definition": {"response": [0.010282026, 0.037427714, 0.112026989, 0.257953812, 0.478980823, 0.730216783, 0.912510408, 0.971721033, 0.964616097, 0.955734525, 0.964925586, 0.986223289, 1, 0.998046627, 0.98393444, 0.96569621, 0.947277433, 0.927083998, 0.90976539, 0.886948914, 0.859517187, 0.827959173, 0.776383783, 0.671173028, 0.481809979, 0.236251944, 0.069538392, 0.013431956, 0.001257675], "wavelength": [766, 767, 768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794]}}, {"name": "nbar_nir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_08", "nbar_B08", "nbar_Band8"], "spectral_definition": {"response": [0.000386696, 0.003018401, 0.01669158, 0.028340486, 0.0502885, 0.08626388, 0.149596686, 0.258428566, 0.425108406, 0.631697563, 0.803109115, 0.904984654, 0.939674653, 0.944958731, 0.948238826, 0.963880684, 0.979861632, 0.991635585, 0.996362309, 1, 0.998257939, 0.998488834, 0.989253171, 0.98294089, 0.968189827, 0.958222106, 0.951650369, 0.947054991, 0.944166995, 0.948383123, 0.946461415, 0.942132884, 0.929937199, 0.914683918, 0.893248878, 0.873037871, 0.852648452, 0.836447483, 0.824300756, 0.814333379, 0.810955964, 0.803715941, 0.791980175, 0.783270185, 0.767838865, 0.754167357, 0.742309406, 0.727235815, 0.719323269, 0.713866399, 0.718941021, 0.726527917, 0.738324031, 0.750210769, 0.761800392, 0.769900245, 0.781725199, 0.78381047, 0.783069959, 0.782718588, 0.781644143, 0.780380397, 0.781443024, 0.781701218, 0.78177353, 0.780064535, 0.777591823, 0.770831803, 0.764574958, 0.753876586, 0.743324604, 0.733775698, 0.722497914, 0.712900724, 0.699439134, 0.688575227, 0.674039061, 0.657552716, 0.643729834, 0.62865391, 0.614005803, 0.603233252, 0.594982815, 0.588091928, 0.585186507, 0.582889219, 0.581493721, 0.580137218, 0.574804624, 0.576654614, 0.572399696, 0.570992768, 0.569291451, 0.571025201, 0.570861066, 0.572213154, 0.575418141, 0.577804028, 0.579603586, 0.579294979, 0.578302049, 0.57565598, 0.569721665, 0.561891364, 0.556830745, 0.549385012, 0.545858439, 0.542536249, 0.541895109, 0.539852497, 0.537997281, 0.53195493, 0.522275927, 0.505572421, 0.48804203, 0.469610434, 0.456107021, 0.445848869, 0.443119818, 0.445581498, 0.447532506, 0.440183411, 0.418240241, 0.369455837, 0.301788007, 0.235014942, 0.174244972, 0.122382945, 0.083462794, 0.056162189, 0.038006008, 0.024240249, 0.014845963, 0.006132899], "wavelength": [774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885, 886, 887, 888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 907]}}, {"name": "nbar_nir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_8A", "nbar_B8A", "nbar_Band8A"], "spectral_definition": {"response": [0.001661751, 0.01602581, 0.032253895, 0.073411273, 0.168937582, 0.345506138, 0.569417239, 0.79634996, 0.937581155, 0.980942645, 0.987241334, 0.994409463, 0.998963959, 0.999788107, 1, 0.994482469, 0.987807181, 0.983157165, 0.979826684, 0.975089851, 0.972818786, 0.966320275, 0.958195153, 0.941870745, 0.894185366, 0.778588669, 0.597362542, 0.377361257, 0.184667876, 0.079045495, 0.033393337, 0.015808546, 0.00162404], "wavelength": [848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880]}}, {"name": "nbar_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_11", "nbar_B11", "nbar_Band11"], "spectral_definition": {"response": [0.0000115, 0.000026996, 0.000081157, 0.000169507, 0.000273428, 0.000343776, 0.000459515, 0.000651677, 0.0008223, 0.001076746, 0.001428776, 0.001958681, 0.002660821, 0.003682001, 0.005217308, 0.007572684, 0.011246256, 0.01713141, 0.026703068, 0.041388968, 0.062904714, 0.094492263, 0.139743066, 0.200760503, 0.281513117, 0.380879812, 0.490209915, 0.606204368, 0.714558374, 0.80351452, 0.86986655, 0.916284448, 0.946609049, 0.963892644, 0.973065345, 0.977057349, 0.977796293, 0.976890332, 0.975338048, 0.973392995, 0.971480798, 0.969740168, 0.969095034, 0.96969742, 0.970522078, 0.972736269, 0.976138953, 0.978944681, 0.981010782, 0.983513536, 0.984837133, 0.984404132, 0.983920166, 0.983372624, 0.981458796, 0.979391949, 0.978058392, 0.976263051, 0.975392679, 0.9757089, 0.976805245, 0.978986183, 0.981998545, 0.98520893, 0.988659162, 0.992331977, 0.994804634, 0.99589809, 0.995903119, 0.994773417, 0.992101664, 0.988591774, 0.984908418, 0.981101728, 0.976805235, 0.97354566, 0.971948013, 0.97053597, 0.970436371, 0.972382602, 0.975244492, 0.978552743, 0.982971465, 0.98808508, 0.992662671, 0.996435703, 0.99906056, 1, 0.999036445, 0.996642174, 0.993293536, 0.989674029, 0.98579838, 0.982153372, 0.979817194, 0.979473331, 0.980262857, 0.982464858, 0.986000509, 0.989562258, 0.991723341, 0.992201372, 0.98939229, 0.982102331, 0.970157085, 0.953186779, 0.932369062, 0.908001591, 0.884086561, 0.864271526, 0.850889881, 0.844206087, 0.843448232, 0.847024828, 0.848701823, 0.840540222, 0.81352592, 0.756843245, 0.670393147, 0.565754809, 0.457566037, 0.353763564, 0.256912748, 0.176281, 0.115842988, 0.073512768, 0.046527708, 0.02905985, 0.018579999, 0.012463091, 0.00878944, 0.006316358, 0.004582867, 0.003359394, 0.002462997, 0.001990739, 0.001501488, 0.001123371, 0.00078272, 0.000541322, 0.000281204, 0.00013347], "wavelength": [1538, 1539, 1540, 1541, 1542, 1543, 1544, 1545, 1546, 1547, 1548, 1549, 1550, 1551, 1552, 1553, 1554, 1555, 1556, 1557, 1558, 1559, 1560, 1561, 1562, 1563, 1564, 1565, 1566, 1567, 1568, 1569, 1570, 1571, 1572, 1573, 1574, 1575, 1576, 1577, 1578, 1579, 1580, 1581, 1582, 1583, 1584, 1585, 1586, 1587, 1588, 1589, 1590, 1591, 1592, 1593, 1594, 1595, 1596, 1597, 1598, 1599, 1600, 1601, 1602, 1603, 1604, 1605, 1606, 1607, 1608, 1609, 1610, 1611, 1612, 1613, 1614, 1615, 1616, 1617, 1618, 1619, 1620, 1621, 1622, 1623, 1624, 1625, 1626, 1627, 1628, 1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636, 1637, 1638, 1639, 1640, 1641, 1642, 1643, 1644, 1645, 1646, 1647, 1648, 1649, 1650, 1651, 1652, 1653, 1654, 1655, 1656, 1657, 1658, 1659, 1660, 1661, 1662, 1663, 1664, 1665, 1666, 1667, 1668, 1669, 1670, 1671, 1672, 1673, 1674, 1675, 1676, 1677, 1678, 1679]}}, {"name": "nbar_swir_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbar_band_12", "nbar_B12", "nbar_Band12"], "spectral_definition": {"response": [0.000227567, 0.000739283, 0.001656775, 0.003019587, 0.004589377, 0.005924935, 0.007534774, 0.008748008, 0.010265481, 0.012236179, 0.014593479, 0.017458937, 0.021063245, 0.025428056, 0.03060944, 0.037234457, 0.045771325, 0.056362502, 0.070016996, 0.088004988, 0.110694417, 0.138884174, 0.173287791, 0.214374591, 0.261990789, 0.317227795, 0.380865706, 0.449470316, 0.522785467, 0.598898522, 0.672128213, 0.737899139, 0.792930708, 0.835658783, 0.866335142, 0.886329697, 0.897588245, 0.901517855, 0.900790721, 0.897113531, 0.892352598, 0.88796428, 0.884432193, 0.882095059, 0.881695748, 0.88269782, 0.887154405, 0.892732955, 0.898903582, 0.905619271, 0.912841006, 0.920179789, 0.926912882, 0.933094888, 0.938438355, 0.943377038, 0.945579227, 0.947407512, 0.948568289, 0.94882972, 0.948111791, 0.947115734, 0.946126982, 0.944870644, 0.943485039, 0.941894052, 0.942445527, 0.943274219, 0.944243794, 0.94528606, 0.946212496, 0.947084905, 0.947941677, 0.948940117, 0.949880321, 0.950676414, 0.951054332, 0.951531833, 0.952326952, 0.952721089, 0.952552047, 0.952417855, 0.952654092, 0.95296197, 0.95331832, 0.953779111, 0.954291677, 0.954837035, 0.955539257, 0.956750259, 0.957986198, 0.959237259, 0.960451396, 0.96141302, 0.96264388, 0.964122014, 0.963609737, 0.963104517, 0.962753979, 0.961850624, 0.960730243, 0.959560745, 0.958377188, 0.956972347, 0.955119849, 0.953076144, 0.95406055, 0.955176712, 0.955719159, 0.955674616, 0.955356546, 0.954611539, 0.953453566, 0.952124922, 0.950597985, 0.948594073, 0.948562399, 0.948548442, 0.94829598, 0.947706109, 0.946620434, 0.94521576, 0.943480979, 0.942137936, 0.940654943, 0.938918576, 0.941493007, 0.943778866, 0.945751584, 0.947277308, 0.948481875, 0.949621704, 0.950767479, 0.951991493, 0.953624457, 0.955262594, 0.952413026, 0.950488752, 0.949721652, 0.949105026, 0.949712169, 0.95167296, 0.955012323, 0.959777857, 0.966208245, 0.973886163, 0.970920044, 0.969139883, 0.968329935, 0.967635904, 0.967555279, 0.968040602, 0.968508397, 0.968956722, 0.969510275, 0.969967732, 0.969097684, 0.968258197, 0.967549788, 0.96650394, 0.965459532, 0.964366923, 0.962929804, 0.961665594, 0.96063821, 0.959368085, 0.959707097, 0.960359643, 0.9616448, 0.962729828, 0.96370081, 0.964773629, 0.965512685, 0.96634935, 0.96753842, 0.96886815, 0.970549249, 0.972426171, 0.974301395, 0.976012041, 0.977203216, 0.978986062, 0.980446263, 0.981524356, 0.982531672, 0.983336508, 0.98463147, 0.986737985, 0.989144288, 0.991223348, 0.99318448, 0.995273324, 0.996704667, 0.998282418, 0.999605161, 1, 0.998654554, 0.995753158, 0.990605371, 0.981520886, 0.968715091, 0.951679125, 0.929343556, 0.902305299, 0.87044084, 0.831947776, 0.786119345, 0.736343248, 0.681862245, 0.623137717, 0.564024643, 0.506650261, 0.451376118, 0.400487569, 0.354176773, 0.309839746, 0.269312679, 0.234102225, 0.20225298, 0.173669677, 0.149356419, 0.128957364, 0.111530972, 0.09689948, 0.084874763, 0.074063524, 0.064469344, 0.056321561, 0.049381236, 0.043196026, 0.037986086, 0.033468826, 0.028983375, 0.025085752, 0.020007676, 0.013837921, 0.008464001, 0.004443102, 0.000848571], "wavelength": [2065, 2066, 2067, 2068, 2069, 2070, 2071, 2072, 2073, 2074, 2075, 2076, 2077, 2078, 2079, 2080, 2081, 2082, 2083, 2084, 2085, 2086, 2087, 2088, 2089, 2090, 2091, 2092, 2093, 2094, 2095, 2096, 2097, 2098, 2099, 2100, 2101, 2102, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2111, 2112, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2121, 2122, 2123, 2124, 2125, 2126, 2127, 2128, 2129, 2130, 2131, 2132, 2133, 2134, 2135, 2136, 2137, 2138, 2139, 2140, 2141, 2142, 2143, 2144, 2145, 2146, 2147, 2148, 2149, 2150, 2151, 2152, 2153, 2154, 2155, 2156, 2157, 2158, 2159, 2160, 2161, 2162, 2163, 2164, 2165, 2166, 2167, 2168, 2169, 2170, 2171, 2172, 2173, 2174, 2175, 2176, 2177, 2178, 2179, 2180, 2181, 2182, 2183, 2184, 2185, 2186, 2187, 2188, 2189, 2190, 2191, 2192, 2193, 2194, 2195, 2196, 2197, 2198, 2199, 2200, 2201, 2202, 2203, 2204, 2205, 2206, 2207, 2208, 2209, 2210, 2211, 2212, 2213, 2214, 2215, 2216, 2217, 2218, 2219, 2220, 2221, 2222, 2223, 2224, 2225, 2226, 2227, 2228, 2229, 2230, 2231, 2232, 2233, 2234, 2235, 2236, 2237, 2238, 2239, 2240, 2241, 2242, 2243, 2244, 2245, 2246, 2247, 2248, 2249, 2250, 2251, 2252, 2253, 2254, 2255, 2256, 2257, 2258, 2259, 2260, 2261, 2262, 2263, 2264, 2265, 2266, 2267, 2268, 2269, 2270, 2271, 2272, 2273, 2274, 2275, 2276, 2277, 2278, 2279, 2280, 2281, 2282, 2283, 2284, 2285, 2286, 2287, 2288, 2289, 2290, 2291, 2292, 2293, 2294, 2295, 2296, 2297, 2298, 2299, 2300, 2301, 2302, 2303]}}, {"name": "nbart_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "flags_definition": {"contiguity": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "not_contiguous", "1": "contiguous"}, "description": "Pixel contiguity in band stack"}}}, {"name": "nbart_coastal_aerosol", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_01", "nbart_B01", "nbart_Band1"], "spectral_definition": {"response": [0.006797798, 0.01099643, 0.004208363, 0.006568034, 0.005883123, 0.00713011, 0.004333651, 0.006263537, 0.004393687, 0.00253157, 0.000621707, 0.002117729, 0.003175796, 0.005213085, 0.003387375, 0.00258671, 0.002384167, 0.004595227, 0.012990945, 0.050622293, 0.18872241, 0.459106539, 0.730160597, 0.847259495, 0.871235903, 0.881448354, 0.899392736, 0.918669431, 0.933420754, 0.94596319, 0.95041031, 0.953972339, 0.96903168, 0.999546173, 1, 0.976368067, 0.96404957, 0.95417544, 0.923744832, 0.88548879, 0.809016274, 0.601561144, 0.306766029, 0.108527711, 0.030542088, 0.008935131], "wavelength": [411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456]}}, {"name": "nbart_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_02", "nbart_B02", "nbart_Band2"], "spectral_definition": {"response": [0.001893306, 0.019440751, 0.020059028, 0.014109631, 0.015612858, 0.015448868, 0.017034152, 0.013311359, 0.014462036, 0.009592091, 0.014500694, 0.011159264, 0.013332524, 0.01355731, 0.01426, 0.014717634, 0.015989541, 0.030654247, 0.055432753, 0.120228972, 0.252260953, 0.462862499, 0.65241169, 0.77750832, 0.824333103, 0.832077099, 0.835037767, 0.838761115, 0.864126031, 0.883293587, 0.90569382, 0.921186621, 0.936616967, 0.931024626, 0.927547539, 0.916622744, 0.9060165, 0.897870416, 0.903146598, 0.908994286, 0.920859439, 0.924523699, 0.918843658, 0.907981319, 0.898032665, 0.88735796, 0.873065866, 0.857761622, 0.846132814, 0.843382711, 0.857924772, 0.879320632, 0.903975503, 0.919580552, 0.946712663, 0.969406608, 0.993636046, 0.999320649, 1, 0.995107621, 0.984163047, 0.979509527, 0.978185449, 0.972278886, 0.96293492, 0.95355824, 0.938134944, 0.924777929, 0.909590075, 0.902313691, 0.892251397, 0.890060534, 0.891851681, 0.899164865, 0.910901434, 0.924636296, 0.938626228, 0.953526854, 0.971831245, 0.987690608, 0.996791216, 0.993851876, 0.9816383, 0.958970396, 0.893259218, 0.736063596, 0.52101528, 0.332578748, 0.195080476, 0.117429222, 0.075138809, 0.050991983, 0.032154822, 0.015134166, 0.004477169], "wavelength": [438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532]}}, {"name": "nbart_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_03", "nbart_B03", "nbart_Band3"], "spectral_definition": {"response": [0.005090312, 0.026897029, 0.12087986, 0.33742273, 0.603624689, 0.810967523, 0.91573833, 0.92605288, 0.92083242, 0.911237119, 0.902005739, 0.897081513, 0.899066029, 0.900672338, 0.902488081, 0.906886173, 0.915610562, 0.927756371, 0.941055569, 0.954196504, 0.966908428, 0.981390028, 0.991619278, 1, 0.999754078, 0.994046577, 0.981792818, 0.968692612, 0.957607907, 0.945644641, 0.92580977, 0.897152993, 0.838534201, 0.698446797, 0.493502787, 0.276900547, 0.107781358, 0.029913795, 0.007336673, 0.000838123], "wavelength": [536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582]}}, {"name": "nbart_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_04", "nbart_B04", "nbart_Band4"], "spectral_definition": {"response": [0.002584, 0.034529, 0.14997, 0.464826, 0.817746, 0.965324, 0.983869, 0.9969, 1.0, 0.995449, 0.991334, 0.977215, 0.936802, 0.873776, 0.814166, 0.776669, 0.764864, 0.775091, 0.801359, 0.830828, 0.857112, 0.883581, 0.90895, 0.934759, 0.955931, 0.96811, 0.973219, 0.971572, 0.969003, 0.965712, 0.960481, 0.944811, 0.884152, 0.706167, 0.422967, 0.189853, 0.063172, 0.020615, 0.002034], "wavelength": [646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685]}}, {"name": "nbart_red_edge_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_05", "nbart_B05", "nbart_Band5"], "spectral_definition": {"response": [0.010471827, 0.057252544, 0.214724996, 0.547189415, 0.871043978, 0.968446586, 0.99124182, 1, 0.99509331, 0.987602081, 0.979408704, 0.970910946, 0.959528083, 0.94236861, 0.926720132, 0.894557475, 0.767248071, 0.504134435, 0.180610636, 0.034019737, 0.002436944], "wavelength": [694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714]}}, {"name": "nbart_red_edge_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_06", "nbart_B06", "nbart_Band6"], "spectral_definition": {"response": [0.017433807, 0.105812957, 0.386050533, 0.782313159, 0.905953099, 0.916416606, 0.92333441, 0.932013378, 0.947550036, 0.965839591, 0.978552758, 0.991319723, 1, 0.999955845, 0.971267313, 0.81917496, 0.467395748, 0.094120897, 0.009834009], "wavelength": [730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748]}}, {"name": "nbart_red_edge_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_07", "nbart_B07", "nbart_Band7"], "spectral_definition": {"response": [0.010282026, 0.037427714, 0.112026989, 0.257953812, 0.478980823, 0.730216783, 0.912510408, 0.971721033, 0.964616097, 0.955734525, 0.964925586, 0.986223289, 1, 0.998046627, 0.98393444, 0.96569621, 0.947277433, 0.927083998, 0.90976539, 0.886948914, 0.859517187, 0.827959173, 0.776383783, 0.671173028, 0.481809979, 0.236251944, 0.069538392, 0.013431956, 0.001257675], "wavelength": [766, 767, 768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794]}}, {"name": "nbart_nir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_08", "nbart_B08", "nbart_Band8"], "spectral_definition": {"response": [0.000386696, 0.003018401, 0.01669158, 0.028340486, 0.0502885, 0.08626388, 0.149596686, 0.258428566, 0.425108406, 0.631697563, 0.803109115, 0.904984654, 0.939674653, 0.944958731, 0.948238826, 0.963880684, 0.979861632, 0.991635585, 0.996362309, 1, 0.998257939, 0.998488834, 0.989253171, 0.98294089, 0.968189827, 0.958222106, 0.951650369, 0.947054991, 0.944166995, 0.948383123, 0.946461415, 0.942132884, 0.929937199, 0.914683918, 0.893248878, 0.873037871, 0.852648452, 0.836447483, 0.824300756, 0.814333379, 0.810955964, 0.803715941, 0.791980175, 0.783270185, 0.767838865, 0.754167357, 0.742309406, 0.727235815, 0.719323269, 0.713866399, 0.718941021, 0.726527917, 0.738324031, 0.750210769, 0.761800392, 0.769900245, 0.781725199, 0.78381047, 0.783069959, 0.782718588, 0.781644143, 0.780380397, 0.781443024, 0.781701218, 0.78177353, 0.780064535, 0.777591823, 0.770831803, 0.764574958, 0.753876586, 0.743324604, 0.733775698, 0.722497914, 0.712900724, 0.699439134, 0.688575227, 0.674039061, 0.657552716, 0.643729834, 0.62865391, 0.614005803, 0.603233252, 0.594982815, 0.588091928, 0.585186507, 0.582889219, 0.581493721, 0.580137218, 0.574804624, 0.576654614, 0.572399696, 0.570992768, 0.569291451, 0.571025201, 0.570861066, 0.572213154, 0.575418141, 0.577804028, 0.579603586, 0.579294979, 0.578302049, 0.57565598, 0.569721665, 0.561891364, 0.556830745, 0.549385012, 0.545858439, 0.542536249, 0.541895109, 0.539852497, 0.537997281, 0.53195493, 0.522275927, 0.505572421, 0.48804203, 0.469610434, 0.456107021, 0.445848869, 0.443119818, 0.445581498, 0.447532506, 0.440183411, 0.418240241, 0.369455837, 0.301788007, 0.235014942, 0.174244972, 0.122382945, 0.083462794, 0.056162189, 0.038006008, 0.024240249, 0.014845963, 0.006132899], "wavelength": [774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885, 886, 887, 888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 907]}}, {"name": "nbart_nir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_8A", "nbart_B8A", "nbart_Band8A"], "spectral_definition": {"response": [0.001661751, 0.01602581, 0.032253895, 0.073411273, 0.168937582, 0.345506138, 0.569417239, 0.79634996, 0.937581155, 0.980942645, 0.987241334, 0.994409463, 0.998963959, 0.999788107, 1, 0.994482469, 0.987807181, 0.983157165, 0.979826684, 0.975089851, 0.972818786, 0.966320275, 0.958195153, 0.941870745, 0.894185366, 0.778588669, 0.597362542, 0.377361257, 0.184667876, 0.079045495, 0.033393337, 0.015808546, 0.00162404], "wavelength": [848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880]}}, {"name": "nbart_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_11", "nbart_B11", "nbart_Band11"], "spectral_definition": {"response": [0.0000115, 0.000026996, 0.000081157, 0.000169507, 0.000273428, 0.000343776, 0.000459515, 0.000651677, 0.0008223, 0.001076746, 0.001428776, 0.001958681, 0.002660821, 0.003682001, 0.005217308, 0.007572684, 0.011246256, 0.01713141, 0.026703068, 0.041388968, 0.062904714, 0.094492263, 0.139743066, 0.200760503, 0.281513117, 0.380879812, 0.490209915, 0.606204368, 0.714558374, 0.80351452, 0.86986655, 0.916284448, 0.946609049, 0.963892644, 0.973065345, 0.977057349, 0.977796293, 0.976890332, 0.975338048, 0.973392995, 0.971480798, 0.969740168, 0.969095034, 0.96969742, 0.970522078, 0.972736269, 0.976138953, 0.978944681, 0.981010782, 0.983513536, 0.984837133, 0.984404132, 0.983920166, 0.983372624, 0.981458796, 0.979391949, 0.978058392, 0.976263051, 0.975392679, 0.9757089, 0.976805245, 0.978986183, 0.981998545, 0.98520893, 0.988659162, 0.992331977, 0.994804634, 0.99589809, 0.995903119, 0.994773417, 0.992101664, 0.988591774, 0.984908418, 0.981101728, 0.976805235, 0.97354566, 0.971948013, 0.97053597, 0.970436371, 0.972382602, 0.975244492, 0.978552743, 0.982971465, 0.98808508, 0.992662671, 0.996435703, 0.99906056, 1, 0.999036445, 0.996642174, 0.993293536, 0.989674029, 0.98579838, 0.982153372, 0.979817194, 0.979473331, 0.980262857, 0.982464858, 0.986000509, 0.989562258, 0.991723341, 0.992201372, 0.98939229, 0.982102331, 0.970157085, 0.953186779, 0.932369062, 0.908001591, 0.884086561, 0.864271526, 0.850889881, 0.844206087, 0.843448232, 0.847024828, 0.848701823, 0.840540222, 0.81352592, 0.756843245, 0.670393147, 0.565754809, 0.457566037, 0.353763564, 0.256912748, 0.176281, 0.115842988, 0.073512768, 0.046527708, 0.02905985, 0.018579999, 0.012463091, 0.00878944, 0.006316358, 0.004582867, 0.003359394, 0.002462997, 0.001990739, 0.001501488, 0.001123371, 0.00078272, 0.000541322, 0.000281204, 0.00013347], "wavelength": [1538, 1539, 1540, 1541, 1542, 1543, 1544, 1545, 1546, 1547, 1548, 1549, 1550, 1551, 1552, 1553, 1554, 1555, 1556, 1557, 1558, 1559, 1560, 1561, 1562, 1563, 1564, 1565, 1566, 1567, 1568, 1569, 1570, 1571, 1572, 1573, 1574, 1575, 1576, 1577, 1578, 1579, 1580, 1581, 1582, 1583, 1584, 1585, 1586, 1587, 1588, 1589, 1590, 1591, 1592, 1593, 1594, 1595, 1596, 1597, 1598, 1599, 1600, 1601, 1602, 1603, 1604, 1605, 1606, 1607, 1608, 1609, 1610, 1611, 1612, 1613, 1614, 1615, 1616, 1617, 1618, 1619, 1620, 1621, 1622, 1623, 1624, 1625, 1626, 1627, 1628, 1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636, 1637, 1638, 1639, 1640, 1641, 1642, 1643, 1644, 1645, 1646, 1647, 1648, 1649, 1650, 1651, 1652, 1653, 1654, 1655, 1656, 1657, 1658, 1659, 1660, 1661, 1662, 1663, 1664, 1665, 1666, 1667, 1668, 1669, 1670, 1671, 1672, 1673, 1674, 1675, 1676, 1677, 1678, 1679]}}, {"name": "nbart_swir_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band_12", "nbart_B12", "nbart_Band12"], "spectral_definition": {"response": [0.000227567, 0.000739283, 0.001656775, 0.003019587, 0.004589377, 0.005924935, 0.007534774, 0.008748008, 0.010265481, 0.012236179, 0.014593479, 0.017458937, 0.021063245, 0.025428056, 0.03060944, 0.037234457, 0.045771325, 0.056362502, 0.070016996, 0.088004988, 0.110694417, 0.138884174, 0.173287791, 0.214374591, 0.261990789, 0.317227795, 0.380865706, 0.449470316, 0.522785467, 0.598898522, 0.672128213, 0.737899139, 0.792930708, 0.835658783, 0.866335142, 0.886329697, 0.897588245, 0.901517855, 0.900790721, 0.897113531, 0.892352598, 0.88796428, 0.884432193, 0.882095059, 0.881695748, 0.88269782, 0.887154405, 0.892732955, 0.898903582, 0.905619271, 0.912841006, 0.920179789, 0.926912882, 0.933094888, 0.938438355, 0.943377038, 0.945579227, 0.947407512, 0.948568289, 0.94882972, 0.948111791, 0.947115734, 0.946126982, 0.944870644, 0.943485039, 0.941894052, 0.942445527, 0.943274219, 0.944243794, 0.94528606, 0.946212496, 0.947084905, 0.947941677, 0.948940117, 0.949880321, 0.950676414, 0.951054332, 0.951531833, 0.952326952, 0.952721089, 0.952552047, 0.952417855, 0.952654092, 0.95296197, 0.95331832, 0.953779111, 0.954291677, 0.954837035, 0.955539257, 0.956750259, 0.957986198, 0.959237259, 0.960451396, 0.96141302, 0.96264388, 0.964122014, 0.963609737, 0.963104517, 0.962753979, 0.961850624, 0.960730243, 0.959560745, 0.958377188, 0.956972347, 0.955119849, 0.953076144, 0.95406055, 0.955176712, 0.955719159, 0.955674616, 0.955356546, 0.954611539, 0.953453566, 0.952124922, 0.950597985, 0.948594073, 0.948562399, 0.948548442, 0.94829598, 0.947706109, 0.946620434, 0.94521576, 0.943480979, 0.942137936, 0.940654943, 0.938918576, 0.941493007, 0.943778866, 0.945751584, 0.947277308, 0.948481875, 0.949621704, 0.950767479, 0.951991493, 0.953624457, 0.955262594, 0.952413026, 0.950488752, 0.949721652, 0.949105026, 0.949712169, 0.95167296, 0.955012323, 0.959777857, 0.966208245, 0.973886163, 0.970920044, 0.969139883, 0.968329935, 0.967635904, 0.967555279, 0.968040602, 0.968508397, 0.968956722, 0.969510275, 0.969967732, 0.969097684, 0.968258197, 0.967549788, 0.96650394, 0.965459532, 0.964366923, 0.962929804, 0.961665594, 0.96063821, 0.959368085, 0.959707097, 0.960359643, 0.9616448, 0.962729828, 0.96370081, 0.964773629, 0.965512685, 0.96634935, 0.96753842, 0.96886815, 0.970549249, 0.972426171, 0.974301395, 0.976012041, 0.977203216, 0.978986062, 0.980446263, 0.981524356, 0.982531672, 0.983336508, 0.98463147, 0.986737985, 0.989144288, 0.991223348, 0.99318448, 0.995273324, 0.996704667, 0.998282418, 0.999605161, 1, 0.998654554, 0.995753158, 0.990605371, 0.981520886, 0.968715091, 0.951679125, 0.929343556, 0.902305299, 0.87044084, 0.831947776, 0.786119345, 0.736343248, 0.681862245, 0.623137717, 0.564024643, 0.506650261, 0.451376118, 0.400487569, 0.354176773, 0.309839746, 0.269312679, 0.234102225, 0.20225298, 0.173669677, 0.149356419, 0.128957364, 0.111530972, 0.09689948, 0.084874763, 0.074063524, 0.064469344, 0.056321561, 0.049381236, 0.043196026, 0.037986086, 0.033468826, 0.028983375, 0.025085752, 0.020007676, 0.013837921, 0.008464001, 0.004443102, 0.000848571], "wavelength": [2065, 2066, 2067, 2068, 2069, 2070, 2071, 2072, 2073, 2074, 2075, 2076, 2077, 2078, 2079, 2080, 2081, 2082, 2083, 2084, 2085, 2086, 2087, 2088, 2089, 2090, 2091, 2092, 2093, 2094, 2095, 2096, 2097, 2098, 2099, 2100, 2101, 2102, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2111, 2112, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2121, 2122, 2123, 2124, 2125, 2126, 2127, 2128, 2129, 2130, 2131, 2132, 2133, 2134, 2135, 2136, 2137, 2138, 2139, 2140, 2141, 2142, 2143, 2144, 2145, 2146, 2147, 2148, 2149, 2150, 2151, 2152, 2153, 2154, 2155, 2156, 2157, 2158, 2159, 2160, 2161, 2162, 2163, 2164, 2165, 2166, 2167, 2168, 2169, 2170, 2171, 2172, 2173, 2174, 2175, 2176, 2177, 2178, 2179, 2180, 2181, 2182, 2183, 2184, 2185, 2186, 2187, 2188, 2189, 2190, 2191, 2192, 2193, 2194, 2195, 2196, 2197, 2198, 2199, 2200, 2201, 2202, 2203, 2204, 2205, 2206, 2207, 2208, 2209, 2210, 2211, 2212, 2213, 2214, 2215, 2216, 2217, 2218, 2219, 2220, 2221, 2222, 2223, 2224, 2225, 2226, 2227, 2228, 2229, 2230, 2231, 2232, 2233, 2234, 2235, 2236, 2237, 2238, 2239, 2240, 2241, 2242, 2243, 2244, 2245, 2246, 2247, 2248, 2249, 2250, 2251, 2252, 2253, 2254, 2255, 2256, 2257, 2258, 2259, 2260, 2261, 2262, 2263, 2264, 2265, 2266, 2267, 2268, 2269, 2270, 2271, 2272, 2273, 2274, 2275, 2276, 2277, 2278, 2279, 2280, 2281, 2282, 2283, 2284, 2285, 2286, 2287, 2288, 2289, 2290, 2291, 2292, 2293, 2294, 2295, 2296, 2297, 2298, 2299, 2300, 2301, 2302, 2303]}}], "metadata_type": "eo_s2_nrt"}	2021-08-27 05:57:11.104633+00	opendatacubeusername	\N
3	ga_ls7e_ard_provisional_3	{"product": {"name": "ga_ls7e_ard_provisional_3"}, "properties": {"eo:platform": "landsat-7", "odc:producer": "ga.gov.au", "eo:instrument": "ETM", "odc:product_family": "ard", "dea:product_maturity": "provisional", "landsat:collection_number": 2}}	5	{"name": "ga_ls7e_ard_provisional_3", "license": "CC-BY-4.0", "metadata": {"product": {"name": "ga_ls7e_ard_provisional_3"}, "properties": {"eo:platform": "landsat-7", "odc:producer": "ga.gov.au", "eo:instrument": "ETM", "odc:product_family": "ard", "dea:product_maturity": "provisional", "landsat:collection_number": 2}}, "description": "Geoscience Australia Landsat 7 Enhanced Thematic Mapper Plus Analysis Ready Data Collection 3 (provisional)", "measurements": [{"name": "nbart_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band01", "blue"]}, {"name": "nbart_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band02", "green"]}, {"name": "nbart_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band03", "red"]}, {"name": "nbart_nir", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band04", "nir"]}, {"name": "nbart_swir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band05", "swir_1", "swir1"]}, {"name": "nbart_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band07", "swir_2", "swir2"]}, {"name": "nbart_panchromatic", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band08", "panchromatic"]}, {"name": "oa_fmask", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["fmask"], "flags_definition": {"fmask": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "nodata", "1": "valid", "2": "cloud", "3": "shadow", "4": "snow", "5": "water"}, "description": "Fmask"}}}, {"name": "oa_nbart_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["nbart_contiguity"], "flags_definition": {"contiguous": {"bits": [0], "values": {"0": false, "1": true}}}}, {"name": "oa_azimuthal_exiting", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_exiting"]}, {"name": "oa_azimuthal_incident", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_incident"]}, {"name": "oa_combined_terrain_shadow", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["combined_terrain_shadow"]}, {"name": "oa_exiting_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["exiting_angle"]}, {"name": "oa_incident_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["incident_angle"]}, {"name": "oa_relative_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_azimuth"]}, {"name": "oa_relative_slope", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_slope"]}, {"name": "oa_satellite_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_azimuth"]}, {"name": "oa_satellite_view", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_view"]}, {"name": "oa_solar_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_azimuth"]}, {"name": "oa_solar_zenith", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_zenith"]}, {"name": "oa_time_delta", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["time_delta"]}], "metadata_type": "eo3_landsat_ard"}	2021-08-27 05:58:45.498206+00	opendatacubeusername	\N
4	ga_ls8c_ard_provisional_3	{"product": {"name": "ga_ls8c_ard_provisional_3"}, "properties": {"eo:platform": "landsat-8", "odc:producer": "ga.gov.au", "eo:instrument": "OLI_TIRS", "odc:product_family": "ard", "dea:product_maturity": "provisional", "landsat:collection_number": 2}}	5	{"name": "ga_ls8c_ard_provisional_3", "license": "CC-BY-4.0", "metadata": {"product": {"name": "ga_ls8c_ard_provisional_3"}, "properties": {"eo:platform": "landsat-8", "odc:producer": "ga.gov.au", "eo:instrument": "OLI_TIRS", "odc:product_family": "ard", "dea:product_maturity": "provisional", "landsat:collection_number": 2}}, "description": "Geoscience Australia Landsat 8 Operational Land Imager and Thermal Infra-Red Scanner Analysis Ready Data Collection 3 (provisional)", "measurements": [{"name": "nbart_coastal_aerosol", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band01", "coastal_aerosol"]}, {"name": "nbart_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band02", "blue"]}, {"name": "nbart_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band03", "green"]}, {"name": "nbart_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band04", "red"]}, {"name": "nbart_nir", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band05", "nir"]}, {"name": "nbart_swir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band06", "swir_1", "swir1"]}, {"name": "nbart_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band07", "swir_2", "swir2"]}, {"name": "nbart_panchromatic", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band08", "panchromatic"]}, {"name": "oa_fmask", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["fmask"], "flags_definition": {"fmask": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "nodata", "1": "valid", "2": "cloud", "3": "shadow", "4": "snow", "5": "water"}, "description": "Fmask"}}}, {"name": "oa_nbart_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["nbart_contiguity"], "flags_definition": {"contiguous": {"bits": [0], "values": {"0": false, "1": true}}}}, {"name": "oa_azimuthal_exiting", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_exiting"]}, {"name": "oa_azimuthal_incident", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_incident"]}, {"name": "oa_combined_terrain_shadow", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["combined_terrain_shadow"]}, {"name": "oa_exiting_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["exiting_angle"]}, {"name": "oa_incident_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["incident_angle"]}, {"name": "oa_relative_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_azimuth"]}, {"name": "oa_relative_slope", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_slope"]}, {"name": "oa_satellite_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_azimuth"]}, {"name": "oa_satellite_view", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_view"]}, {"name": "oa_solar_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_azimuth"]}, {"name": "oa_solar_zenith", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_zenith"]}, {"name": "oa_time_delta", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["time_delta"]}], "metadata_type": "eo3_landsat_ard"}	2021-08-27 05:58:49.305285+00	opendatacubeusername	\N
5	ga_s2am_ard_provisional_3	{"product": {"name": "ga_s2am_ard_provisional_3"}, "properties": {"eo:platform": "sentinel-2a", "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "odc:product_family": "ard", "dea:product_maturity": "provisional"}}	5	{"name": "ga_s2am_ard_provisional_3", "license": "CC-BY-4.0", "metadata": {"product": {"name": "ga_s2am_ard_provisional_3"}, "properties": {"eo:platform": "sentinel-2a", "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "odc:product_family": "ard", "dea:product_maturity": "provisional"}}, "description": "Geoscience Australia Sentinel 2a MSI Analysis Ready Data Collection 3 (provisional)", "measurements": [{"name": "nbart_coastal_aerosol", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band01", "coastal_aerosol"]}, {"name": "nbart_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band02", "blue"]}, {"name": "nbart_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band03", "green"]}, {"name": "nbart_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band04", "red"]}, {"name": "nbart_red_edge_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band05", "red_edge_1"]}, {"name": "nbart_red_edge_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band06", "red_edge_2"]}, {"name": "nbart_red_edge_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band07", "red_edge_3"]}, {"name": "nbart_nir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band08", "nir_1"]}, {"name": "nbart_nir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band8a", "nir_2"]}, {"name": "nbart_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band11", "swir_2", "swir2"]}, {"name": "nbart_swir_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band12", "swir_3"]}, {"name": "oa_fmask", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["fmask"], "flags_definition": {"fmask": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "nodata", "1": "valid", "2": "cloud", "3": "shadow", "4": "snow", "5": "water"}, "description": "Fmask"}}}, {"name": "oa_nbart_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["nbart_contiguity"], "flags_definition": {"contiguous": {"bits": [0], "values": {"0": false, "1": true}}}}, {"name": "oa_azimuthal_exiting", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_exiting"]}, {"name": "oa_azimuthal_incident", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_incident"]}, {"name": "oa_combined_terrain_shadow", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["combined_terrain_shadow"]}, {"name": "oa_exiting_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["exiting_angle"]}, {"name": "oa_incident_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["incident_angle"]}, {"name": "oa_relative_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_azimuth"]}, {"name": "oa_relative_slope", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_slope"]}, {"name": "oa_satellite_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_azimuth"]}, {"name": "oa_satellite_view", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_view"]}, {"name": "oa_solar_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_azimuth"]}, {"name": "oa_solar_zenith", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_zenith"]}, {"name": "oa_time_delta", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["time_delta"]}], "metadata_type": "eo3_landsat_ard"}	2021-08-27 05:58:53.139651+00	opendatacubeusername	\N
6	ga_s2bm_ard_provisional_3	{"product": {"name": "ga_s2bm_ard_provisional_3"}, "properties": {"eo:platform": "sentinel-2b", "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "odc:product_family": "ard", "dea:product_maturity": "provisional"}}	5	{"name": "ga_s2bm_ard_provisional_3", "license": "CC-BY-4.0", "metadata": {"product": {"name": "ga_s2bm_ard_provisional_3"}, "properties": {"eo:platform": "sentinel-2b", "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "odc:product_family": "ard", "dea:product_maturity": "provisional"}}, "description": "Geoscience Australia Sentinel 2b MSI Analysis Ready Data Collection 3 (provisional)", "measurements": [{"name": "nbart_coastal_aerosol", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band01", "coastal_aerosol"]}, {"name": "nbart_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band02", "blue"]}, {"name": "nbart_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band03", "green"]}, {"name": "nbart_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band04", "red"]}, {"name": "nbart_red_edge_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band05", "red_edge_1"]}, {"name": "nbart_red_edge_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band06", "red_edge_2"]}, {"name": "nbart_red_edge_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band07", "red_edge_3"]}, {"name": "nbart_nir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band08", "nir_1"]}, {"name": "nbart_nir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band8a", "nir_2"]}, {"name": "nbart_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band11", "swir_2", "swir2"]}, {"name": "nbart_swir_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band12", "swir_3"]}, {"name": "oa_fmask", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["fmask"], "flags_definition": {"fmask": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "nodata", "1": "valid", "2": "cloud", "3": "shadow", "4": "snow", "5": "water"}, "description": "Fmask"}}}, {"name": "oa_nbart_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["nbart_contiguity"], "flags_definition": {"contiguous": {"bits": [0], "values": {"0": false, "1": true}}}}, {"name": "oa_azimuthal_exiting", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_exiting"]}, {"name": "oa_azimuthal_incident", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_incident"]}, {"name": "oa_combined_terrain_shadow", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["combined_terrain_shadow"]}, {"name": "oa_exiting_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["exiting_angle"]}, {"name": "oa_incident_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["incident_angle"]}, {"name": "oa_relative_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_azimuth"]}, {"name": "oa_relative_slope", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_slope"]}, {"name": "oa_satellite_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_azimuth"]}, {"name": "oa_satellite_view", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_view"]}, {"name": "oa_solar_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_azimuth"]}, {"name": "oa_solar_zenith", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_zenith"]}, {"name": "oa_time_delta", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["time_delta"]}], "metadata_type": "eo3_landsat_ard"}	2021-08-27 05:58:56.931999+00	opendatacubeusername	\N
7	wofs_albers	{"format": {"name": "GeoTIFF"}, "product_type": "wofs"}	2	{"name": "wofs_albers", "storage": {"crs": "EPSG:3577", "tile_size": {"x": 100000.0, "y": 100000.0}, "resolution": {"x": 25, "y": -25}, "dimension_order": ["time", "y", "x"]}, "metadata": {"format": {"name": "GeoTIFF"}, "product_type": "wofs"}, "description": "Historic Flood Mapping Water Observations from Space", "measurements": [{"name": "water", "dtype": "int16", "units": "1", "nodata": 1, "flags_definition": {"dry": {"bits": [7, 6, 5, 4, 3, 1, 0], "values": {"0": true}, "description": "No water detected"}, "sea": {"bits": 2, "values": {"0": false, "1": true}, "description": "Sea"}, "wet": {"bits": [7, 6, 5, 4, 3, 1, 0], "values": {"128": true}, "description": "Clear and Wet"}, "cloud": {"bits": 6, "values": {"0": false, "1": true}, "description": "Cloudy"}, "nodata": {"bits": 0, "values": {"0": false, "1": true}, "description": "No data"}, "high_slope": {"bits": 4, "values": {"0": false, "1": true}, "description": "High slope"}, "cloud_shadow": {"bits": 5, "values": {"0": false, "1": true}, "description": "Cloud shadow"}, "noncontiguous": {"bits": 1, "values": {"0": false, "1": true}, "description": "At least one EO band is missing over over/undersaturated"}, "terrain_or_low_angle": {"bits": 3, "values": {"0": false, "1": true}, "description": "terrain shadow or low solar angle"}}}], "metadata_type": "eo"}	2021-08-27 06:08:21.898359+00	opendatacubeusername	\N
8	ls5_fc_albers	{"format": {"name": "GeoTIFF"}, "platform": {"code": "LANDSAT_5"}, "instrument": {"name": "TM"}, "product_type": "fractional_cover"}	2	{"name": "ls5_fc_albers", "storage": {"crs": "EPSG:3577", "resolution": {"x": 25, "y": -25}, "dimension_order": ["time", "y", "x"]}, "metadata": {"format": {"name": "GeoTIFF"}, "platform": {"code": "LANDSAT_5"}, "instrument": {"name": "TM"}, "product_type": "fractional_cover"}, "description": "Landsat 5 Fractional Cover 25 metre, 100km tile, Australian Albers Equal Area projection (EPSG:3577)", "measurements": [{"name": "BS", "dtype": "uint8", "units": "percent", "nodata": 255, "aliases": ["bare"]}, {"name": "PV", "dtype": "uint8", "units": "percent", "nodata": 255, "aliases": ["green_veg"]}, {"name": "NPV", "dtype": "uint8", "units": "percent", "nodata": 255, "aliases": ["dead_veg"]}, {"name": "UE", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["err"]}], "metadata_type": "eo"}	2021-08-27 06:08:23.90859+00	opendatacubeusername	\N
9	ls8_fc_albers	{"format": {"name": "GeoTIFF"}, "platform": {"code": "LANDSAT_8"}, "instrument": {"name": "OLI_TIRS"}, "product_type": "fractional_cover"}	2	{"name": "ls8_fc_albers", "storage": {"crs": "EPSG:3577", "resolution": {"x": 25, "y": -25}, "dimension_order": ["time", "y", "x"]}, "metadata": {"format": {"name": "GeoTIFF"}, "platform": {"code": "LANDSAT_8"}, "instrument": {"name": "OLI_TIRS"}, "product_type": "fractional_cover"}, "description": "Landsat 8 Fractional Cover 25 metre, 100km tile, Australian Albers Equal Area projection (EPSG:3577)", "measurements": [{"name": "BS", "dtype": "uint8", "units": "percent", "nodata": 255, "aliases": ["bare"]}, {"name": "PV", "dtype": "uint8", "units": "percent", "nodata": 255, "aliases": ["green_veg"]}, {"name": "NPV", "dtype": "uint8", "units": "percent", "nodata": 255, "aliases": ["dead_veg"]}, {"name": "UE", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["err"]}], "metadata_type": "eo"}	2021-08-27 06:08:23.948692+00	opendatacubeusername	\N
10	ls7_fc_albers	{"format": {"name": "GeoTIFF"}, "platform": {"code": "LANDSAT_7"}, "instrument": {"name": "ETM"}, "product_type": "fractional_cover"}	2	{"name": "ls7_fc_albers", "storage": {"crs": "EPSG:3577", "tile_size": {"x": 100000.0, "y": 100000.0}, "resolution": {"x": 25, "y": -25}, "dimension_order": ["time", "y", "x"]}, "metadata": {"format": {"name": "GeoTIFF"}, "platform": {"code": "LANDSAT_7"}, "instrument": {"name": "ETM"}, "product_type": "fractional_cover"}, "description": "Landsat 7 Fractional Cover 25 metre, 100km tile, Australian Albers Equal Area projection (EPSG:3577)", "measurements": [{"name": "BS", "dtype": "int16", "units": "percent", "nodata": -1, "aliases": ["bare"]}, {"name": "PV", "dtype": "int16", "units": "percent", "nodata": -1, "aliases": ["green_veg"]}, {"name": "NPV", "dtype": "int16", "units": "percent", "nodata": -1, "aliases": ["dead_veg"]}, {"name": "UE", "dtype": "int16", "units": "1", "nodata": -1, "aliases": ["err"]}], "metadata_type": "eo"}	2021-08-27 06:08:26.325711+00	opendatacubeusername	\N
\.


--
-- Data for Name: metadata_type; Type: TABLE DATA; Schema: agdc; Owner: agdc_admin
--

COPY agdc.metadata_type (id, name, definition, added, added_by, updated) FROM stdin;
1	eo3	{"name": "eo3", "dataset": {"id": ["id"], "label": ["label"], "format": ["properties", "odc:file_format"], "sources": ["lineage", "source_datasets"], "creation_dt": ["properties", "odc:processing_datetime"], "grid_spatial": ["grid_spatial", "projection"], "measurements": ["measurements"], "search_fields": {"lat": {"type": "double-range", "max_offset": [["extent", "lat", "end"]], "min_offset": [["extent", "lat", "begin"]], "description": "Latitude range"}, "lon": {"type": "double-range", "max_offset": [["extent", "lon", "end"]], "min_offset": [["extent", "lon", "begin"]], "description": "Longitude range"}, "time": {"type": "datetime-range", "max_offset": [["properties", "dtr:end_datetime"], ["properties", "datetime"]], "min_offset": [["properties", "dtr:start_datetime"], ["properties", "datetime"]], "description": "Acquisition time range"}, "platform": {"offset": ["properties", "eo:platform"], "indexed": false, "description": "Platform code"}, "instrument": {"offset": ["properties", "eo:instrument"], "indexed": false, "description": "Instrument name"}, "region_code": {"offset": ["properties", "odc:region_code"], "description": "Spatial reference code from the provider. For Landsat region_code is a scene path row:\\n        '{:03d}{:03d}.format(path,row)'.\\nFor Sentinel it is MGRS code. In general it is a unique string identifier that datasets covering roughly the same spatial region share.\\n"}, "product_family": {"offset": ["properties", "odc:product_family"], "indexed": false, "description": "Product family code"}, "dataset_maturity": {"offset": ["properties", "dea:dataset_maturity"], "indexed": false, "description": "One of - final|interim|nrt  (near real time)"}}}, "description": "Default EO3 with no custom fields"}	2021-08-27 05:23:32.987585+00	opendatacubeusername	\N
2	eo	{"name": "eo", "dataset": {"id": ["id"], "label": ["ga_label"], "format": ["format", "name"], "sources": ["lineage", "source_datasets"], "creation_dt": ["creation_dt"], "grid_spatial": ["grid_spatial", "projection"], "measurements": ["image", "bands"], "search_fields": {"lat": {"type": "double-range", "max_offset": [["extent", "coord", "ur", "lat"], ["extent", "coord", "lr", "lat"], ["extent", "coord", "ul", "lat"], ["extent", "coord", "ll", "lat"]], "min_offset": [["extent", "coord", "ur", "lat"], ["extent", "coord", "lr", "lat"], ["extent", "coord", "ul", "lat"], ["extent", "coord", "ll", "lat"]], "description": "Latitude range"}, "lon": {"type": "double-range", "max_offset": [["extent", "coord", "ul", "lon"], ["extent", "coord", "ur", "lon"], ["extent", "coord", "ll", "lon"], ["extent", "coord", "lr", "lon"]], "min_offset": [["extent", "coord", "ul", "lon"], ["extent", "coord", "ur", "lon"], ["extent", "coord", "ll", "lon"], ["extent", "coord", "lr", "lon"]], "description": "Longitude range"}, "time": {"type": "datetime-range", "max_offset": [["extent", "to_dt"], ["extent", "center_dt"]], "min_offset": [["extent", "from_dt"], ["extent", "center_dt"]], "description": "Acquisition time"}, "platform": {"offset": ["platform", "code"], "description": "Platform code"}, "instrument": {"offset": ["instrument", "name"], "description": "Instrument name"}, "product_type": {"offset": ["product_type"], "description": "Product code"}}}, "description": "Earth Observation datasets.\\n\\nExpected metadata structure produced by the eodatasets library, as used internally at GA.\\n\\nhttps://github.com/GeoscienceAustralia/eo-datasets\\n"}	2021-08-27 05:23:33.019158+00	opendatacubeusername	\N
3	telemetry	{"name": "telemetry", "dataset": {"id": ["id"], "label": ["ga_label"], "sources": ["lineage", "source_datasets"], "creation_dt": ["creation_dt"], "search_fields": {"gsi": {"offset": ["acquisition", "groundstation", "code"], "indexed": false, "description": "Ground Station Identifier (eg. ASA)"}, "time": {"type": "datetime-range", "max_offset": [["acquisition", "los"]], "min_offset": [["acquisition", "aos"]], "description": "Acquisition time"}, "orbit": {"type": "integer", "offset": ["acquisition", "platform_orbit"], "description": "Orbit number"}, "sat_row": {"type": "integer-range", "max_offset": [["image", "satellite_ref_point_end", "y"], ["image", "satellite_ref_point_start", "y"]], "min_offset": [["image", "satellite_ref_point_start", "y"]], "description": "Landsat row"}, "platform": {"offset": ["platform", "code"], "description": "Platform code"}, "sat_path": {"type": "integer-range", "max_offset": [["image", "satellite_ref_point_end", "x"], ["image", "satellite_ref_point_start", "x"]], "min_offset": [["image", "satellite_ref_point_start", "x"]], "description": "Landsat path"}, "instrument": {"offset": ["instrument", "name"], "description": "Instrument name"}, "product_type": {"offset": ["product_type"], "description": "Product code"}}}, "description": "Satellite telemetry datasets.\\n\\nExpected metadata structure produced by telemetry datasets from the eodatasets library, as used internally at GA.\\n\\nhttps://github.com/GeoscienceAustralia/eo-datasets\\n"}	2021-08-27 05:23:33.04347+00	opendatacubeusername	\N
4	eo_s2_nrt	{"name": "eo_s2_nrt", "dataset": {"id": ["id"], "label": ["tile_id"], "format": ["format", "name"], "sources": ["lineage", "source_datasets"], "creation_dt": ["system_information", "time_processed"], "grid_spatial": ["grid_spatial", "projection"], "measurements": ["image", "bands"], "search_fields": {"lat": {"type": "double-range", "max_offset": [["extent", "coord", "ur", "lat"], ["extent", "coord", "lr", "lat"], ["extent", "coord", "ul", "lat"], ["extent", "coord", "ll", "lat"]], "min_offset": [["extent", "coord", "ur", "lat"], ["extent", "coord", "lr", "lat"], ["extent", "coord", "ul", "lat"], ["extent", "coord", "ll", "lat"]], "description": "Latitude range"}, "lon": {"type": "double-range", "max_offset": [["extent", "coord", "ul", "lon"], ["extent", "coord", "ur", "lon"], ["extent", "coord", "ll", "lon"], ["extent", "coord", "lr", "lon"]], "min_offset": [["extent", "coord", "ul", "lon"], ["extent", "coord", "ur", "lon"], ["extent", "coord", "ll", "lon"], ["extent", "coord", "lr", "lon"]], "description": "Longitude range"}, "time": {"type": "datetime-range", "max_offset": [["extent", "center_dt"]], "min_offset": [["extent", "center_dt"]], "description": "Acquisition time"}, "format": {"offset": ["format", "name"], "indexed": false, "description": "File format (GeoTIFF, NetCDF)"}, "platform": {"offset": ["platform", "code"], "description": "Platform code"}, "instrument": {"offset": ["instrument", "name"], "description": "Instrument name"}, "product_type": {"offset": ["product_type"], "description": "Product code"}}}, "description": "Legacy S2 NRT document structure"}	2021-08-27 05:57:08.849998+00	opendatacubeusername	\N
5	eo3_landsat_ard	{"name": "eo3_landsat_ard", "dataset": {"id": ["id"], "label": ["label"], "format": ["properties", "odc:file_format"], "sources": ["lineage", "source_datasets"], "creation_dt": ["properties", "odc:processing_datetime"], "grid_spatial": ["grid_spatial", "projection"], "measurements": ["measurements"], "search_fields": {"gqa": {"type": "double", "offset": ["properties", "gqa:cep90"], "description": "GQA Circular error probable (90%)"}, "lat": {"type": "double-range", "max_offset": [["extent", "lat", "end"]], "min_offset": [["extent", "lat", "begin"]], "description": "Latitude range"}, "lon": {"type": "double-range", "max_offset": [["extent", "lon", "end"]], "min_offset": [["extent", "lon", "begin"]], "description": "Longitude range"}, "time": {"type": "datetime-range", "max_offset": [["properties", "dtr:end_datetime"], ["properties", "datetime"]], "min_offset": [["properties", "dtr:start_datetime"], ["properties", "datetime"]], "description": "Acquisition time range"}, "eo_gsd": {"type": "double", "offset": ["properties", "eo:gsd"], "indexed": false, "description": "Ground sample distance, meters"}, "crs_raw": {"offset": ["crs"], "indexed": false, "description": "The raw CRS string as it appears in metadata"}, "platform": {"offset": ["properties", "eo:platform"], "indexed": false, "description": "Platform code"}, "gqa_abs_x": {"type": "double", "offset": ["properties", "gqa:abs_x"], "indexed": false, "description": "TODO: <gqa:abs_x>"}, "gqa_abs_y": {"type": "double", "offset": ["properties", "gqa:abs_y"], "indexed": false, "description": "TODO: <gqa:abs_y>"}, "gqa_cep90": {"type": "double", "offset": ["properties", "gqa:cep90"], "indexed": false, "description": "TODO: <gqa:cep90>"}, "fmask_snow": {"type": "double", "offset": ["properties", "fmask:snow"], "indexed": false, "description": "TODO: <fmask:snow>"}, "gqa_abs_xy": {"type": "double", "offset": ["properties", "gqa:abs_xy"], "indexed": false, "description": "TODO: <gqa:abs_xy>"}, "gqa_mean_x": {"type": "double", "offset": ["properties", "gqa:mean_x"], "indexed": false, "description": "TODO: <gqa:mean_x>"}, "gqa_mean_y": {"type": "double", "offset": ["properties", "gqa:mean_y"], "indexed": false, "description": "TODO: <gqa:mean_y>"}, "instrument": {"offset": ["properties", "eo:instrument"], "indexed": false, "description": "Instrument name"}, "cloud_cover": {"type": "double", "offset": ["properties", "eo:cloud_cover"], "description": "Cloud cover percentage [0, 100]"}, "fmask_clear": {"type": "double", "offset": ["properties", "fmask:clear"], "indexed": false, "description": "TODO: <fmask:clear>"}, "fmask_water": {"type": "double", "offset": ["properties", "fmask:water"], "indexed": false, "description": "TODO: <fmask:water>"}, "gqa_mean_xy": {"type": "double", "offset": ["properties", "gqa:mean_xy"], "indexed": false, "description": "TODO: <gqa:mean_xy>"}, "region_code": {"offset": ["properties", "odc:region_code"], "description": "Spatial reference code from the provider. For Landsat region_code is a scene path row:\\n        '{:03d}{:03d}.format(path,row)'\\nFor Sentinel it is MGRS code. In general it is a unique string identifier that datasets covering roughly the same spatial region share.\\n"}, "gqa_stddev_x": {"type": "double", "offset": ["properties", "gqa:stddev_x"], "indexed": false, "description": "TODO: <gqa:stddev_x>"}, "gqa_stddev_y": {"type": "double", "offset": ["properties", "gqa:stddev_y"], "indexed": false, "description": "TODO: <gqa:stddev_y>"}, "gqa_stddev_xy": {"type": "double", "offset": ["properties", "gqa:stddev_xy"], "indexed": false, "description": "TODO: <gqa:stddev_xy>"}, "eo_sun_azimuth": {"type": "double", "offset": ["properties", "eo:sun_azimuth"], "indexed": false, "description": "TODO: <eo:sun_azimuth>"}, "product_family": {"offset": ["properties", "odc:product_family"], "indexed": false, "description": "Product family code"}, "dataset_maturity": {"offset": ["properties", "dea:dataset_maturity"], "description": "One of - final|interim|nrt  (near real time)"}, "eo_sun_elevation": {"type": "double", "offset": ["properties", "eo:sun_elevation"], "indexed": false, "description": "TODO: <eo:sun_elevation>"}, "landsat_scene_id": {"offset": ["properties", "landsat:landsat_scene_id"], "indexed": false, "description": "Landsat Scene ID"}, "fmask_cloud_shadow": {"type": "double", "offset": ["properties", "fmask:cloud_shadow"], "indexed": false, "description": "TODO: <fmask:cloud_shadow>"}, "gqa_iterative_mean_x": {"type": "double", "offset": ["properties", "gqa:iterative_mean_x"], "indexed": false, "description": "TODO: <gqa:iterative_mean_x>"}, "gqa_iterative_mean_y": {"type": "double", "offset": ["properties", "gqa:iterative_mean_y"], "indexed": false, "description": "TODO: <gqa:iterative_mean_y>"}, "gqa_iterative_mean_xy": {"type": "double", "offset": ["properties", "gqa:iterative_mean_xy"], "indexed": false, "description": "TODO: <gqa:iterative_mean_xy>"}, "gqa_iterative_stddev_x": {"type": "double", "offset": ["properties", "gqa:iterative_stddev_x"], "indexed": false, "description": "TODO: <gqa:iterative_stddev_x>"}, "gqa_iterative_stddev_y": {"type": "double", "offset": ["properties", "gqa:iterative_stddev_y"], "indexed": false, "description": "TODO: <gqa:iterative_stddev_y>"}, "gqa_iterative_stddev_xy": {"type": "double", "offset": ["properties", "gqa:iterative_stddev_xy"], "indexed": false, "description": "TODO: <gqa:iterative_stddev_xy>"}, "gqa_abs_iterative_mean_x": {"type": "double", "offset": ["properties", "gqa:abs_iterative_mean_x"], "indexed": false, "description": "TODO: <gqa:abs_iterative_mean_x>"}, "gqa_abs_iterative_mean_y": {"type": "double", "offset": ["properties", "gqa:abs_iterative_mean_y"], "indexed": false, "description": "TODO: <gqa:abs_iterative_mean_y>"}, "gqa_abs_iterative_mean_xy": {"type": "double", "offset": ["properties", "gqa:abs_iterative_mean_xy"], "indexed": false, "description": "TODO: <gqa:abs_iterative_mean_xy>"}}}, "description": "EO3 for ARD Landsat Collection 3"}	2021-08-27 05:58:43.760751+00	opendatacubeusername	\N
\.


--
-- Data for Name: dataset_spatial; Type: TABLE DATA; Schema: cubedash; Owner: opendatacubeusername
--

COPY cubedash.dataset_spatial (id, dataset_type_ref, center_time, creation_time, region_code, size_bytes, footprint) FROM stdin;
ffa8b91f-22a3-45b4-8439-c80fc4d83140	3	2021-08-18 00:07:21.236053+00	2021-08-18 19:24:39.52624+00	103076	\N	01030000208D7F00000100000018000000F4308B8B79EE0241AB3A4BADBF1744C146FF5B4BBEED02410C404A1BB91744C189CE29ADFC990341F312A78D87E143C107B303CDCC310541F59CC8838E6243C107B303CD2C670641F59CC883570343C126B4B6F39C50074190F1F77780BC42C196C8DB1BDB5007414DD5CB3B7DBC42C1D33CDCB6F0560741B8B51F2B2CBB42C1705A32ABC8590741D49259E5D0BA42C100000000E45E0741000000C0BDBA42C170663B7C92D617415E064CD300F042C1B69B969FBED91741693003BB11F042C163B0E81F0DDA17414FDE16C21AF042C1E0CC76F8E4041841BD0C98A6D6F042C13C0BB088E32A1841FAF891CA8AF142C13A27B0DF733C184171BC394E7DF342C1AA4E61A4C92A1841D8E77B75CBFE42C1AA4E61A4F91A1641D8E77B75AF4644C13C0BB0886B0E164106076E352C4E44C1E7CF0AEE4BF71541E432695DB34E44C1230BA592D78A03413BB0C95CE81944C12D0FB1EA3B1F0341AC21920BF61844C1382D99553EF1024159DA4C75921844C1F4308B8B79EE0241AB3A4BADBF1744C1
828b51ac-6e76-4cb1-a95a-65d01dc6ef69	5	2021-08-29 01:31:01.246989+00	2021-08-29 08:26:20.045536+00	52LHL	\N	0103000020F07F0000010000000500000000000000D8692841000000803A67604100000000A8C32B41000000803A67604100000000A8C32B41000000809D31604100000000D8692841000000809D31604100000000D8692841000000803A676041
301c66d3-a49c-4937-8be0-3f96d01ecc38	4	2021-08-22 01:31:09.006767+00	2021-08-22 04:58:58.982968+00	107073	\N	01030000208C7F0000010000001300000007FE66850EBD104154FE8D6C9BF23DC10000000014BD10410000000095F23DC10000000034281C4100000000738C3EC1154794252E281C414EC733FB798C3EC12E00296DA8291C41F4BFB5E48D8C3EC12C4F52B940291C41F26FC0936D8D3EC12E00296DC4B519410620A58DCABC40C162FAA73B62B419418303B79ACCBC40C11F1AB38B1DB4194179A9ABCECABC40C10000000014B4194100000080D0BC40C1705A32ABDC8B0C41B2B499EAEE6F40C1DEEF4348E48B0C4190EF2BB0E66F40C1000000003C890C41000000C0DD6F40C1CDBBC38F5E2C0D41442B68B5233F40C1168F7E94DE4F0F4136F20068AC383FC18FCDF94CF36610415336C66480563EC1D967244F73B91041024E38623CF53DC10000000006BC1041000000808DF23DC107FE66850EBD104154FE8D6C9BF23DC1
f1917c8f-8937-45e6-9202-f828a09b172c	6	2021-08-29 00:40:45.064194+00	2021-08-29 05:41:02.750914+00	55LDE	\N	0103000020F37F0000010000000C00000000000000D0591C41000000006436604100000000105B1C41000000006436604183292EAC6A551C412743B4ED6A356041038A53947AFB1A41B0B43D6A3B036041A23EB7859AEA1A41CB9422E8CC006041B5F2E274C9E91A4100000000C7006041AC801CAA68E91A4100000000C7006041907881B810E71A4100000000C7006041000000006069184100000000C70060410000000060691841000000006436604100000000B8581C41000000006436604100000000D0591C410000000064366041
830ca898-2874-45ae-afe5-575dbf52f1ec	8	2004-05-11 00:23:56.5+00	2017-10-24 10:01:27.946578+00	\N	\N	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C2541317015B592FC45C1D3F3E7965A36254100000000102046C100000000804F224100000000102046C1
8f27ae72-ed82-461d-ac05-771f772a988e	10	2004-05-19 00:32:42.5+00	2017-10-21 15:03:14.340143+00	6_-29	\N	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C254124FDF0B8D4DC45C1807325294A14254100000000102046C100000000804F224100000000102046C1
345aff57-ae5b-4b41-bf6c-b5b2a327861a	9	2018-05-27 00:36:12+00	2018-08-04 01:00:38.077435+00	\N	\N	0103000020F90D0000010000000600000000000000C05C254100000000102046C1DDBFE8F2B1DA234100000000102046C11ED3E1606C0B2441D823632EC5F445C1051A3B3EE7B6244100000000C05C45C100000000C05C254100000000C05C45C100000000C05C254100000000102046C1
e6e62140-b8d7-46cd-8530-ad9d682f82f5	1	2021-06-29 23:54:36.819617+00	2021-06-30 03:57:49.515075+00	\N	\N	0103000020F47F000001000000050000000000000050A925410000000052525A4100000000804F22410000000052525A4100000000804F22410000000018E759410000000050A925410000000018E759410000000050A925410000000052525A41
6621a608-9c61-4c9b-aa5d-312f6a32866f	1	2021-08-28 23:52:57.049593+00	2021-08-29 03:36:47.484233+00	\N	\N	0103000020F47F0000010000000700000000000000A8BC234100000000C9E75C41EAEE389553BA2341893856A3AEE75C4100000000A010234100000000A6925C410000000050A9254100000000A6925C410000000050A925414B70B54E03DB5C41CE4D0B50103E2541AD295CB00EDE5C4100000000A8BC234100000000C9E75C41
ccf58424-a33f-4cb1-9841-a5f5cf652ea9	1	2021-08-28 23:55:23.726121+00	2021-08-29 04:02:08.547514+00	\N	\N	0103000020F47F0000010000000500000000000000E89B2241000000005A2D59410000000030841E41000000005A2D59410000000030841E410000000020C2584100000000E89B22410000000020C2584100000000E89B2241000000005A2D5941
0cfbd2fc-a5db-4ae2-9ff1-e4266ad46a5f	1	2021-08-29 01:34:37.59306+00	2021-08-29 06:13:52.263865+00	\N	\N	0103000020F07F0000010000000800000000000000705C2541000000806DD45A4100000000E85C25410000000066D45A411611C76AD45D254177C7A95C80D45A414E6E30C98C692541C47F358DA7DA5A41114859CBB4C82541D83F5A8E0B0D5B410000000030D82541000000009D155B4100000000705C2541000000009D155B4100000000705C2541000000806DD45A41
f0298262-f75f-46b0-ac96-2ee2cc54b887	7	2004-05-03 00:32:41.5+00	2018-05-20 08:30:52.436405+00	6_-29	\N	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C25412FF0E81E6DC345C196446B5FBEF8244100000000102046C100000000804F224100000000102046C1
\.


--
-- Data for Name: product; Type: TABLE DATA; Schema: cubedash; Owner: opendatacubeusername
--

COPY cubedash.product (id, name, dataset_count, last_refresh, last_successful_summary, source_product_refs, derived_product_refs, time_earliest, time_latest, fixed_metadata) FROM stdin;
2	ga_ls7e_ard_provisional_3	1	2021-08-29 23:12:11.121805+00	2021-08-29 23:12:11.121805+00	{}	{}	2021-08-18 00:07:21.236053+00	2021-08-18 00:07:21.236053+00	{"id": "ffa8b91f-22a3-45b4-8439-c80fc4d83140", "gqa": "NaN", "label": "ga_ls7e_ard_provisional_3-2-1_103076_2021-08-18_nrt", "eo_gsd": 15.0, "format": "GeoTIFF", "crs_raw": "epsg:32653", "platform": "landsat-7", "gqa_abs_x": "NaN", "gqa_abs_y": "NaN", "gqa_cep90": "NaN", "fmask_snow": 0.00008182077003228549, "gqa_abs_xy": "NaN", "gqa_mean_x": "NaN", "gqa_mean_y": "NaN", "instrument": "ETM", "cloud_cover": 0.3768730124303096, "fmask_clear": 99.50066747747776, "fmask_water": 0.11604148889058857, "gqa_mean_xy": "NaN", "region_code": "103076", "gqa_stddev_x": "NaN", "gqa_stddev_y": "NaN", "creation_time": "2021-08-18T19:24:39.526240+00:00", "gqa_stddev_xy": "NaN", "eo_sun_azimuth": 56.15238434, "product_family": "ard", "dataset_maturity": "nrt", "eo_sun_elevation": 31.98188606, "landsat_scene_id": "LE71030762021230ASA00", "fmask_cloud_shadow": 0.0063362004313001884, "gqa_iterative_mean_x": "NaN", "gqa_iterative_mean_y": "NaN", "gqa_iterative_mean_xy": "NaN", "gqa_iterative_stddev_x": "NaN", "gqa_iterative_stddev_y": "NaN", "gqa_iterative_stddev_xy": "NaN", "gqa_abs_iterative_mean_x": "NaN", "gqa_abs_iterative_mean_y": "NaN", "gqa_abs_iterative_mean_xy": "NaN"}
3	ga_ls8c_ard_provisional_3	1	2021-08-29 23:12:11.145712+00	2021-08-29 23:12:11.145712+00	{}	{}	2021-08-22 01:31:09.006767+00	2021-08-22 01:31:09.006767+00	{"id": "301c66d3-a49c-4937-8be0-3f96d01ecc38", "gqa": "NaN", "label": "ga_ls8c_ard_provisional_3-2-1_107073_2021-08-22_nrt", "eo_gsd": 15.0, "format": "GeoTIFF", "crs_raw": "epsg:32652", "platform": "landsat-8", "gqa_abs_x": "NaN", "gqa_abs_y": "NaN", "gqa_cep90": "NaN", "fmask_snow": 0.0, "gqa_abs_xy": "NaN", "gqa_mean_x": "NaN", "gqa_mean_y": "NaN", "instrument": "OLI_TIRS", "cloud_cover": 0.0012691125714388253, "fmask_clear": 99.98017042291667, "fmask_water": 0.017725845025840924, "gqa_mean_xy": "NaN", "region_code": "107073", "gqa_stddev_x": "NaN", "gqa_stddev_y": "NaN", "creation_time": "2021-08-22T04:58:58.982968+00:00", "gqa_stddev_xy": "NaN", "eo_sun_azimuth": 46.81969064, "product_family": "ard", "dataset_maturity": "nrt", "eo_sun_elevation": 47.21169755, "landsat_scene_id": "LC81070732021234LGN00", "fmask_cloud_shadow": 0.0008346194860526124, "gqa_iterative_mean_x": "NaN", "gqa_iterative_mean_y": "NaN", "gqa_iterative_mean_xy": "NaN", "gqa_iterative_stddev_x": "NaN", "gqa_iterative_stddev_y": "NaN", "gqa_iterative_stddev_xy": "NaN", "gqa_abs_iterative_mean_x": "NaN", "gqa_abs_iterative_mean_y": "NaN", "gqa_abs_iterative_mean_xy": "NaN"}
1	ga_s2am_ard_provisional_3	1	2021-08-29 23:12:11.130234+00	2021-08-29 23:12:11.130234+00	{}	{}	2021-08-29 01:31:01.246989+00	2021-08-29 01:31:01.246989+00	{"id": "828b51ac-6e76-4cb1-a95a-65d01dc6ef69", "gqa": "NaN", "label": "ga_s2am_ard_provisional_3-2-1_52LHL_2021-08-29_nrt", "eo_gsd": 10.0, "format": "GeoTIFF", "crs_raw": "epsg:32752", "platform": "sentinel-2a", "gqa_abs_x": "NaN", "gqa_abs_y": "NaN", "gqa_cep90": "NaN", "fmask_snow": 0.07106147623929583, "gqa_abs_xy": "NaN", "gqa_mean_x": "NaN", "gqa_mean_y": "NaN", "instrument": "MSI", "cloud_cover": 0.8212381511673817, "fmask_clear": 98.87364010072959, "fmask_water": 0.0866951337255019, "gqa_mean_xy": "NaN", "region_code": "52LHL", "gqa_stddev_x": "NaN", "gqa_stddev_y": "NaN", "creation_time": "2021-08-29T08:26:20.045536+00:00", "gqa_stddev_xy": "NaN", "eo_sun_azimuth": 49.3627516258236, "product_family": "ard", "dataset_maturity": "nrt", "eo_sun_elevation": 33.6443175558024, "landsat_scene_id": null, "fmask_cloud_shadow": 0.1473651381382278, "gqa_iterative_mean_x": "NaN", "gqa_iterative_mean_y": "NaN", "gqa_iterative_mean_xy": "NaN", "gqa_iterative_stddev_x": "NaN", "gqa_iterative_stddev_y": "NaN", "gqa_iterative_stddev_xy": "NaN", "gqa_abs_iterative_mean_x": "NaN", "gqa_abs_iterative_mean_y": "NaN", "gqa_abs_iterative_mean_xy": "NaN"}
5	ls5_fc_albers	1	2021-08-29 23:12:11.421453+00	2021-08-29 23:12:11.421453+00	{}	{}	2004-05-11 00:23:56.5+00	2004-05-11 00:23:56.5+00	{"id": "830ca898-2874-45ae-afe5-575dbf52f1ec", "label": null, "format": "GeoTIFF", "platform": "LANDSAT_5", "instrument": "TM", "product_type": "fractional_cover", "creation_time": "2017-10-24T10:01:27.946578"}
6	ls7_fc_albers	1	2021-08-29 23:12:11.405943+00	2021-08-29 23:12:11.405943+00	{}	{}	2004-05-19 00:32:42.5+00	2004-05-19 00:32:42.5+00	{"id": "8f27ae72-ed82-461d-ac05-771f772a988e", "label": null, "format": "GeoTIFF", "platform": "LANDSAT_7", "instrument": "ETM", "product_type": "fractional_cover", "creation_time": "2017-10-21T15:03:14.340143"}
4	ga_s2bm_ard_provisional_3	1	2021-08-29 23:12:11.422116+00	2021-08-29 23:12:11.422116+00	{}	{}	2021-08-29 00:40:45.064194+00	2021-08-29 00:40:45.064194+00	{"id": "f1917c8f-8937-45e6-9202-f828a09b172c", "gqa": "NaN", "label": "ga_s2bm_ard_provisional_3-2-1_55LDE_2021-08-29_nrt", "eo_gsd": 10.0, "format": "GeoTIFF", "crs_raw": "epsg:32755", "platform": "sentinel-2b", "gqa_abs_x": "NaN", "gqa_abs_y": "NaN", "gqa_cep90": "NaN", "fmask_snow": 0.005133749456492932, "gqa_abs_xy": "NaN", "gqa_mean_x": "NaN", "gqa_mean_y": "NaN", "instrument": "MSI", "cloud_cover": 95.73379167967182, "fmask_clear": 0.023973706866518413, "fmask_water": 4.10925035656634, "gqa_mean_xy": "NaN", "region_code": "55LDE", "gqa_stddev_x": "NaN", "gqa_stddev_y": "NaN", "creation_time": "2021-08-29T05:41:02.750914+00:00", "gqa_stddev_xy": "NaN", "eo_sun_azimuth": 46.1603385068743, "product_family": "ard", "dataset_maturity": "nrt", "eo_sun_elevation": 33.0185676410833, "landsat_scene_id": null, "fmask_cloud_shadow": 0.12785050743883075, "gqa_iterative_mean_x": "NaN", "gqa_iterative_mean_y": "NaN", "gqa_iterative_mean_xy": "NaN", "gqa_iterative_stddev_x": "NaN", "gqa_iterative_stddev_y": "NaN", "gqa_iterative_stddev_xy": "NaN", "gqa_abs_iterative_mean_x": "NaN", "gqa_abs_iterative_mean_y": "NaN", "gqa_abs_iterative_mean_xy": "NaN"}
7	s2b_nrt_granule	0	2021-08-29 23:12:11.880341+00	2021-08-29 23:12:11.880341+00	{}	{}	\N	\N	{}
8	ls8_fc_albers	1	2021-08-29 23:12:11.805118+00	2021-08-29 23:12:11.805118+00	{}	{}	2018-05-27 00:36:12+00	2018-05-27 00:36:12+00	{"id": "345aff57-ae5b-4b41-bf6c-b5b2a327861a", "label": null, "format": "GeoTIFF", "platform": "LANDSAT_8", "instrument": "OLI_TIRS", "product_type": "fractional_cover", "creation_time": "2018-08-04T01:00:38.077435"}
9	s2a_nrt_granule	4	2021-08-29 23:12:11.847418+00	2021-08-29 23:12:11.847418+00	{}	{}	2021-06-29 23:54:36.819617+00	2021-08-29 01:34:37.59306+00	{"format": "GeoTiff", "platform": "SENTINEL_2A", "instrument": "MSI", "product_type": "ard"}
10	wofs_albers	1	2021-08-29 23:12:12.016571+00	2021-08-29 23:12:12.016571+00	{}	{}	2004-05-03 00:32:41.5+00	2004-05-03 00:32:41.5+00	{"id": "f0298262-f75f-46b0-ac96-2ee2cc54b887", "label": null, "format": "GeoTIFF", "platform": "LANDSAT_7", "instrument": "ETM", "product_type": "wofs", "creation_time": "2018-05-20T08:30:52.436405"}
\.


--
-- Data for Name: region; Type: TABLE DATA; Schema: cubedash; Owner: opendatacubeusername
--

COPY cubedash.region (dataset_type_ref, region_code, count, generation_time, footprint) FROM stdin;
5	52LHL	1	2021-08-29 23:12:11.226181+00	0103000020E61000000100000005000000C71AF9215E78604013149240A34C29C0B9394278AB9860400C4ED6314C4629C0861C34BC27996040D3B45A5C8A412BC0638E9C41B9786040F2D8AC3B65482BC0C71AF9215E78604013149240A34C29C0
3	103076	1	2021-08-29 23:12:11.238394+00	0103000020E61000000100000015000000EBD946B4B6736040F6A5A106CDC637C0C60BC7D9B4736040F3525BEEC4C637C0BB91C326A3756040467DDF6A048737C0EBFE6C9E917D604033D6D8E7828136C00B796B2C1D806040D58A2805182E36C0355C9B4E2E806040AF2871F8872C36C0B36B43D035806040C3CC97191D2C36C0533C3CD7428060400F8B9E5D082C36C0266589DEF7BD6040733638A73D7136C03B14FC0208BE6040C02FB084527136C0A8094C9009BE60407BDBD4495D7136C0333F1A9EE3BE60401FC5DB12477236C08D834CFDA4BF6040C9DF0B29267336C026B367F1FDBF6040D876DCD3787536C04462C3D3A0BF6040C2572CCBD68236C0DBC070D7A1B460409A8DE84D560638C08717D9225EB460409E4A4D412E0F38C034C64CB5E6B360402A782EACC50F38C09667043F46756040ABB4CE39A0C937C00C474502BD73604049314462C7C737C0EBD946B4B6736040F6A5A106CDC637C0
4	107073	1	2021-08-29 23:12:11.261959+00	0103000020E6100000010000000D00000088A436E3BDB75F40607A537C54BD31C0B0B7659D5414604084877263641B32C03EDFBA92521460401D90B8DAE81B32C0A97CB2E0ED0760403AB0835EB8D633C04F8AAB6AE5076040878E7A20BFD633C0128FB3A7BE9D5F4075BF40B58B7733C04B6064D7BE9D5F405788B6FA817733C0D303F39EB19D5F40C67DE3A8767733C005A9B6AF17A15F403BC65ABFF93D33C076B952A869AC5F4014CA7AF7D57D32C02D49A91099B75F40C4A4674DE1BE31C08A8BFBB2B3B75F402EAEB7CC4BBD31C088A436E3BDB75F40607A537C54BD31C0
6	55LDE	1	2021-08-29 23:12:11.59185+00	0103000020E61000000100000009000000C49B2FFC7F5562402B3701C8EF222BC0533BE30A86556240A35794E8EF222BC0BD86927A6A5562408501E9DF282C2BC0482E8A40CC4E624092CFBF7FC6072DC0683AA43B794E6240017FF90FD11E2DC0865BF63F754E6240E0D867E9081F2DC0E80994A94842624072DDA98B6B1E2DC01B8C3A6769426240E8C5DA9B2B222BC0C49B2FFC7F5562402B3701C8EF222BC0
8		1	2021-08-29 23:12:11.640659+00	0103000020E610000001000000060000004EE1F0CF44436140432A4E0314A23AC0CDF1074EBA41614068AA66FE0CBE39C08E6DC065F46161409DCA0FD355B239C0A8DEC02C6C636140A8E8F44CDD6C3AC005AC6AC32762614098EB6DB0E5963AC04EE1F0CF44436140432A4E0314A23AC0
10	6_-29	1	2021-08-29 23:12:11.647455+00	0103000020E610000001000000060000004EE1F0CF44436140432A4E0314A23AC0CDF1074EBA41614068AA66FE0CBE39C08E6DC065F46161409DCA0FD355B239C0FEF0A12721636140F4169EF4D2473AC04F6F4752BD606140D721FD1C72973AC04EE1F0CF44436140432A4E0314A23AC0
9		1	2021-08-29 23:12:11.942797+00	0103000020E610000001000000060000000117D347C06361404474E05946963AC0FE8E950BB4536140EA1F4475559C3AC01C0F59695A55614042A7E7B111693AC06B707A9A1D5B6140583ABCFAF8B439C08E6DC065F46161409DCA0FD355B239C00117D347C06361404474E05946963AC0
1		4	2021-08-29 23:12:11.975882+00	0106000020E61000000400000001030000000100000005000000A96F6360B14463405EAEF2093BBA3EC087E1B4DB1345634093CFC566CDB73FC09CEC4545FE1F63406C2E947D26B93FC09C2ADE49FE1F6340A891D0FE86BB3EC0A96F6360B14463405EAEF2093BBA3EC00103000000010000000500000074DFF21B47646340A5683BD421023CC0CA29382FEB64634090C60080AEFF3CC00959276CDB4063408FDE9B8318033DC006B4A1248D406340869F68B468053CC074DFF21B47646340A5683BD421023CC001030000000100000008000000E305FE576060604090CF753BCBCE3AC0803EF3960A606040DB7CE0F698343AC000FF17971C65604054A7BBB202343AC0FD9DA41A86646040CE0517765A483AC00AC0E239E260604060FCDCE800C03AC023B4EDEC6E606040024E37F29CCE3AC0A33A5553656060407D121869DCCE3AC0E305FE576060604090CF753BCBCE3AC00103000000010000000700000054B5F3F8744D63402C4052B8D2E635C0BB805A87C55C6340F7410D029EFC35C02ADEDD8E0961634034D2D8526A0336C09B4B883F596163404CEBEA22AFAE36C0EAB26A9FDA466340BEA51723D7B036C0385DFF675D4D634034CD67C412E735C054B5F3F8744D63402C4052B8D2E635C0
7	6_-29	1	2021-08-29 23:12:12.191934+00	0103000020E610000001000000060000004EE1F0CF44436140432A4E0314A23AC0CDF1074EBA41614068AA66FE0CBE39C08E6DC065F46161409DCA0FD355B239C0DE697840E56261406B4544502D2A3AC0584DD938985F61404A05E605E3973AC04EE1F0CF44436140432A4E0314A23AC0
\.


--
-- Data for Name: time_overview; Type: TABLE DATA; Schema: cubedash; Owner: opendatacubeusername
--

COPY cubedash.time_overview (product_ref, period_type, start_day, dataset_count, time_earliest, time_latest, timeline_period, timeline_dataset_start_days, timeline_dataset_counts, regions, region_dataset_counts, newest_dataset_creation_time, generation_time, product_refresh_time, footprint_count, footprint_geometry, crses, size_bytes) FROM stdin;
1	month	2021-08-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0}	{52LHL}	{1}	2021-08-29 08:26:20.045536+00	2021-08-29 23:12:11.277646+00	2021-08-29 23:12:11.130234+00	1	0103000020F90D000001000000050000008218F512F4BCD9C0DCB2D5EC555E34C176DB958BD5CCF440236099ABFB5934C1BD33F1E6170CF540DA4D3100AEFF35C1DEB2F6FE9359D8C044671481700436C18218F512F4BCD9C0DCB2D5EC555E34C1	{EPSG:32752}	\N
2	month	2021-08-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0}	{103076}	{1}	2021-08-18 19:24:39.52624+00	2021-08-29 23:12:11.283645+00	2021-08-29 23:12:11.121805+00	1	0103000020F90D00000100000018000000AD95835D0AE9E2C055DD1E37F99243C1E3FD3403E6EBE2C021B77D56F29243C10B62F66DDDF7DFC00B148DAF7C5C43C18EBE05681015D2C0A66F7132F0DC42C19E2DE3DDF243BEC054BE0942577D42C14604BF3C13C376408D928CBA3F3642C174C9E35941407740F52B038C3C3642C197278BADE410824010C555E7EA3442C1D839FE4AACFE84400EFD3ADB8F3442C1D6CC4B23CC138A40B2EE3F327E3442C1BBCF28EF9B1E0841FEA14793647242C10B7ABAF1DF2408417736AFE1777242C1EFA7D65878250841BC5DED34817242C1BC20F2BB247A08415EEF0B315D7342C1A9342A0037C50841A19669F22D7442C16A42633956E70841BE383C63317642C15EB789CB43C008415EEA25C88C8142C18CF484AD35350441998FB21333CB43C1918CE6FCAA1904416B4EA63DBBD243C14C53EB53BAEB0341F1E5033533D343C11EDE44F0AF81E0C0F0D619CD5B9543C15FE50D33DE29E2C0273AF3E4429443C18C9C6B2E2DDFE2C0C9530CDECE9343C1AD95835D0AE9E2C055DD1E37F99243C1	{EPSG:32653}	\N
3	month	2021-08-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0}	{107073}	{1}	2021-08-22 04:58:58.982968+00	2021-08-29 23:12:11.294421+00	2021-08-29 23:12:11.145712+00	1	0103000020F90D00000100000013000000F32C99F7919B20C1842E6126AA0E3DC17666ED988F9B20C1B189DFB1A30E3DC1ED2C3B48B0BB15C183E1E1ED06953DC171A61E74B5BB15C1D739D8F20D953DC16A65854D39BA15C1EFFB6F901F953DC18535922D8BBA15C1ABF1A8F5FF953DC196FF57E08AE217C156900AEEE54340C1E355B728EBE317C1CCFF2E16E94340C1FD137CEA2FE417C10120A27EE74340C164109A4738E417C1A2B9C33DED4340C13DE2A2A148AB21C178EF63437B0040C1E008C4AE47AB21C197291300730040C1491E570BF2AB21C1C75EA03E6B0040C1DC924569EF8821C11FF00697939E3FC1B7A3C4B2361321C1C04EA13997563EC19E55FB18DCC020C1C074C28F13733DC192A77CD9389D20C1C64414E350113DC1F2894808179C20C19AEAD7269E0E3DC1F32C99F7919B20C1842E6126AA0E3DC1	{EPSG:32652}	\N
3	year	2021-01-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0}	{107073}	{1}	2021-08-22 04:58:58.982968+00	2021-08-29 23:12:11.332174+00	2021-08-29 23:12:11.145712+00	1	0103000020F90D00000100000005000000F32C99F7919B20C1842E6126AA0E3DC16A65854D39BA15C1EFFB6F901F953DC196FF57E08AE217C156900AEEE54340C1491E570BF2AB21C1C75EA03E6B0040C1F32C99F7919B20C1842E6126AA0E3DC1	{EPSG:32652}	0
2	year	2021-01-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0}	{103076}	{1}	2021-08-18 19:24:39.52624+00	2021-08-29 23:12:11.333302+00	2021-08-29 23:12:11.121805+00	1	0103000020F90D00000100000005000000AD95835D0AE9E2C055DD1E37F99243C1D839FE4AACFE84400EFD3ADB8F3442C16A42633956E70841BE383C63317642C1918CE6FCAA1904416B4EA63DBBD243C1AD95835D0AE9E2C055DD1E37F99243C1	{EPSG:32653}	0
1	year	2021-01-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0}	{52LHL}	{1}	2021-08-29 08:26:20.045536+00	2021-08-29 23:12:11.337254+00	2021-08-29 23:12:11.130234+00	1	0103000020F90D000001000000050000008218F512F4BCD9C0DCB2D5EC555E34C176DB958BD5CCF440236099ABFB5934C1BD33F1E6170CF540DA4D3100AEFF35C1DEB2F6FE9359D8C044671481700436C18218F512F4BCD9C0DCB2D5EC555E34C1	{EPSG:32752}	0
2	all	1900-01-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0}	{103076}	{1}	2021-08-18 19:24:39.52624+00	2021-08-29 23:12:11.340446+00	2021-08-29 23:12:11.121805+00	1	0103000020F90D00000100000005000000AD95835D0AE9E2C055DD1E37F99243C1D839FE4AACFE84400EFD3ADB8F3442C16A42633956E70841BE383C63317642C1918CE6FCAA1904416B4EA63DBBD243C1AD95835D0AE9E2C055DD1E37F99243C1	{EPSG:32653}	0
3	all	1900-01-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0}	{107073}	{1}	2021-08-22 04:58:58.982968+00	2021-08-29 23:12:11.342937+00	2021-08-29 23:12:11.145712+00	1	0103000020F90D00000100000005000000F32C99F7919B20C1842E6126AA0E3DC16A65854D39BA15C1EFFB6F901F953DC196FF57E08AE217C156900AEEE54340C1491E570BF2AB21C1C75EA03E6B0040C1F32C99F7919B20C1842E6126AA0E3DC1	{EPSG:32652}	0
1	all	1900-01-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0}	{52LHL}	{1}	2021-08-29 08:26:20.045536+00	2021-08-29 23:12:11.36806+00	2021-08-29 23:12:11.130234+00	1	0103000020F90D000001000000050000008218F512F4BCD9C0DCB2D5EC555E34C176DB958BD5CCF440236099ABFB5934C1BD33F1E6170CF540DA4D3100AEFF35C1DEB2F6FE9359D8C044671481700436C18218F512F4BCD9C0DCB2D5EC555E34C1	{EPSG:32752}	0
4	month	2021-08-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0}	{55LDE}	{1}	2021-08-29 05:41:02.750914+00	2021-08-29 23:12:11.651573+00	2021-08-29 23:12:11.422116+00	1	0103000020F90D0000010000000C000000E0A48B746782384185D7555FD74D37C176A5D709B8823841587F4DC6E04D37C196D9A70F6880384195826571575537C10A9237DA8AFB374127095DFD6DD538C199A783DF15F537417CBA494D12E838C1EFFF3802DCF43741A3C227B23AE838C14B1A99B7C3F43741E248D6E037E838C19AE3DB262DF43741EC2D056A26E838C1DACFB99021543741A1A7A3F4B1D538C1CCE457246F843741BA47CD13813037C1FAFEE7F120823841C37C4925CF4D37C1E0A48B746782384185D7555FD74D37C1	{EPSG:32755}	\N
5	month	2004-05-01	1	2004-04-30 14:30:00+00	2004-05-31 14:30:00+00	day	{"2004-05-01 00:00:00+00","2004-05-02 00:00:00+00","2004-05-03 00:00:00+00","2004-05-04 00:00:00+00","2004-05-05 00:00:00+00","2004-05-06 00:00:00+00","2004-05-07 00:00:00+00","2004-05-08 00:00:00+00","2004-05-09 00:00:00+00","2004-05-10 00:00:00+00","2004-05-11 00:00:00+00","2004-05-12 00:00:00+00","2004-05-13 00:00:00+00","2004-05-14 00:00:00+00","2004-05-15 00:00:00+00","2004-05-16 00:00:00+00","2004-05-17 00:00:00+00","2004-05-18 00:00:00+00","2004-05-19 00:00:00+00","2004-05-20 00:00:00+00","2004-05-21 00:00:00+00","2004-05-22 00:00:00+00","2004-05-23 00:00:00+00","2004-05-24 00:00:00+00","2004-05-25 00:00:00+00","2004-05-26 00:00:00+00","2004-05-27 00:00:00+00","2004-05-28 00:00:00+00","2004-05-29 00:00:00+00","2004-05-30 00:00:00+00","2004-05-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}	{NULL}	{1}	2017-10-24 10:01:27.946578+00	2021-08-29 23:12:11.687792+00	2021-08-29 23:12:11.421453+00	1	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C2541307015B592FC45C1D3F3E7965A36254100000000102046C100000000804F224100000000102046C1	{EPSG:3577}	\N
6	month	2004-05-01	1	2004-04-30 14:30:00+00	2004-05-31 14:30:00+00	day	{"2004-05-01 00:00:00+00","2004-05-02 00:00:00+00","2004-05-03 00:00:00+00","2004-05-04 00:00:00+00","2004-05-05 00:00:00+00","2004-05-06 00:00:00+00","2004-05-07 00:00:00+00","2004-05-08 00:00:00+00","2004-05-09 00:00:00+00","2004-05-10 00:00:00+00","2004-05-11 00:00:00+00","2004-05-12 00:00:00+00","2004-05-13 00:00:00+00","2004-05-14 00:00:00+00","2004-05-15 00:00:00+00","2004-05-16 00:00:00+00","2004-05-17 00:00:00+00","2004-05-18 00:00:00+00","2004-05-19 00:00:00+00","2004-05-20 00:00:00+00","2004-05-21 00:00:00+00","2004-05-22 00:00:00+00","2004-05-23 00:00:00+00","2004-05-24 00:00:00+00","2004-05-25 00:00:00+00","2004-05-26 00:00:00+00","2004-05-27 00:00:00+00","2004-05-28 00:00:00+00","2004-05-29 00:00:00+00","2004-05-30 00:00:00+00","2004-05-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0}	{6_-29}	{1}	2017-10-21 15:03:14.340143+00	2021-08-29 23:12:11.695201+00	2021-08-29 23:12:11.405943+00	1	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C254123FDF0B8D4DC45C1807325294A14254100000000102046C100000000804F224100000000102046C1	{EPSG:3577}	\N
5	year	2004-01-01	1	2004-04-30 14:30:00+00	2004-05-31 14:30:00+00	day	{"2004-05-01 00:00:00+00","2004-05-02 00:00:00+00","2004-05-03 00:00:00+00","2004-05-04 00:00:00+00","2004-05-05 00:00:00+00","2004-05-06 00:00:00+00","2004-05-07 00:00:00+00","2004-05-08 00:00:00+00","2004-05-09 00:00:00+00","2004-05-10 00:00:00+00","2004-05-11 00:00:00+00","2004-05-12 00:00:00+00","2004-05-13 00:00:00+00","2004-05-14 00:00:00+00","2004-05-15 00:00:00+00","2004-05-16 00:00:00+00","2004-05-17 00:00:00+00","2004-05-18 00:00:00+00","2004-05-19 00:00:00+00","2004-05-20 00:00:00+00","2004-05-21 00:00:00+00","2004-05-22 00:00:00+00","2004-05-23 00:00:00+00","2004-05-24 00:00:00+00","2004-05-25 00:00:00+00","2004-05-26 00:00:00+00","2004-05-27 00:00:00+00","2004-05-28 00:00:00+00","2004-05-29 00:00:00+00","2004-05-30 00:00:00+00","2004-05-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}	{NULL}	{1}	2017-10-24 10:01:27.946578+00	2021-08-29 23:12:11.730675+00	2021-08-29 23:12:11.421453+00	1	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C2541307015B592FC45C1D3F3E7965A36254100000000102046C100000000804F224100000000102046C1	{EPSG:3577}	0
5	all	1900-01-01	1	2004-04-30 14:30:00+00	2004-05-31 14:30:00+00	day	{"2004-05-01 00:00:00+00","2004-05-02 00:00:00+00","2004-05-03 00:00:00+00","2004-05-04 00:00:00+00","2004-05-05 00:00:00+00","2004-05-06 00:00:00+00","2004-05-07 00:00:00+00","2004-05-08 00:00:00+00","2004-05-09 00:00:00+00","2004-05-10 00:00:00+00","2004-05-11 00:00:00+00","2004-05-12 00:00:00+00","2004-05-13 00:00:00+00","2004-05-14 00:00:00+00","2004-05-15 00:00:00+00","2004-05-16 00:00:00+00","2004-05-17 00:00:00+00","2004-05-18 00:00:00+00","2004-05-19 00:00:00+00","2004-05-20 00:00:00+00","2004-05-21 00:00:00+00","2004-05-22 00:00:00+00","2004-05-23 00:00:00+00","2004-05-24 00:00:00+00","2004-05-25 00:00:00+00","2004-05-26 00:00:00+00","2004-05-27 00:00:00+00","2004-05-28 00:00:00+00","2004-05-29 00:00:00+00","2004-05-30 00:00:00+00","2004-05-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}	{NULL}	{1}	2017-10-24 10:01:27.946578+00	2021-08-29 23:12:11.738432+00	2021-08-29 23:12:11.421453+00	1	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C2541307015B592FC45C1D3F3E7965A36254100000000102046C100000000804F224100000000102046C1	{EPSG:3577}	0
6	year	2004-01-01	1	2004-04-30 14:30:00+00	2004-05-31 14:30:00+00	day	{"2004-05-01 00:00:00+00","2004-05-02 00:00:00+00","2004-05-03 00:00:00+00","2004-05-04 00:00:00+00","2004-05-05 00:00:00+00","2004-05-06 00:00:00+00","2004-05-07 00:00:00+00","2004-05-08 00:00:00+00","2004-05-09 00:00:00+00","2004-05-10 00:00:00+00","2004-05-11 00:00:00+00","2004-05-12 00:00:00+00","2004-05-13 00:00:00+00","2004-05-14 00:00:00+00","2004-05-15 00:00:00+00","2004-05-16 00:00:00+00","2004-05-17 00:00:00+00","2004-05-18 00:00:00+00","2004-05-19 00:00:00+00","2004-05-20 00:00:00+00","2004-05-21 00:00:00+00","2004-05-22 00:00:00+00","2004-05-23 00:00:00+00","2004-05-24 00:00:00+00","2004-05-25 00:00:00+00","2004-05-26 00:00:00+00","2004-05-27 00:00:00+00","2004-05-28 00:00:00+00","2004-05-29 00:00:00+00","2004-05-30 00:00:00+00","2004-05-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0}	{6_-29}	{1}	2017-10-21 15:03:14.340143+00	2021-08-29 23:12:11.745567+00	2021-08-29 23:12:11.405943+00	1	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C254123FDF0B8D4DC45C1807325294A14254100000000102046C100000000804F224100000000102046C1	{EPSG:3577}	0
6	all	1900-01-01	1	2004-04-30 14:30:00+00	2004-05-31 14:30:00+00	day	{"2004-05-01 00:00:00+00","2004-05-02 00:00:00+00","2004-05-03 00:00:00+00","2004-05-04 00:00:00+00","2004-05-05 00:00:00+00","2004-05-06 00:00:00+00","2004-05-07 00:00:00+00","2004-05-08 00:00:00+00","2004-05-09 00:00:00+00","2004-05-10 00:00:00+00","2004-05-11 00:00:00+00","2004-05-12 00:00:00+00","2004-05-13 00:00:00+00","2004-05-14 00:00:00+00","2004-05-15 00:00:00+00","2004-05-16 00:00:00+00","2004-05-17 00:00:00+00","2004-05-18 00:00:00+00","2004-05-19 00:00:00+00","2004-05-20 00:00:00+00","2004-05-21 00:00:00+00","2004-05-22 00:00:00+00","2004-05-23 00:00:00+00","2004-05-24 00:00:00+00","2004-05-25 00:00:00+00","2004-05-26 00:00:00+00","2004-05-27 00:00:00+00","2004-05-28 00:00:00+00","2004-05-29 00:00:00+00","2004-05-30 00:00:00+00","2004-05-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0}	{6_-29}	{1}	2017-10-21 15:03:14.340143+00	2021-08-29 23:12:11.766948+00	2021-08-29 23:12:11.405943+00	1	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C254123FDF0B8D4DC45C1807325294A14254100000000102046C100000000804F224100000000102046C1	{EPSG:3577}	0
4	year	2021-01-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0}	{55LDE}	{1}	2021-08-29 05:41:02.750914+00	2021-08-29 23:12:11.778557+00	2021-08-29 23:12:11.422116+00	1	0103000020F90D00000100000005000000E0A48B746782384185D7555FD74D37C199A783DF15F537417CBA494D12E838C1DACFB99021543741A1A7A3F4B1D538C1CCE457246F843741BA47CD13813037C1E0A48B746782384185D7555FD74D37C1	{EPSG:32755}	0
4	all	1900-01-01	1	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0}	{55LDE}	{1}	2021-08-29 05:41:02.750914+00	2021-08-29 23:12:11.816413+00	2021-08-29 23:12:11.422116+00	1	0103000020F90D00000100000005000000E0A48B746782384185D7555FD74D37C199A783DF15F537417CBA494D12E838C1DACFB99021543741A1A7A3F4B1D538C1CCE457246F843741BA47CD13813037C1E0A48B746782384185D7555FD74D37C1	{EPSG:32755}	0
7	all	1900-01-01	0	\N	\N	day	{}	{}	{}	{}	\N	2021-08-29 23:12:11.970725+00	2021-08-29 23:12:11.880341+00	0	\N	{}	0
8	month	2018-05-01	1	2018-04-30 14:30:00+00	2018-05-31 14:30:00+00	day	{"2018-05-01 00:00:00+00","2018-05-02 00:00:00+00","2018-05-03 00:00:00+00","2018-05-04 00:00:00+00","2018-05-05 00:00:00+00","2018-05-06 00:00:00+00","2018-05-07 00:00:00+00","2018-05-08 00:00:00+00","2018-05-09 00:00:00+00","2018-05-10 00:00:00+00","2018-05-11 00:00:00+00","2018-05-12 00:00:00+00","2018-05-13 00:00:00+00","2018-05-14 00:00:00+00","2018-05-15 00:00:00+00","2018-05-16 00:00:00+00","2018-05-17 00:00:00+00","2018-05-18 00:00:00+00","2018-05-19 00:00:00+00","2018-05-20 00:00:00+00","2018-05-21 00:00:00+00","2018-05-22 00:00:00+00","2018-05-23 00:00:00+00","2018-05-24 00:00:00+00","2018-05-25 00:00:00+00","2018-05-26 00:00:00+00","2018-05-27 00:00:00+00","2018-05-28 00:00:00+00","2018-05-29 00:00:00+00","2018-05-30 00:00:00+00","2018-05-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0}	{NULL}	{1}	2018-08-04 01:00:38.077435+00	2021-08-29 23:12:12.009419+00	2021-08-29 23:12:11.805118+00	1	0103000020F90D0000010000000600000000000000C05C254100000000102046C1DDBFE8F2B1DA234100000000102046C11ED3E1606C0B2441D823632EC5F445C1051A3B3EE7B6244100000000C05C45C100000000C05C254100000000C05C45C100000000C05C254100000000102046C1	{EPSG:3577}	\N
9	month	2021-06-01	1	2021-05-31 14:30:00+00	2021-06-30 14:30:00+00	day	{"2021-06-01 00:00:00+00","2021-06-02 00:00:00+00","2021-06-03 00:00:00+00","2021-06-04 00:00:00+00","2021-06-05 00:00:00+00","2021-06-06 00:00:00+00","2021-06-07 00:00:00+00","2021-06-08 00:00:00+00","2021-06-09 00:00:00+00","2021-06-10 00:00:00+00","2021-06-11 00:00:00+00","2021-06-12 00:00:00+00","2021-06-13 00:00:00+00","2021-06-14 00:00:00+00","2021-06-15 00:00:00+00","2021-06-16 00:00:00+00","2021-06-17 00:00:00+00","2021-06-18 00:00:00+00","2021-06-19 00:00:00+00","2021-06-20 00:00:00+00","2021-06-21 00:00:00+00","2021-06-22 00:00:00+00","2021-06-23 00:00:00+00","2021-06-24 00:00:00+00","2021-06-25 00:00:00+00","2021-06-26 00:00:00+00","2021-06-27 00:00:00+00","2021-06-28 00:00:00+00","2021-06-29 00:00:00+00","2021-06-30 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1}	{NULL}	{1}	2021-06-30 03:57:49.515075+00	2021-08-29 23:12:12.034791+00	2021-08-29 23:12:11.847418+00	1	0103000020F90D00000100000005000000BA7FB9F7D60D4141056A35E4BDBD48C141415A1377EA404117F64383DF9349C17D0DD8465719404163505CF9787149C1A76E7BB2CD3C404181BF325C439B48C1BA7FB9F7D60D4141056A35E4BDBD48C1	{EPSG:32756}	\N
9	month	2021-07-01	0	2021-06-30 14:30:00+00	2021-07-31 14:30:00+00	day	{"2021-07-01 00:00:00+00","2021-07-02 00:00:00+00","2021-07-03 00:00:00+00","2021-07-04 00:00:00+00","2021-07-05 00:00:00+00","2021-07-06 00:00:00+00","2021-07-07 00:00:00+00","2021-07-08 00:00:00+00","2021-07-09 00:00:00+00","2021-07-10 00:00:00+00","2021-07-11 00:00:00+00","2021-07-12 00:00:00+00","2021-07-13 00:00:00+00","2021-07-14 00:00:00+00","2021-07-15 00:00:00+00","2021-07-16 00:00:00+00","2021-07-17 00:00:00+00","2021-07-18 00:00:00+00","2021-07-19 00:00:00+00","2021-07-20 00:00:00+00","2021-07-21 00:00:00+00","2021-07-22 00:00:00+00","2021-07-23 00:00:00+00","2021-07-24 00:00:00+00","2021-07-25 00:00:00+00","2021-07-26 00:00:00+00","2021-07-27 00:00:00+00","2021-07-28 00:00:00+00","2021-07-29 00:00:00+00","2021-07-30 00:00:00+00","2021-07-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}	{}	{}	\N	2021-08-29 23:12:12.056869+00	2021-08-29 23:12:11.847418+00	0	\N	\N	\N
9	month	2021-08-01	3	2021-07-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0,0}	{NULL}	{3}	2021-08-29 06:13:52.263865+00	2021-08-29 23:12:12.087118+00	2021-08-29 23:12:11.847418+00	3	0106000020F90D00000300000001030000000100000005000000108014CF83DD3F41B88C1A8154E74AC1DB961B5F1F973F417575C7B71BBD4BC1F0904C91B7F33D4175D4C4A7839A4BC1BCED641EA23A3E4193733867BFC44AC1108014CF83DD3F41B88C1A8154E74AC101030000000100000008000000E335B1DFE0B1F7C0F88F70BE112B46C1185393F22213F8C06C08182625A745C1706A3C0B7641F4C0F7D4BF496CA645C1427122DC14AFF4C0A968CBF0D9B745C1882B9D35A553F7C0891A5BA0631E46C15A89DFB7FDA6F7C007327175E92A46C1D964A8AC21AEF7C0E692A036202B46C1E335B1DFE0B1F7C0F88F70BE112B46C1010300000001000000070000006089E710E4714141D75EA3166C8243C17133D6C0E5CC414163C4308997A543C1F01F0F7819E64141C42899830EB043C17A7C7FF4D4CD414192D983F0FD3F44C18683C0F06C2B4141417AB81ECA2444C15998D65C497141414BADF50C888243C16089E710E4714141D75EA3166C8243C1	{EPSG:32756,EPSG:32752}	\N
8	year	2018-01-01	1	2018-04-30 14:30:00+00	2018-05-31 14:30:00+00	day	{"2018-05-01 00:00:00+00","2018-05-02 00:00:00+00","2018-05-03 00:00:00+00","2018-05-04 00:00:00+00","2018-05-05 00:00:00+00","2018-05-06 00:00:00+00","2018-05-07 00:00:00+00","2018-05-08 00:00:00+00","2018-05-09 00:00:00+00","2018-05-10 00:00:00+00","2018-05-11 00:00:00+00","2018-05-12 00:00:00+00","2018-05-13 00:00:00+00","2018-05-14 00:00:00+00","2018-05-15 00:00:00+00","2018-05-16 00:00:00+00","2018-05-17 00:00:00+00","2018-05-18 00:00:00+00","2018-05-19 00:00:00+00","2018-05-20 00:00:00+00","2018-05-21 00:00:00+00","2018-05-22 00:00:00+00","2018-05-23 00:00:00+00","2018-05-24 00:00:00+00","2018-05-25 00:00:00+00","2018-05-26 00:00:00+00","2018-05-27 00:00:00+00","2018-05-28 00:00:00+00","2018-05-29 00:00:00+00","2018-05-30 00:00:00+00","2018-05-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0}	{NULL}	{1}	2018-08-04 01:00:38.077435+00	2021-08-29 23:12:12.092653+00	2021-08-29 23:12:11.805118+00	1	0103000020F90D0000010000000500000000000000C05C254100000000102046C1DDBFE8F2B1DA234100000000102046C1051A3B3EE7B6244100000000C05C45C100000000C05C254100000000C05C45C100000000C05C254100000000102046C1	{EPSG:3577}	0
8	all	1900-01-01	1	2018-04-30 14:30:00+00	2018-05-31 14:30:00+00	day	{"2018-05-01 00:00:00+00","2018-05-02 00:00:00+00","2018-05-03 00:00:00+00","2018-05-04 00:00:00+00","2018-05-05 00:00:00+00","2018-05-06 00:00:00+00","2018-05-07 00:00:00+00","2018-05-08 00:00:00+00","2018-05-09 00:00:00+00","2018-05-10 00:00:00+00","2018-05-11 00:00:00+00","2018-05-12 00:00:00+00","2018-05-13 00:00:00+00","2018-05-14 00:00:00+00","2018-05-15 00:00:00+00","2018-05-16 00:00:00+00","2018-05-17 00:00:00+00","2018-05-18 00:00:00+00","2018-05-19 00:00:00+00","2018-05-20 00:00:00+00","2018-05-21 00:00:00+00","2018-05-22 00:00:00+00","2018-05-23 00:00:00+00","2018-05-24 00:00:00+00","2018-05-25 00:00:00+00","2018-05-26 00:00:00+00","2018-05-27 00:00:00+00","2018-05-28 00:00:00+00","2018-05-29 00:00:00+00","2018-05-30 00:00:00+00","2018-05-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0}	{NULL}	{1}	2018-08-04 01:00:38.077435+00	2021-08-29 23:12:12.102768+00	2021-08-29 23:12:11.805118+00	1	0103000020F90D0000010000000500000000000000C05C254100000000102046C1DDBFE8F2B1DA234100000000102046C1051A3B3EE7B6244100000000C05C45C100000000C05C254100000000C05C45C100000000C05C254100000000102046C1	{EPSG:3577}	0
9	year	2021-01-01	4	2021-05-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-06-01 00:00:00+00","2021-06-02 00:00:00+00","2021-06-03 00:00:00+00","2021-06-04 00:00:00+00","2021-06-05 00:00:00+00","2021-06-06 00:00:00+00","2021-06-07 00:00:00+00","2021-06-08 00:00:00+00","2021-06-09 00:00:00+00","2021-06-10 00:00:00+00","2021-06-11 00:00:00+00","2021-06-12 00:00:00+00","2021-06-13 00:00:00+00","2021-06-14 00:00:00+00","2021-06-15 00:00:00+00","2021-06-16 00:00:00+00","2021-06-17 00:00:00+00","2021-06-18 00:00:00+00","2021-06-19 00:00:00+00","2021-06-20 00:00:00+00","2021-06-21 00:00:00+00","2021-06-22 00:00:00+00","2021-06-23 00:00:00+00","2021-06-24 00:00:00+00","2021-06-25 00:00:00+00","2021-06-26 00:00:00+00","2021-06-27 00:00:00+00","2021-06-28 00:00:00+00","2021-06-29 00:00:00+00","2021-06-30 00:00:00+00","2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0,0}	{NULL}	{4}	2021-08-29 06:13:52.263865+00	2021-08-29 23:12:12.167486+00	2021-08-29 23:12:11.847418+00	4	0106000020F90D00000400000001030000000100000005000000108014CF83DD3F41B88C1A8154E74AC1DB961B5F1F973F417575C7B71BBD4BC1F0904C91B7F33D4175D4C4A7839A4BC1BCED641EA23A3E4193733867BFC44AC1108014CF83DD3F41B88C1A8154E74AC101030000000100000005000000BA7FB9F7D60D4141056A35E4BDBD48C141415A1377EA404117F64383DF9349C17D0DD8465719404163505CF9787149C1A76E7BB2CD3C404181BF325C439B48C1BA7FB9F7D60D4141056A35E4BDBD48C101030000000100000005000000E335B1DFE0B1F7C0F88F70BE112B46C1185393F22213F8C06C08182625A745C1706A3C0B7641F4C0F7D4BF496CA645C1882B9D35A553F7C0891A5BA0631E46C1E335B1DFE0B1F7C0F88F70BE112B46C1010300000001000000050000006089E710E4714141D75EA3166C8243C1F01F0F7819E64141C42899830EB043C17A7C7FF4D4CD414192D983F0FD3F44C18683C0F06C2B4141417AB81ECA2444C16089E710E4714141D75EA3166C8243C1	{EPSG:32756,EPSG:32752}	0
9	all	1900-01-01	4	2021-05-31 14:30:00+00	2021-08-31 14:30:00+00	day	{"2021-06-01 00:00:00+00","2021-06-02 00:00:00+00","2021-06-03 00:00:00+00","2021-06-04 00:00:00+00","2021-06-05 00:00:00+00","2021-06-06 00:00:00+00","2021-06-07 00:00:00+00","2021-06-08 00:00:00+00","2021-06-09 00:00:00+00","2021-06-10 00:00:00+00","2021-06-11 00:00:00+00","2021-06-12 00:00:00+00","2021-06-13 00:00:00+00","2021-06-14 00:00:00+00","2021-06-15 00:00:00+00","2021-06-16 00:00:00+00","2021-06-17 00:00:00+00","2021-06-18 00:00:00+00","2021-06-19 00:00:00+00","2021-06-20 00:00:00+00","2021-06-21 00:00:00+00","2021-06-22 00:00:00+00","2021-06-23 00:00:00+00","2021-06-24 00:00:00+00","2021-06-25 00:00:00+00","2021-06-26 00:00:00+00","2021-06-27 00:00:00+00","2021-06-28 00:00:00+00","2021-06-29 00:00:00+00","2021-06-30 00:00:00+00","2021-08-01 00:00:00+00","2021-08-02 00:00:00+00","2021-08-03 00:00:00+00","2021-08-04 00:00:00+00","2021-08-05 00:00:00+00","2021-08-06 00:00:00+00","2021-08-07 00:00:00+00","2021-08-08 00:00:00+00","2021-08-09 00:00:00+00","2021-08-10 00:00:00+00","2021-08-11 00:00:00+00","2021-08-12 00:00:00+00","2021-08-13 00:00:00+00","2021-08-14 00:00:00+00","2021-08-15 00:00:00+00","2021-08-16 00:00:00+00","2021-08-17 00:00:00+00","2021-08-18 00:00:00+00","2021-08-19 00:00:00+00","2021-08-20 00:00:00+00","2021-08-21 00:00:00+00","2021-08-22 00:00:00+00","2021-08-23 00:00:00+00","2021-08-24 00:00:00+00","2021-08-25 00:00:00+00","2021-08-26 00:00:00+00","2021-08-27 00:00:00+00","2021-08-28 00:00:00+00","2021-08-29 00:00:00+00","2021-08-30 00:00:00+00","2021-08-31 00:00:00+00"}	{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0,0}	{NULL}	{4}	2021-08-29 06:13:52.263865+00	2021-08-29 23:12:12.186269+00	2021-08-29 23:12:11.847418+00	4	0106000020F90D00000400000001030000000100000005000000108014CF83DD3F41B88C1A8154E74AC1DB961B5F1F973F417575C7B71BBD4BC1F0904C91B7F33D4175D4C4A7839A4BC1BCED641EA23A3E4193733867BFC44AC1108014CF83DD3F41B88C1A8154E74AC101030000000100000005000000BA7FB9F7D60D4141056A35E4BDBD48C141415A1377EA404117F64383DF9349C17D0DD8465719404163505CF9787149C1A76E7BB2CD3C404181BF325C439B48C1BA7FB9F7D60D4141056A35E4BDBD48C101030000000100000005000000E335B1DFE0B1F7C0F88F70BE112B46C1185393F22213F8C06C08182625A745C1706A3C0B7641F4C0F7D4BF496CA645C1882B9D35A553F7C0891A5BA0631E46C1E335B1DFE0B1F7C0F88F70BE112B46C1010300000001000000050000006089E710E4714141D75EA3166C8243C1F01F0F7819E64141C42899830EB043C17A7C7FF4D4CD414192D983F0FD3F44C18683C0F06C2B4141417AB81ECA2444C16089E710E4714141D75EA3166C8243C1	{EPSG:32756,EPSG:32752}	0
10	month	2004-05-01	1	2004-04-30 14:30:00+00	2004-05-31 14:30:00+00	day	{"2004-05-01 00:00:00+00","2004-05-02 00:00:00+00","2004-05-03 00:00:00+00","2004-05-04 00:00:00+00","2004-05-05 00:00:00+00","2004-05-06 00:00:00+00","2004-05-07 00:00:00+00","2004-05-08 00:00:00+00","2004-05-09 00:00:00+00","2004-05-10 00:00:00+00","2004-05-11 00:00:00+00","2004-05-12 00:00:00+00","2004-05-13 00:00:00+00","2004-05-14 00:00:00+00","2004-05-15 00:00:00+00","2004-05-16 00:00:00+00","2004-05-17 00:00:00+00","2004-05-18 00:00:00+00","2004-05-19 00:00:00+00","2004-05-20 00:00:00+00","2004-05-21 00:00:00+00","2004-05-22 00:00:00+00","2004-05-23 00:00:00+00","2004-05-24 00:00:00+00","2004-05-25 00:00:00+00","2004-05-26 00:00:00+00","2004-05-27 00:00:00+00","2004-05-28 00:00:00+00","2004-05-29 00:00:00+00","2004-05-30 00:00:00+00","2004-05-31 00:00:00+00"}	{0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}	{6_-29}	{1}	2018-05-20 08:30:52.436405+00	2021-08-29 23:12:12.230224+00	2021-08-29 23:12:12.016571+00	1	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C25412EF0E81E6DC345C196446B5FBEF8244100000000102046C100000000804F224100000000102046C1	{EPSG:3577}	\N
10	year	2004-01-01	1	2004-04-30 14:30:00+00	2004-05-31 14:30:00+00	day	{"2004-05-01 00:00:00+00","2004-05-02 00:00:00+00","2004-05-03 00:00:00+00","2004-05-04 00:00:00+00","2004-05-05 00:00:00+00","2004-05-06 00:00:00+00","2004-05-07 00:00:00+00","2004-05-08 00:00:00+00","2004-05-09 00:00:00+00","2004-05-10 00:00:00+00","2004-05-11 00:00:00+00","2004-05-12 00:00:00+00","2004-05-13 00:00:00+00","2004-05-14 00:00:00+00","2004-05-15 00:00:00+00","2004-05-16 00:00:00+00","2004-05-17 00:00:00+00","2004-05-18 00:00:00+00","2004-05-19 00:00:00+00","2004-05-20 00:00:00+00","2004-05-21 00:00:00+00","2004-05-22 00:00:00+00","2004-05-23 00:00:00+00","2004-05-24 00:00:00+00","2004-05-25 00:00:00+00","2004-05-26 00:00:00+00","2004-05-27 00:00:00+00","2004-05-28 00:00:00+00","2004-05-29 00:00:00+00","2004-05-30 00:00:00+00","2004-05-31 00:00:00+00"}	{0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}	{6_-29}	{1}	2018-05-20 08:30:52.436405+00	2021-08-29 23:12:12.268421+00	2021-08-29 23:12:12.016571+00	1	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C25412EF0E81E6DC345C196446B5FBEF8244100000000102046C100000000804F224100000000102046C1	{EPSG:3577}	0
10	all	1900-01-01	1	2004-04-30 14:30:00+00	2004-05-31 14:30:00+00	day	{"2004-05-01 00:00:00+00","2004-05-02 00:00:00+00","2004-05-03 00:00:00+00","2004-05-04 00:00:00+00","2004-05-05 00:00:00+00","2004-05-06 00:00:00+00","2004-05-07 00:00:00+00","2004-05-08 00:00:00+00","2004-05-09 00:00:00+00","2004-05-10 00:00:00+00","2004-05-11 00:00:00+00","2004-05-12 00:00:00+00","2004-05-13 00:00:00+00","2004-05-14 00:00:00+00","2004-05-15 00:00:00+00","2004-05-16 00:00:00+00","2004-05-17 00:00:00+00","2004-05-18 00:00:00+00","2004-05-19 00:00:00+00","2004-05-20 00:00:00+00","2004-05-21 00:00:00+00","2004-05-22 00:00:00+00","2004-05-23 00:00:00+00","2004-05-24 00:00:00+00","2004-05-25 00:00:00+00","2004-05-26 00:00:00+00","2004-05-27 00:00:00+00","2004-05-28 00:00:00+00","2004-05-29 00:00:00+00","2004-05-30 00:00:00+00","2004-05-31 00:00:00+00"}	{0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}	{6_-29}	{1}	2018-05-20 08:30:52.436405+00	2021-08-29 23:12:12.275735+00	2021-08-29 23:12:12.016571+00	1	0103000020F90D0000010000000600000000000000804F224100000000102046C100000000804F224100000000C05C45C100000000C05C254100000000C05C45C100000000C05C25412EF0E81E6DC345C196446B5FBEF8244100000000102046C100000000804F224100000000102046C1	{EPSG:3577}	0
\.


--
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) FROM stdin;
\.


--
-- Name: dataset_location_id_seq; Type: SEQUENCE SET; Schema: agdc; Owner: agdc_admin
--

SELECT pg_catalog.setval('agdc.dataset_location_id_seq', 14, true);


--
-- Name: dataset_type_id_seq; Type: SEQUENCE SET; Schema: agdc; Owner: agdc_admin
--

SELECT pg_catalog.setval('agdc.dataset_type_id_seq', 10, true);


--
-- Name: metadata_type_id_seq; Type: SEQUENCE SET; Schema: agdc; Owner: agdc_admin
--

SELECT pg_catalog.setval('agdc.metadata_type_id_seq', 5, true);


--
-- Name: product_id_seq; Type: SEQUENCE SET; Schema: cubedash; Owner: opendatacubeusername
--

SELECT pg_catalog.setval('cubedash.product_id_seq', 10, true);


--
-- Name: dataset pk_dataset; Type: CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset
    ADD CONSTRAINT pk_dataset PRIMARY KEY (id);


--
-- Name: dataset_location pk_dataset_location; Type: CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_location
    ADD CONSTRAINT pk_dataset_location PRIMARY KEY (id);


--
-- Name: dataset_source pk_dataset_source; Type: CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_source
    ADD CONSTRAINT pk_dataset_source PRIMARY KEY (dataset_ref, classifier);


--
-- Name: dataset_type pk_dataset_type; Type: CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_type
    ADD CONSTRAINT pk_dataset_type PRIMARY KEY (id);


--
-- Name: metadata_type pk_metadata_type; Type: CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.metadata_type
    ADD CONSTRAINT pk_metadata_type PRIMARY KEY (id);


--
-- Name: dataset_location uq_dataset_location_uri_scheme; Type: CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_location
    ADD CONSTRAINT uq_dataset_location_uri_scheme UNIQUE (uri_scheme, uri_body, dataset_ref);


--
-- Name: dataset_source uq_dataset_source_source_dataset_ref; Type: CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_source
    ADD CONSTRAINT uq_dataset_source_source_dataset_ref UNIQUE (source_dataset_ref, dataset_ref);


--
-- Name: dataset_type uq_dataset_type_name; Type: CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_type
    ADD CONSTRAINT uq_dataset_type_name UNIQUE (name);


--
-- Name: metadata_type uq_metadata_type_name; Type: CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.metadata_type
    ADD CONSTRAINT uq_metadata_type_name UNIQUE (name);


--
-- Name: dataset_spatial dataset_spatial_pkey; Type: CONSTRAINT; Schema: cubedash; Owner: opendatacubeusername
--

ALTER TABLE ONLY cubedash.dataset_spatial
    ADD CONSTRAINT dataset_spatial_pkey PRIMARY KEY (id);


--
-- Name: product product_name_key; Type: CONSTRAINT; Schema: cubedash; Owner: opendatacubeusername
--

ALTER TABLE ONLY cubedash.product
    ADD CONSTRAINT product_name_key UNIQUE (name);


--
-- Name: product product_pkey; Type: CONSTRAINT; Schema: cubedash; Owner: opendatacubeusername
--

ALTER TABLE ONLY cubedash.product
    ADD CONSTRAINT product_pkey PRIMARY KEY (id);


--
-- Name: region region_pkey; Type: CONSTRAINT; Schema: cubedash; Owner: opendatacubeusername
--

ALTER TABLE ONLY cubedash.region
    ADD CONSTRAINT region_pkey PRIMARY KEY (dataset_type_ref, region_code);


--
-- Name: time_overview time_overview_pkey; Type: CONSTRAINT; Schema: cubedash; Owner: opendatacubeusername
--

ALTER TABLE ONLY cubedash.time_overview
    ADD CONSTRAINT time_overview_pkey PRIMARY KEY (product_ref, start_day, period_type);


--
-- Name: dix_ga_ls7e_ard_provisional_3_cloud_cover; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_cloud_cover ON agdc.dataset USING btree ((((metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_ls7e_ard_provisional_3_dataset_maturity; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_dataset_maturity ON agdc.dataset USING btree (((metadata #>> '{properties,dea:dataset_maturity}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_ls7e_ard_provisional_3_gqa; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_gqa ON agdc.dataset USING btree ((((metadata #>> '{properties,gqa:cep90}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_ls7e_ard_provisional_3_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_ls7e_ard_provisional_3_region_code; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_region_code ON agdc.dataset USING btree (((metadata #>> '{properties,odc:region_code}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_ls7e_ard_provisional_3_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text), agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_ls8c_ard_provisional_3_cloud_cover; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_cloud_cover ON agdc.dataset USING btree ((((metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: dix_ga_ls8c_ard_provisional_3_dataset_maturity; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_dataset_maturity ON agdc.dataset USING btree (((metadata #>> '{properties,dea:dataset_maturity}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: dix_ga_ls8c_ard_provisional_3_gqa; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_gqa ON agdc.dataset USING btree ((((metadata #>> '{properties,gqa:cep90}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: dix_ga_ls8c_ard_provisional_3_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: dix_ga_ls8c_ard_provisional_3_region_code; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_region_code ON agdc.dataset USING btree (((metadata #>> '{properties,odc:region_code}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: dix_ga_ls8c_ard_provisional_3_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text), agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: dix_ga_s2am_ard_provisional_3_cloud_cover; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_cloud_cover ON agdc.dataset USING btree ((((metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 5));


--
-- Name: dix_ga_s2am_ard_provisional_3_dataset_maturity; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_dataset_maturity ON agdc.dataset USING btree (((metadata #>> '{properties,dea:dataset_maturity}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 5));


--
-- Name: dix_ga_s2am_ard_provisional_3_gqa; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_gqa ON agdc.dataset USING btree ((((metadata #>> '{properties,gqa:cep90}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 5));


--
-- Name: dix_ga_s2am_ard_provisional_3_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 5));


--
-- Name: dix_ga_s2am_ard_provisional_3_region_code; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_region_code ON agdc.dataset USING btree (((metadata #>> '{properties,odc:region_code}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 5));


--
-- Name: dix_ga_s2am_ard_provisional_3_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text), agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 5));


--
-- Name: dix_ga_s2bm_ard_provisional_3_cloud_cover; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_cloud_cover ON agdc.dataset USING btree ((((metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 6));


--
-- Name: dix_ga_s2bm_ard_provisional_3_dataset_maturity; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_dataset_maturity ON agdc.dataset USING btree (((metadata #>> '{properties,dea:dataset_maturity}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 6));


--
-- Name: dix_ga_s2bm_ard_provisional_3_gqa; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_gqa ON agdc.dataset USING btree ((((metadata #>> '{properties,gqa:cep90}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 6));


--
-- Name: dix_ga_s2bm_ard_provisional_3_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 6));


--
-- Name: dix_ga_s2bm_ard_provisional_3_region_code; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_region_code ON agdc.dataset USING btree (((metadata #>> '{properties,odc:region_code}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 6));


--
-- Name: dix_ga_s2bm_ard_provisional_3_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text), agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 6));


--
-- Name: dix_ls5_fc_albers_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ls5_fc_albers_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 8));


--
-- Name: dix_ls5_fc_albers_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ls5_fc_albers_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 8));


--
-- Name: dix_ls7_fc_albers_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ls7_fc_albers_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 10));


--
-- Name: dix_ls7_fc_albers_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ls7_fc_albers_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 10));


--
-- Name: dix_ls8_fc_albers_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ls8_fc_albers_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 9));


--
-- Name: dix_ls8_fc_albers_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ls8_fc_albers_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 9));


--
-- Name: dix_s2a_nrt_granule_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_s2a_nrt_granule_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text), tstzrange(agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[])), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 1));


--
-- Name: dix_s2a_nrt_granule_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_s2a_nrt_granule_time_lat_lon ON agdc.dataset USING gist (tstzrange(agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[])), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 1));


--
-- Name: dix_s2b_nrt_granule_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_s2b_nrt_granule_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text), tstzrange(agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[])), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 2));


--
-- Name: dix_s2b_nrt_granule_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_s2b_nrt_granule_time_lat_lon ON agdc.dataset USING gist (tstzrange(agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[])), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 2));


--
-- Name: dix_wofs_albers_instrument; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_wofs_albers_instrument ON agdc.dataset USING btree (((metadata #>> '{instrument,name}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 7));


--
-- Name: dix_wofs_albers_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_wofs_albers_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 7));


--
-- Name: dix_wofs_albers_platform; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_wofs_albers_platform ON agdc.dataset USING btree (((metadata #>> '{platform,code}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 7));


--
-- Name: dix_wofs_albers_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_wofs_albers_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{extent,from_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{extent,to_dt}'::text[])), agdc.common_timestamp((metadata #>> '{extent,center_dt}'::text[]))), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ur,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ul,lat}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lat}'::text[]))::double precision), '[]'::text), agdc.float8range(LEAST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), GREATEST(((metadata #>> '{extent,coord,ul,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ur,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,ll,lon}'::text[]))::double precision, ((metadata #>> '{extent,coord,lr,lon}'::text[]))::double precision), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 7));


--
-- Name: ix_agdc_dataset_dataset_type_ref; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX ix_agdc_dataset_dataset_type_ref ON agdc.dataset USING btree (dataset_type_ref);


--
-- Name: ix_agdc_dataset_location_dataset_ref; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX ix_agdc_dataset_location_dataset_ref ON agdc.dataset_location USING btree (dataset_ref);


--
-- Name: ix_dataset_added; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX ix_dataset_added ON agdc.dataset USING btree (added DESC);


--
-- Name: ix_dataset_type_changed; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX ix_dataset_type_changed ON agdc.dataset USING btree (dataset_type_ref, GREATEST(added, updated, archived) DESC);


--
-- Name: dataset_spatial_all_collections_order_idx; Type: INDEX; Schema: cubedash; Owner: opendatacubeusername
--

CREATE INDEX dataset_spatial_all_collections_order_idx ON cubedash.dataset_spatial USING btree (center_time, id) WHERE (footprint IS NOT NULL);


--
-- Name: dataset_spatial_collection_items_idx; Type: INDEX; Schema: cubedash; Owner: opendatacubeusername
--

CREATE INDEX dataset_spatial_collection_items_idx ON cubedash.dataset_spatial USING btree (dataset_type_ref, center_time, id) WHERE (footprint IS NOT NULL);


--
-- Name: dataset_spatial_dataset_type_ref_center_time_idx; Type: INDEX; Schema: cubedash; Owner: opendatacubeusername
--

CREATE INDEX dataset_spatial_dataset_type_ref_center_time_idx ON cubedash.dataset_spatial USING btree (dataset_type_ref, center_time);


--
-- Name: dataset_spatial_dataset_type_ref_region_code_idx; Type: INDEX; Schema: cubedash; Owner: opendatacubeusername
--

CREATE INDEX dataset_spatial_dataset_type_ref_region_code_idx ON cubedash.dataset_spatial USING btree (dataset_type_ref, region_code text_pattern_ops);


--
-- Name: dataset_spatial_footprint_wrs86_idx; Type: INDEX; Schema: cubedash; Owner: opendatacubeusername
--

CREATE INDEX dataset_spatial_footprint_wrs86_idx ON cubedash.dataset_spatial USING gist (public.st_transform(footprint, 4326));


--
-- Name: mv_dataset_spatial_quality_dataset_type_ref; Type: INDEX; Schema: cubedash; Owner: opendatacubeusername
--

CREATE UNIQUE INDEX mv_dataset_spatial_quality_dataset_type_ref ON cubedash.mv_dataset_spatial_quality USING btree (dataset_type_ref);


--
-- Name: mv_spatial_ref_sys_lower_auth_srid_idx; Type: INDEX; Schema: cubedash; Owner: opendatacubeusername
--

CREATE UNIQUE INDEX mv_spatial_ref_sys_lower_auth_srid_idx ON cubedash.mv_spatial_ref_sys USING btree (lower((auth_name)::text), auth_srid);


--
-- Name: mv_spatial_ref_sys_srid_idx; Type: INDEX; Schema: cubedash; Owner: opendatacubeusername
--

CREATE UNIQUE INDEX mv_spatial_ref_sys_srid_idx ON cubedash.mv_spatial_ref_sys USING btree (srid);


--
-- Name: dataset row_update_time_dataset; Type: TRIGGER; Schema: agdc; Owner: agdc_admin
--

CREATE TRIGGER row_update_time_dataset BEFORE UPDATE ON agdc.dataset FOR EACH ROW EXECUTE FUNCTION agdc.set_row_update_time();


--
-- Name: dataset_type row_update_time_dataset_type; Type: TRIGGER; Schema: agdc; Owner: agdc_admin
--

CREATE TRIGGER row_update_time_dataset_type BEFORE UPDATE ON agdc.dataset_type FOR EACH ROW EXECUTE FUNCTION agdc.set_row_update_time();


--
-- Name: metadata_type row_update_time_metadata_type; Type: TRIGGER; Schema: agdc; Owner: agdc_admin
--

CREATE TRIGGER row_update_time_metadata_type BEFORE UPDATE ON agdc.metadata_type FOR EACH ROW EXECUTE FUNCTION agdc.set_row_update_time();


--
-- Name: dataset fk_dataset_dataset_type_ref_dataset_type; Type: FK CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset
    ADD CONSTRAINT fk_dataset_dataset_type_ref_dataset_type FOREIGN KEY (dataset_type_ref) REFERENCES agdc.dataset_type(id);


--
-- Name: dataset_location fk_dataset_location_dataset_ref_dataset; Type: FK CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_location
    ADD CONSTRAINT fk_dataset_location_dataset_ref_dataset FOREIGN KEY (dataset_ref) REFERENCES agdc.dataset(id);


--
-- Name: dataset fk_dataset_metadata_type_ref_metadata_type; Type: FK CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset
    ADD CONSTRAINT fk_dataset_metadata_type_ref_metadata_type FOREIGN KEY (metadata_type_ref) REFERENCES agdc.metadata_type(id);


--
-- Name: dataset_source fk_dataset_source_dataset_ref_dataset; Type: FK CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_source
    ADD CONSTRAINT fk_dataset_source_dataset_ref_dataset FOREIGN KEY (dataset_ref) REFERENCES agdc.dataset(id);


--
-- Name: dataset_source fk_dataset_source_source_dataset_ref_dataset; Type: FK CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_source
    ADD CONSTRAINT fk_dataset_source_source_dataset_ref_dataset FOREIGN KEY (source_dataset_ref) REFERENCES agdc.dataset(id);


--
-- Name: dataset_type fk_dataset_type_metadata_type_ref_metadata_type; Type: FK CONSTRAINT; Schema: agdc; Owner: agdc_admin
--

ALTER TABLE ONLY agdc.dataset_type
    ADD CONSTRAINT fk_dataset_type_metadata_type_ref_metadata_type FOREIGN KEY (metadata_type_ref) REFERENCES agdc.metadata_type(id);


--
-- Name: time_overview time_overview_product_ref_fkey; Type: FK CONSTRAINT; Schema: cubedash; Owner: opendatacubeusername
--

ALTER TABLE ONLY cubedash.time_overview
    ADD CONSTRAINT time_overview_product_ref_fkey FOREIGN KEY (product_ref) REFERENCES cubedash.product(id);


--
-- Name: SCHEMA agdc; Type: ACL; Schema: -; Owner: agdc_admin
--

GRANT USAGE ON SCHEMA agdc TO agdc_user;
GRANT CREATE ON SCHEMA agdc TO agdc_manage;


--
-- Name: FUNCTION common_timestamp(text); Type: ACL; Schema: agdc; Owner: agdc_admin
--

GRANT ALL ON FUNCTION agdc.common_timestamp(text) TO agdc_user;


--
-- Name: TABLE dataset; Type: ACL; Schema: agdc; Owner: agdc_admin
--

GRANT SELECT ON TABLE agdc.dataset TO agdc_user;
GRANT INSERT ON TABLE agdc.dataset TO agdc_ingest;


--
-- Name: TABLE dataset_location; Type: ACL; Schema: agdc; Owner: agdc_admin
--

GRANT SELECT ON TABLE agdc.dataset_location TO agdc_user;
GRANT INSERT ON TABLE agdc.dataset_location TO agdc_ingest;


--
-- Name: SEQUENCE dataset_location_id_seq; Type: ACL; Schema: agdc; Owner: agdc_admin
--

GRANT SELECT,USAGE ON SEQUENCE agdc.dataset_location_id_seq TO agdc_ingest;


--
-- Name: TABLE dataset_source; Type: ACL; Schema: agdc; Owner: agdc_admin
--

GRANT SELECT ON TABLE agdc.dataset_source TO agdc_user;
GRANT INSERT ON TABLE agdc.dataset_source TO agdc_ingest;


--
-- Name: TABLE dataset_type; Type: ACL; Schema: agdc; Owner: agdc_admin
--

GRANT SELECT ON TABLE agdc.dataset_type TO agdc_user;
GRANT INSERT,DELETE ON TABLE agdc.dataset_type TO agdc_manage;


--
-- Name: SEQUENCE dataset_type_id_seq; Type: ACL; Schema: agdc; Owner: agdc_admin
--

GRANT SELECT,USAGE ON SEQUENCE agdc.dataset_type_id_seq TO agdc_ingest;


--
-- Name: TABLE metadata_type; Type: ACL; Schema: agdc; Owner: agdc_admin
--

GRANT SELECT ON TABLE agdc.metadata_type TO agdc_user;
GRANT INSERT,DELETE ON TABLE agdc.metadata_type TO agdc_manage;


--
-- Name: SEQUENCE metadata_type_id_seq; Type: ACL; Schema: agdc; Owner: agdc_admin
--

GRANT SELECT,USAGE ON SEQUENCE agdc.metadata_type_id_seq TO agdc_ingest;


--
-- Name: mv_dataset_spatial_quality; Type: MATERIALIZED VIEW DATA; Schema: cubedash; Owner: opendatacubeusername
--

REFRESH MATERIALIZED VIEW cubedash.mv_dataset_spatial_quality;


--
-- Name: mv_spatial_ref_sys; Type: MATERIALIZED VIEW DATA; Schema: cubedash; Owner: opendatacubeusername
--

REFRESH MATERIALIZED VIEW cubedash.mv_spatial_ref_sys;


--
-- PostgreSQL database dump complete
--
