--
-- PostgreSQL database dump
--

-- Dumped from database version 13.4 (Debian 13.4-1.pgdg110+1)
-- Dumped by pg_dump version 13.4 (Debian 13.4-1.pgdg110+1)

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
-- Name: pg_cron; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA public;


--
-- Name: EXTENSION pg_cron; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_cron IS 'Job scheduler for PostgreSQL';


--
-- Name: topology; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA topology;


ALTER SCHEMA topology OWNER TO postgres;

--
-- Name: SCHEMA topology; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA topology IS 'PostGIS Topology schema';


--
-- Name: hstore; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS hstore WITH SCHEMA public;


--
-- Name: EXTENSION hstore; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION hstore IS 'data type for storing sets of (key, value) pairs';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: pgrouting; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgrouting WITH SCHEMA public;


--
-- Name: EXTENSION pgrouting; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgrouting IS 'pgRouting Extension';


--
-- Name: postgis_raster; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_raster WITH SCHEMA public;


--
-- Name: EXTENSION postgis_raster; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_raster IS 'PostGIS raster types and functions';


--
-- Name: postgis_topology; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;


--
-- Name: EXTENSION postgis_topology; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_topology IS 'PostGIS topology spatial types and functions';


--
-- Name: float8range; Type: TYPE; Schema: agdc; Owner: agdc_admin
--

CREATE TYPE agdc.float8range AS RANGE (
    subtype = double precision,
    subtype_diff = float8mi
);


ALTER TYPE agdc.float8range OWNER TO agdc_admin;

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
-- Name: set_row_update_time(); Type: FUNCTION; Schema: agdc; Owner: agdc_admin
--

CREATE FUNCTION agdc.set_row_update_time() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
begin
  new.updated = now();
  return new;
end;
$$;


ALTER FUNCTION agdc.set_row_update_time() OWNER TO agdc_admin;

--
-- Name: asbinary(public.geometry); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.asbinary(public.geometry) RETURNS bytea
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/postgis-3', 'LWGEOM_asBinary';


ALTER FUNCTION public.asbinary(public.geometry) OWNER TO postgres;

--
-- Name: asbinary(public.geometry, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.asbinary(public.geometry, text) RETURNS bytea
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/postgis-3', 'LWGEOM_asBinary';


ALTER FUNCTION public.asbinary(public.geometry, text) OWNER TO postgres;

--
-- Name: astext(public.geometry); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.astext(public.geometry) RETURNS text
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/postgis-3', 'LWGEOM_asText';


ALTER FUNCTION public.astext(public.geometry) OWNER TO postgres;

--
-- Name: estimated_extent(text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.estimated_extent(text, text) RETURNS public.box2d
    LANGUAGE c IMMUTABLE STRICT SECURITY DEFINER
    AS '$libdir/postgis-3', 'geometry_estimated_extent';


ALTER FUNCTION public.estimated_extent(text, text) OWNER TO postgres;

--
-- Name: estimated_extent(text, text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.estimated_extent(text, text, text) RETURNS public.box2d
    LANGUAGE c IMMUTABLE STRICT SECURITY DEFINER
    AS '$libdir/postgis-3', 'geometry_estimated_extent';


ALTER FUNCTION public.estimated_extent(text, text, text) OWNER TO postgres;

--
-- Name: geomfromtext(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.geomfromtext(text) RETURNS public.geometry
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$SELECT ST_GeomFromText($1)$_$;


ALTER FUNCTION public.geomfromtext(text) OWNER TO postgres;

--
-- Name: geomfromtext(text, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.geomfromtext(text, integer) RETURNS public.geometry
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$SELECT ST_GeomFromText($1, $2)$_$;


ALTER FUNCTION public.geomfromtext(text, integer) OWNER TO postgres;

--
-- Name: ndims(public.geometry); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.ndims(public.geometry) RETURNS smallint
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/postgis-3', 'LWGEOM_ndims';


ALTER FUNCTION public.ndims(public.geometry) OWNER TO postgres;

--
-- Name: setsrid(public.geometry, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.setsrid(public.geometry, integer) RETURNS public.geometry
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/postgis-3', 'LWGEOM_set_srid';


ALTER FUNCTION public.setsrid(public.geometry, integer) OWNER TO postgres;

--
-- Name: srid(public.geometry); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.srid(public.geometry) RETURNS integer
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/postgis-3', 'LWGEOM_get_srid';


ALTER FUNCTION public.srid(public.geometry) OWNER TO postgres;

--
-- Name: st_asbinary(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.st_asbinary(text) RETURNS bytea
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$ SELECT ST_AsBinary($1::geometry);$_$;


ALTER FUNCTION public.st_asbinary(text) OWNER TO postgres;

--
-- Name: st_astext(bytea); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.st_astext(bytea) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$ SELECT ST_AsText($1::geometry);$_$;


ALTER FUNCTION public.st_astext(bytea) OWNER TO postgres;

--
-- Name: gist_geometry_ops; Type: OPERATOR FAMILY; Schema: public; Owner: postgres
--

CREATE OPERATOR FAMILY public.gist_geometry_ops USING gist;


ALTER OPERATOR FAMILY public.gist_geometry_ops USING gist OWNER TO postgres;

--
-- Name: gist_geometry_ops; Type: OPERATOR CLASS; Schema: public; Owner: postgres
--

CREATE OPERATOR CLASS public.gist_geometry_ops
    FOR TYPE public.geometry USING gist FAMILY public.gist_geometry_ops AS
    STORAGE public.box2df ,
    OPERATOR 1 public.<<(public.geometry,public.geometry) ,
    OPERATOR 2 public.&<(public.geometry,public.geometry) ,
    OPERATOR 3 public.&&(public.geometry,public.geometry) ,
    OPERATOR 4 public.&>(public.geometry,public.geometry) ,
    OPERATOR 5 public.>>(public.geometry,public.geometry) ,
    OPERATOR 6 public.~=(public.geometry,public.geometry) ,
    OPERATOR 7 public.~(public.geometry,public.geometry) ,
    OPERATOR 8 public.@(public.geometry,public.geometry) ,
    OPERATOR 9 public.&<|(public.geometry,public.geometry) ,
    OPERATOR 10 public.<<|(public.geometry,public.geometry) ,
    OPERATOR 11 public.|>>(public.geometry,public.geometry) ,
    OPERATOR 12 public.|&>(public.geometry,public.geometry) ,
    OPERATOR 13 public.<->(public.geometry,public.geometry) FOR ORDER BY pg_catalog.float_ops ,
    OPERATOR 14 public.<#>(public.geometry,public.geometry) FOR ORDER BY pg_catalog.float_ops ,
    FUNCTION 1 (public.geometry, public.geometry) public.geometry_gist_consistent_2d(internal,public.geometry,integer) ,
    FUNCTION 2 (public.geometry, public.geometry) public.geometry_gist_union_2d(bytea,internal) ,
    FUNCTION 3 (public.geometry, public.geometry) public.geometry_gist_compress_2d(internal) ,
    FUNCTION 4 (public.geometry, public.geometry) public.geometry_gist_decompress_2d(internal) ,
    FUNCTION 5 (public.geometry, public.geometry) public.geometry_gist_penalty_2d(internal,internal,internal) ,
    FUNCTION 6 (public.geometry, public.geometry) public.geometry_gist_picksplit_2d(internal,internal) ,
    FUNCTION 7 (public.geometry, public.geometry) public.geometry_gist_same_2d(public.geometry,public.geometry,internal) ,
    FUNCTION 8 (public.geometry, public.geometry) public.geometry_gist_distance_2d(internal,public.geometry,integer);


ALTER OPERATOR CLASS public.gist_geometry_ops USING gist OWNER TO postgres;

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
    ((dataset.metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision AS cloud_cover,
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
    (dataset.metadata #>> '{properties,landsat:landsat_product_id}'::text[]) AS landsat_product_id,
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
  WHERE ((dataset.archived IS NULL) AND (dataset.metadata_type_ref = 4));


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
    (dataset.metadata #>> '{properties,landsat:landsat_product_id}'::text[]) AS landsat_product_id,
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
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 1));


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
    (dataset.metadata #>> '{properties,landsat:landsat_product_id}'::text[]) AS landsat_product_id,
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
  WHERE ((dataset.archived IS NULL) AND (dataset.dataset_type_ref = 2));


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
    (dataset.metadata #>> '{properties,landsat:landsat_product_id}'::text[]) AS landsat_product_id,
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
    (dataset.metadata #>> '{properties,landsat:landsat_product_id}'::text[]) AS landsat_product_id,
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


ALTER TABLE agdc.dv_ga_s2bm_ard_provisional_3_dataset OWNER TO opendatacubeusername;

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
-- Data for Name: dataset; Type: TABLE DATA; Schema: agdc; Owner: agdc_admin
--

COPY agdc.dataset (id, metadata_type_ref, dataset_type_ref, metadata, archived, added, added_by, updated) FROM stdin;
37024e3d-2c35-4055-85dc-df4ed6d967b0	4	1	{"id": "37024e3d-2c35-4055-85dc-df4ed6d967b0", "crs": "epsg:32652", "grids": {"default": {"shape": [7101, 8171], "transform": [30.0, 0.0, 574185.0, 0.0, -30.0, -2452185.0, 0.0, 0.0, 1.0]}, "nbart:panchromatic": {"shape": [14201, 16341], "transform": [15.0, 0.0, 574192.5, 0.0, -15.0, -2452192.5, 0.0, 0.0, 1.0]}}, "label": "ga_ls7e_ard_provisional_3-2-1_104076_2022-08-23_nrt", "extent": {"lat": {"end": -22.17406605876065, "begin": -24.06986283164164}, "lon": {"end": 132.09471012335976, "begin": 129.73346364488773}}, "$schema": "https://schemas.opendatacube.org/dataset", "lineage": {"source_datasets": {}}, "product": {"href": "https://collections.dea.ga.gov.au/product/ga_ls7e_ard_provisional_3", "name": "ga_ls7e_ard_provisional_3"}, "geometry": {"type": "Polygon", "coordinates": [[[614528.9027080537, -2457837.750406792], [615345.791510683, -2454308.1542603164], [615597.8462201493, -2453360.3880549967], [615611.3013631506, -2453351.097968509], [615832.5, -2452522.5], [647274.9851732625, -2457787.7073020088], [812559.988399997, -2485567.7078444622], [812599.4200651109, -2485588.394394707], [812603.9158876796, -2485594.2798351604], [817670.0689144533, -2486445.4313323554], [818498.7534676669, -2487506.6758963712], [816374.2349137607, -2497101.73199951], [777832.0680007687, -2664404.1555031706], [776800.0680303809, -2664644.591817715], [771719.3166911778, -2663790.9006248023], [771695.0340151904, -2663797.2959088576], [574725.7917960675, -2630690.916407865], [574732.7040911425, -2630315.0340151903], [574748.9866931718, -2630238.110651134], [574736.847501974, -2630228.8848658237], [575145.7676660897, -2628248.2568068276], [592245.7690827096, -2554118.2506685993], [612698.6662237544, -2465745.7981378045], [614242.8867289199, -2459059.1158740656], [614528.9027080537, -2457837.750406792]]]}, "properties": {"eo:gsd": 15.0, "datetime": "2022-08-23 23:39:39.529301Z", "gqa:abs_x": 0.31, "gqa:abs_y": 0.36, "gqa:cep90": 0.61, "fmask:snow": 0.000040017609081916345, "gqa:abs_xy": 0.47, "gqa:mean_x": -0.07, "gqa:mean_y": 0.19, "eo:platform": "landsat-7", "fmask:clear": 99.81393145697211, "fmask:cloud": 0.07457948412566476, "fmask:water": 0.0973795169000866, "gqa:mean_xy": 0.2, "gqa:stddev_x": 0.63, "gqa:stddev_y": 0.75, "odc:producer": "ga.gov.au", "eo:instrument": "ETM", "gqa:stddev_xy": 0.98, "eo:cloud_cover": 0.07457948412566476, "eo:sun_azimuth": 63.45249016, "landsat:wrs_row": 76, "odc:file_format": "GeoTIFF", "odc:region_code": "104076", "eo:sun_elevation": 26.3560112, "landsat:wrs_path": 104, "fmask:cloud_shadow": 0.014069524393050422, "odc:product_family": "ard", "odc:dataset_version": "3.2.1", "dea:dataset_maturity": "nrt", "dea:product_maturity": "provisional", "gqa:iterative_mean_x": -0.07, "gqa:iterative_mean_y": 0.21, "gqa:iterative_mean_xy": 0.22, "gqa:iterative_stddev_x": 0.25, "gqa:iterative_stddev_y": 0.21, "gqa:iterative_stddev_xy": 0.33, "odc:processing_datetime": "2022-08-24 07:00:03.140637Z", "gqa:abs_iterative_mean_x": 0.21, "gqa:abs_iterative_mean_y": 0.25, "landsat:landsat_scene_id": "LE71040762022235ASA00", "gqa:abs_iterative_mean_xy": 0.33, "landsat:collection_number": 2, "landsat:landsat_product_id": "LE07_L1TP_104076_20220823_20220824_02_RT", "landsat:collection_category": "RT"}, "accessories": {"checksum:sha1": {"path": "ga_ls7e_ard_provisional_3-2-1_104076_2022-08-23_nrt.sha1"}, "thumbnail:nbart": {"path": "ga_ls7e_nbart_provisional_3-2-1_104076_2022-08-23_nrt_thumbnail.jpg"}, "metadata:processor": {"path": "ga_ls7e_ard_provisional_3-2-1_104076_2022-08-23_nrt.proc-info.yaml"}}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[614528.9027080537, -2457837.750406792], [615345.791510683, -2454308.1542603164], [615597.8462201493, -2453360.3880549967], [615611.3013631506, -2453351.097968509], [615832.5, -2452522.5], [647274.9851732625, -2457787.7073020088], [812559.988399997, -2485567.7078444622], [812599.4200651109, -2485588.394394707], [812603.9158876796, -2485594.2798351604], [817670.0689144533, -2486445.4313323554], [818498.7534676669, -2487506.6758963712], [816374.2349137607, -2497101.73199951], [777832.0680007687, -2664404.1555031706], [776800.0680303809, -2664644.591817715], [771719.3166911778, -2663790.9006248023], [771695.0340151904, -2663797.2959088576], [574725.7917960675, -2630690.916407865], [574732.7040911425, -2630315.0340151903], [574748.9866931718, -2630238.110651134], [574736.847501974, -2630228.8848658237], [575145.7676660897, -2628248.2568068276], [592245.7690827096, -2554118.2506685993], [612698.6662237544, -2465745.7981378045], [614242.8867289199, -2459059.1158740656], [614528.9027080537, -2457837.750406792]]]}, "geo_ref_points": {"ll": {"x": 574185.0, "y": -2665215.0}, "lr": {"x": 819315.0, "y": -2665215.0}, "ul": {"x": 574185.0, "y": -2452185.0}, "ur": {"x": 819315.0, "y": -2452185.0}}, "spatial_reference": "epsg:32652"}}, "measurements": {"oa_fmask": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_fmask.tif"}, "nbart_nir": {"path": "ga_ls7e_nbart_provisional_3-2-1_104076_2022-08-23_nrt_band04.tif"}, "nbart_red": {"path": "ga_ls7e_nbart_provisional_3-2-1_104076_2022-08-23_nrt_band03.tif"}, "nbart_blue": {"path": "ga_ls7e_nbart_provisional_3-2-1_104076_2022-08-23_nrt_band01.tif"}, "nbart_green": {"path": "ga_ls7e_nbart_provisional_3-2-1_104076_2022-08-23_nrt_band02.tif"}, "nbart_swir_1": {"path": "ga_ls7e_nbart_provisional_3-2-1_104076_2022-08-23_nrt_band05.tif"}, "nbart_swir_2": {"path": "ga_ls7e_nbart_provisional_3-2-1_104076_2022-08-23_nrt_band07.tif"}, "oa_time_delta": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_time-delta.tif"}, "oa_solar_zenith": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_solar-zenith.tif"}, "oa_exiting_angle": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_exiting-angle.tif"}, "oa_solar_azimuth": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_solar-azimuth.tif"}, "oa_incident_angle": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_incident-angle.tif"}, "oa_relative_slope": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_relative-slope.tif"}, "oa_satellite_view": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_satellite-view.tif"}, "nbart_panchromatic": {"grid": "nbart:panchromatic", "path": "ga_ls7e_nbart_provisional_3-2-1_104076_2022-08-23_nrt_band08.tif"}, "oa_nbart_contiguity": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_nbart-contiguity.tif"}, "oa_relative_azimuth": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_relative-azimuth.tif"}, "oa_azimuthal_exiting": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_azimuthal-exiting.tif"}, "oa_satellite_azimuth": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_satellite-azimuth.tif"}, "oa_azimuthal_incident": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_azimuthal-incident.tif"}, "oa_combined_terrain_shadow": {"path": "ga_ls7e_oa_provisional_3-2-1_104076_2022-08-23_nrt_combined-terrain-shadow.tif"}}}	\N	2022-09-16 07:55:17.703437+00	opendatacubeusername	\N
6a2fa1fa-4cb5-4366-a186-9f5c8accb775	4	2	{"id": "6a2fa1fa-4cb5-4366-a186-9f5c8accb775", "crs": "epsg:32652", "grids": {"default": {"shape": [7711, 7611], "transform": [30.0, 0.0, 230685.0, 0.0, -30.0, -1962585.0, 0.0, 0.0, 1.0]}, "nbart:panchromatic": {"shape": [15421, 15221], "transform": [15.0, 0.0, 230692.5, 0.0, -15.0, -1962592.5, 0.0, 0.0, 1.0]}}, "label": "ga_ls8c_ard_provisional_3-2-1_107073_2022-08-25_nrt", "extent": {"lat": {"end": -17.739234618925693, "begin": -19.838678186539276}, "lon": {"end": 128.60928444285074, "begin": 126.43841642691646}}, "$schema": "https://schemas.opendatacube.org/dataset", "lineage": {"source_datasets": {}}, "product": {"href": "https://collections.dea.ga.gov.au/product/ga_ls8c_ard_provisional_3", "name": "ga_ls8c_ard_provisional_3"}, "geometry": {"type": "Polygon", "coordinates": [[[231144.6184735896, -2154482.2177769234], [231090.7917960675, -2154470.916407865], [231082.81705628242, -2154394.432237984], [233677.8187145806, -2141974.424311714], [250687.8217532252, -2060899.4098427843], [265732.8251716727, -1989544.3936494782], [271282.8267275764, -1963339.386308239], [271447.5, -1962652.5], [271525.23471754504, -1962662.833773861], [271545.0, -1962645.0], [450021.1803144315, -2000175.6435064503], [458565.0, -2002005.0], [458564.6019158552, -2002006.9006362492], [458662.5, -2002027.5], [418642.1816330843, -2193190.574028298], [418522.1782467748, -2193760.590157216], [418492.5, -2193817.5], [418376.53419219016, -2193793.1519916784], [418088.83607167273, -2193764.3599384804], [231143.7867965644, -2154486.2132034358], [231144.6184735896, -2154482.2177769234]]]}, "properties": {"eo:gsd": 15.0, "datetime": "2022-08-25 01:31:30.623872Z", "gqa:abs_x": 0.35, "gqa:abs_y": 0.17, "gqa:cep90": 0.33, "fmask:snow": 0.0, "gqa:abs_xy": 0.39, "gqa:mean_x": -0.26, "gqa:mean_y": 0.09, "eo:platform": "landsat-8", "fmask:clear": 99.98939121456549, "fmask:cloud": 0.00046402694911389634, "fmask:water": 0.009732290086177169, "gqa:mean_xy": 0.28, "gqa:stddev_x": 2.38, "gqa:stddev_y": 0.24, "odc:producer": "ga.gov.au", "eo:instrument": "OLI_TIRS", "gqa:stddev_xy": 2.39, "eo:cloud_cover": 0.00046402694911389634, "eo:sun_azimuth": 47.55858689, "landsat:wrs_row": 73, "odc:file_format": "GeoTIFF", "odc:region_code": "107073", "eo:sun_elevation": 48.04373848, "landsat:wrs_path": 107, "fmask:cloud_shadow": 0.0004124683992123523, "odc:product_family": "ard", "odc:dataset_version": "3.2.1", "dea:dataset_maturity": "nrt", "dea:product_maturity": "provisional", "gqa:iterative_mean_x": -0.09, "gqa:iterative_mean_y": 0.07, "gqa:iterative_mean_xy": 0.12, "gqa:iterative_stddev_x": 0.15, "gqa:iterative_stddev_y": 0.1, "gqa:iterative_stddev_xy": 0.18, "odc:processing_datetime": "2022-08-25 08:43:49.275907Z", "gqa:abs_iterative_mean_x": 0.14, "gqa:abs_iterative_mean_y": 0.1, "landsat:landsat_scene_id": "LC81070732022237LGN00", "gqa:abs_iterative_mean_xy": 0.17, "landsat:collection_number": 2, "landsat:landsat_product_id": "LC08_L1TP_107073_20220825_20220825_02_RT", "landsat:collection_category": "RT"}, "accessories": {"checksum:sha1": {"path": "ga_ls8c_ard_provisional_3-2-1_107073_2022-08-25_nrt.sha1"}, "thumbnail:nbart": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2022-08-25_nrt_thumbnail.jpg"}, "metadata:processor": {"path": "ga_ls8c_ard_provisional_3-2-1_107073_2022-08-25_nrt.proc-info.yaml"}}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[231144.6184735896, -2154482.2177769234], [231090.7917960675, -2154470.916407865], [231082.81705628242, -2154394.432237984], [233677.8187145806, -2141974.424311714], [250687.8217532252, -2060899.4098427843], [265732.8251716727, -1989544.3936494782], [271282.8267275764, -1963339.386308239], [271447.5, -1962652.5], [271525.23471754504, -1962662.833773861], [271545.0, -1962645.0], [450021.1803144315, -2000175.6435064503], [458565.0, -2002005.0], [458564.6019158552, -2002006.9006362492], [458662.5, -2002027.5], [418642.1816330843, -2193190.574028298], [418522.1782467748, -2193760.590157216], [418492.5, -2193817.5], [418376.53419219016, -2193793.1519916784], [418088.83607167273, -2193764.3599384804], [231143.7867965644, -2154486.2132034358], [231144.6184735896, -2154482.2177769234]]]}, "geo_ref_points": {"ll": {"x": 230685.0, "y": -2193915.0}, "lr": {"x": 459015.0, "y": -2193915.0}, "ul": {"x": 230685.0, "y": -1962585.0}, "ur": {"x": 459015.0, "y": -1962585.0}}, "spatial_reference": "epsg:32652"}}, "measurements": {"oa_fmask": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_fmask.tif"}, "nbart_nir": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2022-08-25_nrt_band05.tif"}, "nbart_red": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2022-08-25_nrt_band04.tif"}, "nbart_blue": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2022-08-25_nrt_band02.tif"}, "nbart_green": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2022-08-25_nrt_band03.tif"}, "nbart_swir_1": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2022-08-25_nrt_band06.tif"}, "nbart_swir_2": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2022-08-25_nrt_band07.tif"}, "oa_time_delta": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_time-delta.tif"}, "oa_solar_zenith": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_solar-zenith.tif"}, "oa_exiting_angle": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_exiting-angle.tif"}, "oa_solar_azimuth": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_solar-azimuth.tif"}, "oa_incident_angle": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_incident-angle.tif"}, "oa_relative_slope": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_relative-slope.tif"}, "oa_satellite_view": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_satellite-view.tif"}, "nbart_panchromatic": {"grid": "nbart:panchromatic", "path": "ga_ls8c_nbart_provisional_3-2-1_107073_2022-08-25_nrt_band08.tif"}, "oa_nbart_contiguity": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_nbart-contiguity.tif"}, "oa_relative_azimuth": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_relative-azimuth.tif"}, "oa_azimuthal_exiting": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_azimuthal-exiting.tif"}, "oa_satellite_azimuth": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_satellite-azimuth.tif"}, "nbart_coastal_aerosol": {"path": "ga_ls8c_nbart_provisional_3-2-1_107073_2022-08-25_nrt_band01.tif"}, "oa_azimuthal_incident": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_azimuthal-incident.tif"}, "oa_combined_terrain_shadow": {"path": "ga_ls8c_oa_provisional_3-2-1_107073_2022-08-25_nrt_combined-terrain-shadow.tif"}}}	\N	2022-09-16 07:55:19.68112+00	opendatacubeusername	\N
a1911fa7-668b-49a0-8231-c950bdaaca4e	4	3	{"id": "a1911fa7-668b-49a0-8231-c950bdaaca4e", "crs": "epsg:32752", "grids": {"20": {"shape": [5490, 5490], "transform": [20.0, 0.0, 799980.0, 0.0, -20.0, 8600020.0, 0.0, 0.0, 1.0]}, "60": {"shape": [1830, 1830], "transform": [60.0, 0.0, 799980.0, 0.0, -60.0, 8600020.0, 0.0, 0.0, 1.0]}, "default": {"shape": [10980, 10980], "transform": [10.0, 0.0, 799980.0, 0.0, -10.0, 8600020.0, 0.0, 0.0, 1.0]}}, "label": "ga_s2am_ard_provisional_3-2-1_52LHL_2022-08-24_nrt", "extent": {"lat": {"end": -12.637300069246544, "begin": -13.641397347306768}, "lon": {"end": 132.78610048463833, "begin": 131.7614908089947}}, "$schema": "https://schemas.opendatacube.org/dataset", "lineage": {"source_datasets": {}}, "product": {"href": "https://collections.dea.ga.gov.au/product/ga_s2am_ard_provisional_3", "name": "ga_s2am_ard_provisional_3"}, "geometry": {"type": "Polygon", "coordinates": [[[799980.0, 8600020.0], [909780.0, 8600020.0], [909780.0, 8490220.0], [799980.0, 8490220.0], [799980.0, 8600020.0]]]}, "properties": {"eo:gsd": 10.0, "datetime": "2022-08-24 01:31:12.306718Z", "gqa:abs_x": 0.31, "gqa:abs_y": 0.22, "gqa:cep90": 0.51, "fmask:snow": 0.09912707655249983, "gqa:abs_xy": 0.38, "gqa:mean_x": 0.24, "gqa:mean_y": 0.03, "eo:platform": "sentinel-2a", "fmask:clear": 99.79400201061046, "fmask:cloud": 0.0, "fmask:water": 0.10687091283705097, "gqa:mean_xy": 0.25, "gqa:stddev_x": 0.41, "gqa:stddev_y": 0.45, "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "gqa:stddev_xy": 0.61, "eo:cloud_cover": 0.0, "eo:sun_azimuth": 47.360850798581, "odc:file_format": "GeoTIFF", "odc:region_code": "52LHL", "eo:constellation": "sentinel-2", "eo:sun_elevation": 35.1155052347735, "sentinel:utm_zone": 52, "fmask:cloud_shadow": 0.0, "odc:product_family": "ard", "odc:dataset_version": "3.2.1", "dea:dataset_maturity": "nrt", "dea:product_maturity": "provisional", "gqa:iterative_mean_x": 0.24, "gqa:iterative_mean_y": 0.02, "sentinel:grid_square": "HL", "gqa:iterative_mean_xy": 0.24, "sentinel:datastrip_id": "S2A_OPER_MSI_L1C_DS_ATOS_20220824T025056_S20220824T012859_N04.00", "gqa:iterative_stddev_x": 0.16, "gqa:iterative_stddev_y": 0.18, "sentinel:latitude_band": "L", "gqa:iterative_stddev_xy": 0.24, "odc:processing_datetime": "2022-08-24 08:44:56.406794Z", "gqa:abs_iterative_mean_x": 0.25, "gqa:abs_iterative_mean_y": 0.14, "gqa:abs_iterative_mean_xy": 0.29, "sentinel:sentinel_tile_id": "S2A_OPER_MSI_L1C_TL_ATOS_20220824T025056_A037451_T52LHL_N04.00", "sentinel:datatake_start_datetime": "2022-08-24 02:50:56Z"}, "accessories": {"checksum:sha1": {"path": "ga_s2am_ard_provisional_3-2-1_52LHL_2022-08-24_nrt.sha1"}, "thumbnail:nbart": {"path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_thumbnail.jpg"}, "metadata:processor": {"path": "ga_s2am_ard_provisional_3-2-1_52LHL_2022-08-24_nrt.proc-info.yaml"}}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[799980.0, 8600020.0], [909780.0, 8600020.0], [909780.0, 8490220.0], [799980.0, 8490220.0], [799980.0, 8600020.0]]]}, "geo_ref_points": {"ll": {"x": 799980.0, "y": 8490220.0}, "lr": {"x": 909780.0, "y": 8490220.0}, "ul": {"x": 799980.0, "y": 8600020.0}, "ur": {"x": 909780.0, "y": 8600020.0}}, "spatial_reference": "epsg:32752"}}, "measurements": {"oa_fmask": {"grid": "20", "path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_fmask.tif"}, "nbart_red": {"path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_band04.tif"}, "nbart_blue": {"path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_band02.tif"}, "nbart_green": {"path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_band03.tif"}, "nbart_nir_1": {"path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_band08.tif"}, "nbart_nir_2": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_band08a.tif"}, "nbart_swir_2": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_band11.tif"}, "nbart_swir_3": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_band12.tif"}, "oa_time_delta": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_time-delta.tif"}, "oa_solar_zenith": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_solar-zenith.tif"}, "nbart_red_edge_1": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_band05.tif"}, "nbart_red_edge_2": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_band06.tif"}, "nbart_red_edge_3": {"grid": "20", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_band07.tif"}, "oa_exiting_angle": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_exiting-angle.tif"}, "oa_solar_azimuth": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_solar-azimuth.tif"}, "oa_incident_angle": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_incident-angle.tif"}, "oa_relative_slope": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_relative-slope.tif"}, "oa_satellite_view": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_satellite-view.tif"}, "oa_nbart_contiguity": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_nbart-contiguity.tif"}, "oa_relative_azimuth": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_relative-azimuth.tif"}, "oa_azimuthal_exiting": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_azimuthal-exiting.tif"}, "oa_satellite_azimuth": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_satellite-azimuth.tif"}, "nbart_coastal_aerosol": {"grid": "60", "path": "ga_s2am_nbart_provisional_3-2-1_52LHL_2022-08-24_nrt_band01.tif"}, "oa_azimuthal_incident": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_azimuthal-incident.tif"}, "oa_combined_terrain_shadow": {"path": "ga_s2am_oa_provisional_3-2-1_52LHL_2022-08-24_nrt_combined-terrain-shadow.tif"}}}	\N	2022-09-16 07:55:21.646557+00	opendatacubeusername	\N
a8af6783-f229-4db4-aaf4-af1ddafa0e45	4	4	{"id": "a8af6783-f229-4db4-aaf4-af1ddafa0e45", "crs": "epsg:32755", "grids": {"20": {"shape": [5490, 5490], "transform": [20.0, 0.0, 399960.0, 0.0, -20.0, 8500000.0, 0.0, 0.0, 1.0]}, "60": {"shape": [1830, 1830], "transform": [60.0, 0.0, 399960.0, 0.0, -60.0, 8500000.0, 0.0, 0.0, 1.0]}, "default": {"shape": [10980, 10980], "transform": [10.0, 0.0, 399960.0, 0.0, -10.0, 8500000.0, 0.0, 0.0, 1.0]}}, "label": "ga_s2bm_ard_provisional_3-2-1_55LDE_2022-08-31_nrt", "extent": {"lat": {"end": -13.567722461175256, "begin": -14.561239492890762}, "lon": {"end": 147.09060225681048, "begin": 146.16251761705198}}, "$schema": "https://schemas.opendatacube.org/dataset", "lineage": {"source_datasets": {}}, "product": {"href": "https://collections.dea.ga.gov.au/product/ga_s2bm_ard_provisional_3", "name": "ga_s2bm_ard_provisional_3"}, "geometry": {"type": "Polygon", "coordinates": [[[411020.49747498444, 8395764.433003273], [424098.0818604976, 8453245.021966778], [429030.2490827044, 8474962.218019813], [429577.0451471075, 8477363.700207612], [433681.493362407, 8495453.303133374], [434701.53652825835, 8499893.491570402], [434709.39144442376, 8499904.532186856], [434720.2503058669, 8499952.223390274], [434728.0074295721, 8499967.288429495], [434735.4497389044, 8500000.0], [434744.85091038153, 8500000.0], [434777.31262181944, 8500000.0], [509760.0, 8500000.0], [509760.0, 8390200.0], [409800.0, 8390200.0], [409780.0, 8390200.0], [411020.49747498444, 8395764.433003273]]]}, "properties": {"eo:gsd": 10.0, "datetime": "2022-08-31 00:30:53.168304Z", "gqa:abs_x": "NaN", "gqa:abs_y": "NaN", "gqa:cep90": "NaN", "fmask:snow": 0.05283151515454416, "gqa:abs_xy": "NaN", "gqa:mean_x": "NaN", "gqa:mean_y": "NaN", "eo:platform": "sentinel-2b", "fmask:clear": 0.22679442855542353, "fmask:cloud": 86.54279894162045, "fmask:water": 12.670355085257196, "gqa:mean_xy": "NaN", "gqa:stddev_x": "NaN", "gqa:stddev_y": "NaN", "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "gqa:stddev_xy": "NaN", "eo:cloud_cover": 86.54279894162045, "eo:sun_azimuth": 49.8493706735335, "odc:file_format": "GeoTIFF", "odc:region_code": "55LDE", "eo:constellation": "sentinel-2", "eo:sun_elevation": 34.2810700275433, "sentinel:utm_zone": 55, "fmask:cloud_shadow": 0.5072200294123894, "odc:product_family": "ard", "odc:dataset_version": "3.2.1", "dea:dataset_maturity": "nrt", "dea:product_maturity": "provisional", "gqa:iterative_mean_x": "NaN", "gqa:iterative_mean_y": "NaN", "sentinel:grid_square": "DE", "gqa:iterative_mean_xy": "NaN", "sentinel:datastrip_id": "S2B_OPER_MSI_L1C_DS_2BPS_20220831T012856_S20220831T002708_N04.00", "gqa:iterative_stddev_x": "NaN", "gqa:iterative_stddev_y": "NaN", "sentinel:latitude_band": "L", "gqa:iterative_stddev_xy": "NaN", "odc:processing_datetime": "2022-08-31 06:18:29.365639Z", "gqa:abs_iterative_mean_x": "NaN", "gqa:abs_iterative_mean_y": "NaN", "gqa:abs_iterative_mean_xy": "NaN", "sentinel:sentinel_tile_id": "S2B_OPER_MSI_L1C_TL_2BPS_20220831T012856_A028642_T55LDE_N04.00", "sentinel:datatake_start_datetime": "2022-08-31 01:28:56Z"}, "accessories": {"checksum:sha1": {"path": "ga_s2bm_ard_provisional_3-2-1_55LDE_2022-08-31_nrt.sha1"}, "thumbnail:nbart": {"path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_thumbnail.jpg"}, "metadata:processor": {"path": "ga_s2bm_ard_provisional_3-2-1_55LDE_2022-08-31_nrt.proc-info.yaml"}}, "grid_spatial": {"projection": {"valid_data": {"type": "Polygon", "coordinates": [[[411020.49747498444, 8395764.433003273], [424098.0818604976, 8453245.021966778], [429030.2490827044, 8474962.218019813], [429577.0451471075, 8477363.700207612], [433681.493362407, 8495453.303133374], [434701.53652825835, 8499893.491570402], [434709.39144442376, 8499904.532186856], [434720.2503058669, 8499952.223390274], [434728.0074295721, 8499967.288429495], [434735.4497389044, 8500000.0], [434744.85091038153, 8500000.0], [434777.31262181944, 8500000.0], [509760.0, 8500000.0], [509760.0, 8390200.0], [409800.0, 8390200.0], [409780.0, 8390200.0], [411020.49747498444, 8395764.433003273]]]}, "geo_ref_points": {"ll": {"x": 399960.0, "y": 8390200.0}, "lr": {"x": 509760.0, "y": 8390200.0}, "ul": {"x": 399960.0, "y": 8500000.0}, "ur": {"x": 509760.0, "y": 8500000.0}}, "spatial_reference": "epsg:32755"}}, "measurements": {"oa_fmask": {"grid": "20", "path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_fmask.tif"}, "nbart_red": {"path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_band04.tif"}, "nbart_blue": {"path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_band02.tif"}, "nbart_green": {"path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_band03.tif"}, "nbart_nir_1": {"path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_band08.tif"}, "nbart_nir_2": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_band08a.tif"}, "nbart_swir_2": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_band11.tif"}, "nbart_swir_3": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_band12.tif"}, "oa_time_delta": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_time-delta.tif"}, "oa_solar_zenith": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_solar-zenith.tif"}, "nbart_red_edge_1": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_band05.tif"}, "nbart_red_edge_2": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_band06.tif"}, "nbart_red_edge_3": {"grid": "20", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_band07.tif"}, "oa_exiting_angle": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_exiting-angle.tif"}, "oa_solar_azimuth": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_solar-azimuth.tif"}, "oa_incident_angle": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_incident-angle.tif"}, "oa_relative_slope": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_relative-slope.tif"}, "oa_satellite_view": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_satellite-view.tif"}, "oa_nbart_contiguity": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_nbart-contiguity.tif"}, "oa_relative_azimuth": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_relative-azimuth.tif"}, "oa_azimuthal_exiting": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_azimuthal-exiting.tif"}, "oa_satellite_azimuth": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_satellite-azimuth.tif"}, "nbart_coastal_aerosol": {"grid": "60", "path": "ga_s2bm_nbart_provisional_3-2-1_55LDE_2022-08-31_nrt_band01.tif"}, "oa_azimuthal_incident": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_azimuthal-incident.tif"}, "oa_combined_terrain_shadow": {"path": "ga_s2bm_oa_provisional_3-2-1_55LDE_2022-08-31_nrt_combined-terrain-shadow.tif"}}}	\N	2022-09-16 07:55:23.580158+00	opendatacubeusername	\N
\.


--
-- Data for Name: dataset_location; Type: TABLE DATA; Schema: agdc; Owner: agdc_admin
--

COPY agdc.dataset_location (id, dataset_ref, uri_scheme, uri_body, added, added_by, archived) FROM stdin;
1	37024e3d-2c35-4055-85dc-df4ed6d967b0	https	//data.dea.ga.gov.au/baseline/ga_ls7e_ard_provisional_3/104/076/2022/08/23_nrt/ga_ls7e_ard_provisional_3-2-1_104076_2022-08-23_nrt.odc-metadata.yaml	2022-09-16 07:55:17.703437+00	opendatacubeusername	\N
2	6a2fa1fa-4cb5-4366-a186-9f5c8accb775	https	//data.dea.ga.gov.au/baseline/ga_ls8c_ard_provisional_3/107/073/2022/08/25_nrt/ga_ls8c_ard_provisional_3-2-1_107073_2022-08-25_nrt.odc-metadata.yaml	2022-09-16 07:55:19.68112+00	opendatacubeusername	\N
3	a1911fa7-668b-49a0-8231-c950bdaaca4e	https	//data.dea.ga.gov.au/baseline/ga_s2am_ard_provisional_3/52/LHL/2022/08/24_nrt/20220824T025056/ga_s2am_ard_provisional_3-2-1_52LHL_2022-08-24_nrt.odc-metadata.yaml	2022-09-16 07:55:21.646557+00	opendatacubeusername	\N
4	a8af6783-f229-4db4-aaf4-af1ddafa0e45	https	//data.dea.ga.gov.au/baseline/ga_s2bm_ard_provisional_3/55/LDE/2022/08/31_nrt/20220831T012856/ga_s2bm_ard_provisional_3-2-1_55LDE_2022-08-31_nrt.odc-metadata.yaml	2022-09-16 07:55:23.580158+00	opendatacubeusername	\N
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
1	ga_ls7e_ard_provisional_3	{"product": {"name": "ga_ls7e_ard_provisional_3"}, "properties": {"eo:platform": "landsat-7", "odc:producer": "ga.gov.au", "eo:instrument": "ETM", "odc:product_family": "ard", "dea:product_maturity": "provisional", "landsat:collection_number": 2}}	4	{"name": "ga_ls7e_ard_provisional_3", "license": "CC-BY-4.0", "metadata": {"product": {"name": "ga_ls7e_ard_provisional_3"}, "properties": {"eo:platform": "landsat-7", "odc:producer": "ga.gov.au", "eo:instrument": "ETM", "odc:product_family": "ard", "dea:product_maturity": "provisional", "landsat:collection_number": 2}}, "description": "Geoscience Australia Landsat 7 Enhanced Thematic Mapper Plus Analysis Ready Data Collection 3 (provisional)", "measurements": [{"name": "nbart_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band01", "blue"]}, {"name": "nbart_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band02", "green"]}, {"name": "nbart_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band03", "red"]}, {"name": "nbart_nir", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band04", "nir"]}, {"name": "nbart_swir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band05", "swir_1", "swir1"]}, {"name": "nbart_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band07", "swir_2", "swir2"]}, {"name": "nbart_panchromatic", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band08", "panchromatic"]}, {"name": "oa_fmask", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["fmask"], "flags_definition": {"fmask": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "nodata", "1": "valid", "2": "cloud", "3": "shadow", "4": "snow", "5": "water"}, "description": "Fmask"}}}, {"name": "oa_nbart_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["nbart_contiguity"], "flags_definition": {"contiguous": {"bits": [0], "values": {"0": false, "1": true}}}}, {"name": "oa_azimuthal_exiting", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_exiting"]}, {"name": "oa_azimuthal_incident", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_incident"]}, {"name": "oa_combined_terrain_shadow", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["combined_terrain_shadow"]}, {"name": "oa_exiting_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["exiting_angle"]}, {"name": "oa_incident_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["incident_angle"]}, {"name": "oa_relative_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_azimuth"]}, {"name": "oa_relative_slope", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_slope"]}, {"name": "oa_satellite_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_azimuth"]}, {"name": "oa_satellite_view", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_view"]}, {"name": "oa_solar_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_azimuth"]}, {"name": "oa_solar_zenith", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_zenith"]}, {"name": "oa_time_delta", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["time_delta"]}], "metadata_type": "eo3_landsat_ard"}	2022-09-16 07:54:47.828817+00	opendatacubeusername	\N
2	ga_ls8c_ard_provisional_3	{"product": {"name": "ga_ls8c_ard_provisional_3"}, "properties": {"eo:platform": "landsat-8", "odc:producer": "ga.gov.au", "eo:instrument": "OLI_TIRS", "odc:product_family": "ard", "dea:product_maturity": "provisional", "landsat:collection_number": 2}}	4	{"name": "ga_ls8c_ard_provisional_3", "license": "CC-BY-4.0", "metadata": {"product": {"name": "ga_ls8c_ard_provisional_3"}, "properties": {"eo:platform": "landsat-8", "odc:producer": "ga.gov.au", "eo:instrument": "OLI_TIRS", "odc:product_family": "ard", "dea:product_maturity": "provisional", "landsat:collection_number": 2}}, "description": "Geoscience Australia Landsat 8 Operational Land Imager and Thermal Infra-Red Scanner Analysis Ready Data Collection 3 (provisional)", "measurements": [{"name": "nbart_coastal_aerosol", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band01", "coastal_aerosol"]}, {"name": "nbart_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band02", "blue"]}, {"name": "nbart_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band03", "green"]}, {"name": "nbart_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band04", "red"]}, {"name": "nbart_nir", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band05", "nir"]}, {"name": "nbart_swir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band06", "swir_1", "swir1"]}, {"name": "nbart_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band07", "swir_2", "swir2"]}, {"name": "nbart_panchromatic", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band08", "panchromatic"]}, {"name": "oa_fmask", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["fmask"], "flags_definition": {"fmask": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "nodata", "1": "valid", "2": "cloud", "3": "shadow", "4": "snow", "5": "water"}, "description": "Fmask"}}}, {"name": "oa_nbart_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["nbart_contiguity"], "flags_definition": {"contiguous": {"bits": [0], "values": {"0": false, "1": true}}}}, {"name": "oa_azimuthal_exiting", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_exiting"]}, {"name": "oa_azimuthal_incident", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_incident"]}, {"name": "oa_combined_terrain_shadow", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["combined_terrain_shadow"]}, {"name": "oa_exiting_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["exiting_angle"]}, {"name": "oa_incident_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["incident_angle"]}, {"name": "oa_relative_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_azimuth"]}, {"name": "oa_relative_slope", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_slope"]}, {"name": "oa_satellite_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_azimuth"]}, {"name": "oa_satellite_view", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_view"]}, {"name": "oa_solar_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_azimuth"]}, {"name": "oa_solar_zenith", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_zenith"]}, {"name": "oa_time_delta", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["time_delta"]}], "metadata_type": "eo3_landsat_ard"}	2022-09-16 07:54:50.073369+00	opendatacubeusername	\N
3	ga_s2am_ard_provisional_3	{"product": {"name": "ga_s2am_ard_provisional_3"}, "properties": {"eo:platform": "sentinel-2a", "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "odc:product_family": "ard", "dea:product_maturity": "provisional"}}	4	{"name": "ga_s2am_ard_provisional_3", "license": "CC-BY-4.0", "metadata": {"product": {"name": "ga_s2am_ard_provisional_3"}, "properties": {"eo:platform": "sentinel-2a", "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "odc:product_family": "ard", "dea:product_maturity": "provisional"}}, "description": "Geoscience Australia Sentinel 2a MSI Analysis Ready Data Collection 3 (provisional)", "measurements": [{"name": "nbart_coastal_aerosol", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band01", "coastal_aerosol"]}, {"name": "nbart_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band02", "blue"]}, {"name": "nbart_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band03", "green"]}, {"name": "nbart_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band04", "red"]}, {"name": "nbart_red_edge_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band05", "red_edge_1"]}, {"name": "nbart_red_edge_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band06", "red_edge_2"]}, {"name": "nbart_red_edge_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band07", "red_edge_3"]}, {"name": "nbart_nir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band08", "nir_1"]}, {"name": "nbart_nir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band8a", "nir_2"]}, {"name": "nbart_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band11", "swir_2", "swir2"]}, {"name": "nbart_swir_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band12", "swir_3"]}, {"name": "oa_fmask", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["fmask"], "flags_definition": {"fmask": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "nodata", "1": "valid", "2": "cloud", "3": "shadow", "4": "snow", "5": "water"}, "description": "Fmask"}}}, {"name": "oa_nbart_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["nbart_contiguity"], "flags_definition": {"contiguous": {"bits": [0], "values": {"0": false, "1": true}}}}, {"name": "oa_azimuthal_exiting", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_exiting"]}, {"name": "oa_azimuthal_incident", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_incident"]}, {"name": "oa_combined_terrain_shadow", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["combined_terrain_shadow"]}, {"name": "oa_exiting_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["exiting_angle"]}, {"name": "oa_incident_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["incident_angle"]}, {"name": "oa_relative_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_azimuth"]}, {"name": "oa_relative_slope", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_slope"]}, {"name": "oa_satellite_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_azimuth"]}, {"name": "oa_satellite_view", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_view"]}, {"name": "oa_solar_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_azimuth"]}, {"name": "oa_solar_zenith", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_zenith"]}, {"name": "oa_time_delta", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["time_delta"]}], "metadata_type": "eo3_landsat_ard"}	2022-09-16 07:54:52.426768+00	opendatacubeusername	\N
4	ga_s2bm_ard_provisional_3	{"product": {"name": "ga_s2bm_ard_provisional_3"}, "properties": {"eo:platform": "sentinel-2b", "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "odc:product_family": "ard", "dea:product_maturity": "provisional"}}	4	{"name": "ga_s2bm_ard_provisional_3", "license": "CC-BY-4.0", "metadata": {"product": {"name": "ga_s2bm_ard_provisional_3"}, "properties": {"eo:platform": "sentinel-2b", "odc:producer": "ga.gov.au", "eo:instrument": "MSI", "odc:product_family": "ard", "dea:product_maturity": "provisional"}}, "description": "Geoscience Australia Sentinel 2b MSI Analysis Ready Data Collection 3 (provisional)", "measurements": [{"name": "nbart_coastal_aerosol", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band01", "coastal_aerosol"]}, {"name": "nbart_blue", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band02", "blue"]}, {"name": "nbart_green", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band03", "green"]}, {"name": "nbart_red", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band04", "red"]}, {"name": "nbart_red_edge_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band05", "red_edge_1"]}, {"name": "nbart_red_edge_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band06", "red_edge_2"]}, {"name": "nbart_red_edge_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band07", "red_edge_3"]}, {"name": "nbart_nir_1", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band08", "nir_1"]}, {"name": "nbart_nir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band8a", "nir_2"]}, {"name": "nbart_swir_2", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band11", "swir_2", "swir2"]}, {"name": "nbart_swir_3", "dtype": "int16", "units": "1", "nodata": -999, "aliases": ["nbart_band12", "swir_3"]}, {"name": "oa_fmask", "dtype": "uint8", "units": "1", "nodata": 0, "aliases": ["fmask"], "flags_definition": {"fmask": {"bits": [0, 1, 2, 3, 4, 5, 6, 7], "values": {"0": "nodata", "1": "valid", "2": "cloud", "3": "shadow", "4": "snow", "5": "water"}, "description": "Fmask"}}}, {"name": "oa_nbart_contiguity", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["nbart_contiguity"], "flags_definition": {"contiguous": {"bits": [0], "values": {"0": false, "1": true}}}}, {"name": "oa_azimuthal_exiting", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_exiting"]}, {"name": "oa_azimuthal_incident", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["azimuthal_incident"]}, {"name": "oa_combined_terrain_shadow", "dtype": "uint8", "units": "1", "nodata": 255, "aliases": ["combined_terrain_shadow"]}, {"name": "oa_exiting_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["exiting_angle"]}, {"name": "oa_incident_angle", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["incident_angle"]}, {"name": "oa_relative_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_azimuth"]}, {"name": "oa_relative_slope", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["relative_slope"]}, {"name": "oa_satellite_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_azimuth"]}, {"name": "oa_satellite_view", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["satellite_view"]}, {"name": "oa_solar_azimuth", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_azimuth"]}, {"name": "oa_solar_zenith", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["solar_zenith"]}, {"name": "oa_time_delta", "dtype": "float32", "units": "1", "nodata": "NaN", "aliases": ["time_delta"]}], "metadata_type": "eo3_landsat_ard"}	2022-09-16 07:54:54.580479+00	opendatacubeusername	\N
\.


--
-- Data for Name: metadata_type; Type: TABLE DATA; Schema: agdc; Owner: agdc_admin
--

COPY agdc.metadata_type (id, name, definition, added, added_by, updated) FROM stdin;
1	eo3	{"name": "eo3", "dataset": {"id": ["id"], "label": ["label"], "format": ["properties", "odc:file_format"], "sources": ["lineage", "source_datasets"], "creation_dt": ["properties", "odc:processing_datetime"], "grid_spatial": ["grid_spatial", "projection"], "measurements": ["measurements"], "search_fields": {"lat": {"type": "double-range", "max_offset": [["extent", "lat", "end"]], "min_offset": [["extent", "lat", "begin"]], "description": "Latitude range"}, "lon": {"type": "double-range", "max_offset": [["extent", "lon", "end"]], "min_offset": [["extent", "lon", "begin"]], "description": "Longitude range"}, "time": {"type": "datetime-range", "max_offset": [["properties", "dtr:end_datetime"], ["properties", "datetime"]], "min_offset": [["properties", "dtr:start_datetime"], ["properties", "datetime"]], "description": "Acquisition time range"}, "platform": {"offset": ["properties", "eo:platform"], "indexed": false, "description": "Platform code"}, "instrument": {"offset": ["properties", "eo:instrument"], "indexed": false, "description": "Instrument name"}, "cloud_cover": {"type": "double", "offset": ["properties", "eo:cloud_cover"], "indexed": false, "description": "Cloud cover percentage [0, 100]"}, "region_code": {"offset": ["properties", "odc:region_code"], "description": "Spatial reference code from the provider. For Landsat region_code is a scene path row:\\n        '{:03d}{:03d}.format(path,row)'.\\nFor Sentinel it is MGRS code. In general it is a unique string identifier that datasets covering roughly the same spatial region share.\\n"}, "product_family": {"offset": ["properties", "odc:product_family"], "indexed": false, "description": "Product family code"}, "dataset_maturity": {"offset": ["properties", "dea:dataset_maturity"], "indexed": false, "description": "One of - final|interim|nrt  (near real time)"}}}, "description": "Default EO3 with no custom fields"}	2022-09-16 07:54:38.976775+00	opendatacubeusername	\N
2	eo	{"name": "eo", "dataset": {"id": ["id"], "label": ["ga_label"], "format": ["format", "name"], "sources": ["lineage", "source_datasets"], "creation_dt": ["creation_dt"], "grid_spatial": ["grid_spatial", "projection"], "measurements": ["image", "bands"], "search_fields": {"lat": {"type": "double-range", "max_offset": [["extent", "coord", "ur", "lat"], ["extent", "coord", "lr", "lat"], ["extent", "coord", "ul", "lat"], ["extent", "coord", "ll", "lat"]], "min_offset": [["extent", "coord", "ur", "lat"], ["extent", "coord", "lr", "lat"], ["extent", "coord", "ul", "lat"], ["extent", "coord", "ll", "lat"]], "description": "Latitude range"}, "lon": {"type": "double-range", "max_offset": [["extent", "coord", "ul", "lon"], ["extent", "coord", "ur", "lon"], ["extent", "coord", "ll", "lon"], ["extent", "coord", "lr", "lon"]], "min_offset": [["extent", "coord", "ul", "lon"], ["extent", "coord", "ur", "lon"], ["extent", "coord", "ll", "lon"], ["extent", "coord", "lr", "lon"]], "description": "Longitude range"}, "time": {"type": "datetime-range", "max_offset": [["extent", "to_dt"], ["extent", "center_dt"]], "min_offset": [["extent", "from_dt"], ["extent", "center_dt"]], "description": "Acquisition time"}, "platform": {"offset": ["platform", "code"], "description": "Platform code"}, "instrument": {"offset": ["instrument", "name"], "description": "Instrument name"}, "product_type": {"offset": ["product_type"], "description": "Product code"}}}, "description": "Earth Observation datasets.\\n\\nExpected metadata structure produced by the eodatasets library, as used internally at GA.\\n\\nhttps://github.com/GeoscienceAustralia/eo-datasets\\n"}	2022-09-16 07:54:39.014304+00	opendatacubeusername	\N
3	telemetry	{"name": "telemetry", "dataset": {"id": ["id"], "label": ["ga_label"], "sources": ["lineage", "source_datasets"], "creation_dt": ["creation_dt"], "search_fields": {"gsi": {"offset": ["acquisition", "groundstation", "code"], "indexed": false, "description": "Ground Station Identifier (eg. ASA)"}, "time": {"type": "datetime-range", "max_offset": [["acquisition", "los"]], "min_offset": [["acquisition", "aos"]], "description": "Acquisition time"}, "orbit": {"type": "integer", "offset": ["acquisition", "platform_orbit"], "description": "Orbit number"}, "sat_row": {"type": "integer-range", "max_offset": [["image", "satellite_ref_point_end", "y"], ["image", "satellite_ref_point_start", "y"]], "min_offset": [["image", "satellite_ref_point_start", "y"]], "description": "Landsat row"}, "platform": {"offset": ["platform", "code"], "description": "Platform code"}, "sat_path": {"type": "integer-range", "max_offset": [["image", "satellite_ref_point_end", "x"], ["image", "satellite_ref_point_start", "x"]], "min_offset": [["image", "satellite_ref_point_start", "x"]], "description": "Landsat path"}, "instrument": {"offset": ["instrument", "name"], "description": "Instrument name"}, "product_type": {"offset": ["product_type"], "description": "Product code"}}}, "description": "Satellite telemetry datasets.\\n\\nExpected metadata structure produced by telemetry datasets from the eodatasets library, as used internally at GA.\\n\\nhttps://github.com/GeoscienceAustralia/eo-datasets\\n"}	2022-09-16 07:54:39.049051+00	opendatacubeusername	\N
4	eo3_landsat_ard	{"name": "eo3_landsat_ard", "dataset": {"id": ["id"], "label": ["label"], "format": ["properties", "odc:file_format"], "sources": ["lineage", "source_datasets"], "creation_dt": ["properties", "odc:processing_datetime"], "grid_spatial": ["grid_spatial", "projection"], "measurements": ["measurements"], "search_fields": {"gqa": {"type": "double", "offset": ["properties", "gqa:cep90"], "description": "GQA Circular error probable (90%)"}, "lat": {"type": "double-range", "max_offset": [["extent", "lat", "end"]], "min_offset": [["extent", "lat", "begin"]], "description": "Latitude range"}, "lon": {"type": "double-range", "max_offset": [["extent", "lon", "end"]], "min_offset": [["extent", "lon", "begin"]], "description": "Longitude range"}, "time": {"type": "datetime-range", "max_offset": [["properties", "dtr:end_datetime"], ["properties", "datetime"]], "min_offset": [["properties", "dtr:start_datetime"], ["properties", "datetime"]], "description": "Acquisition time range"}, "eo_gsd": {"type": "double", "offset": ["properties", "eo:gsd"], "indexed": false, "description": "Ground sample distance, meters"}, "crs_raw": {"offset": ["crs"], "indexed": false, "description": "The raw CRS string as it appears in metadata"}, "platform": {"offset": ["properties", "eo:platform"], "indexed": false, "description": "Platform code"}, "gqa_abs_x": {"type": "double", "offset": ["properties", "gqa:abs_x"], "indexed": false, "description": "TODO: <gqa:abs_x>"}, "gqa_abs_y": {"type": "double", "offset": ["properties", "gqa:abs_y"], "indexed": false, "description": "TODO: <gqa:abs_y>"}, "gqa_cep90": {"type": "double", "offset": ["properties", "gqa:cep90"], "indexed": false, "description": "TODO: <gqa:cep90>"}, "fmask_snow": {"type": "double", "offset": ["properties", "fmask:snow"], "indexed": false, "description": "TODO: <fmask:snow>"}, "gqa_abs_xy": {"type": "double", "offset": ["properties", "gqa:abs_xy"], "indexed": false, "description": "TODO: <gqa:abs_xy>"}, "gqa_mean_x": {"type": "double", "offset": ["properties", "gqa:mean_x"], "indexed": false, "description": "TODO: <gqa:mean_x>"}, "gqa_mean_y": {"type": "double", "offset": ["properties", "gqa:mean_y"], "indexed": false, "description": "TODO: <gqa:mean_y>"}, "instrument": {"offset": ["properties", "eo:instrument"], "indexed": false, "description": "Instrument name"}, "cloud_cover": {"type": "double", "offset": ["properties", "eo:cloud_cover"], "description": "Cloud cover percentage [0, 100]"}, "fmask_clear": {"type": "double", "offset": ["properties", "fmask:clear"], "indexed": false, "description": "TODO: <fmask:clear>"}, "fmask_water": {"type": "double", "offset": ["properties", "fmask:water"], "indexed": false, "description": "TODO: <fmask:water>"}, "gqa_mean_xy": {"type": "double", "offset": ["properties", "gqa:mean_xy"], "indexed": false, "description": "TODO: <gqa:mean_xy>"}, "region_code": {"offset": ["properties", "odc:region_code"], "description": "Spatial reference code from the provider. For Landsat region_code is a scene path row:\\n        '{:03d}{:03d}.format(path,row)'\\nFor Sentinel it is MGRS code. In general it is a unique string identifier that datasets covering roughly the same spatial region share.\\n"}, "gqa_stddev_x": {"type": "double", "offset": ["properties", "gqa:stddev_x"], "indexed": false, "description": "TODO: <gqa:stddev_x>"}, "gqa_stddev_y": {"type": "double", "offset": ["properties", "gqa:stddev_y"], "indexed": false, "description": "TODO: <gqa:stddev_y>"}, "gqa_stddev_xy": {"type": "double", "offset": ["properties", "gqa:stddev_xy"], "indexed": false, "description": "TODO: <gqa:stddev_xy>"}, "eo_sun_azimuth": {"type": "double", "offset": ["properties", "eo:sun_azimuth"], "indexed": false, "description": "TODO: <eo:sun_azimuth>"}, "product_family": {"offset": ["properties", "odc:product_family"], "indexed": false, "description": "Product family code"}, "dataset_maturity": {"offset": ["properties", "dea:dataset_maturity"], "description": "One of - final|interim|nrt  (near real time)"}, "eo_sun_elevation": {"type": "double", "offset": ["properties", "eo:sun_elevation"], "indexed": false, "description": "TODO: <eo:sun_elevation>"}, "landsat_scene_id": {"offset": ["properties", "landsat:landsat_scene_id"], "indexed": false, "description": "Landsat Scene ID"}, "fmask_cloud_shadow": {"type": "double", "offset": ["properties", "fmask:cloud_shadow"], "indexed": false, "description": "TODO: <fmask:cloud_shadow>"}, "landsat_product_id": {"offset": ["properties", "landsat:landsat_product_id"], "indexed": false, "description": "Landsat Product ID"}, "gqa_iterative_mean_x": {"type": "double", "offset": ["properties", "gqa:iterative_mean_x"], "indexed": false, "description": "TODO: <gqa:iterative_mean_x>"}, "gqa_iterative_mean_y": {"type": "double", "offset": ["properties", "gqa:iterative_mean_y"], "indexed": false, "description": "TODO: <gqa:iterative_mean_y>"}, "gqa_iterative_mean_xy": {"type": "double", "offset": ["properties", "gqa:iterative_mean_xy"], "indexed": false, "description": "TODO: <gqa:iterative_mean_xy>"}, "gqa_iterative_stddev_x": {"type": "double", "offset": ["properties", "gqa:iterative_stddev_x"], "indexed": false, "description": "TODO: <gqa:iterative_stddev_x>"}, "gqa_iterative_stddev_y": {"type": "double", "offset": ["properties", "gqa:iterative_stddev_y"], "indexed": false, "description": "TODO: <gqa:iterative_stddev_y>"}, "gqa_iterative_stddev_xy": {"type": "double", "offset": ["properties", "gqa:iterative_stddev_xy"], "indexed": false, "description": "TODO: <gqa:iterative_stddev_xy>"}, "gqa_abs_iterative_mean_x": {"type": "double", "offset": ["properties", "gqa:abs_iterative_mean_x"], "indexed": false, "description": "TODO: <gqa:abs_iterative_mean_x>"}, "gqa_abs_iterative_mean_y": {"type": "double", "offset": ["properties", "gqa:abs_iterative_mean_y"], "indexed": false, "description": "TODO: <gqa:abs_iterative_mean_y>"}, "gqa_abs_iterative_mean_xy": {"type": "double", "offset": ["properties", "gqa:abs_iterative_mean_xy"], "indexed": false, "description": "TODO: <gqa:abs_iterative_mean_xy>"}}}, "description": "EO3 for ARD Landsat Collection 3"}	2022-09-16 07:54:45.608226+00	opendatacubeusername	\N
\.


--
-- Data for Name: job; Type: TABLE DATA; Schema: cron; Owner: postgres
--

COPY cron.job (jobid, schedule, command, nodename, nodeport, database, username, active, jobname) FROM stdin;
\.


--
-- Data for Name: job_run_details; Type: TABLE DATA; Schema: cron; Owner: postgres
--

COPY cron.job_run_details (jobid, runid, job_pid, database, username, command, status, return_message, start_time, end_time) FROM stdin;
\.


--
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) FROM stdin;
\.


--
-- Data for Name: topology; Type: TABLE DATA; Schema: topology; Owner: postgres
--

COPY topology.topology (id, name, srid, "precision", hasz) FROM stdin;
\.


--
-- Data for Name: layer; Type: TABLE DATA; Schema: topology; Owner: postgres
--

COPY topology.layer (topology_id, layer_id, schema_name, table_name, feature_column, feature_type, level, child_id) FROM stdin;
\.


--
-- Name: dataset_location_id_seq; Type: SEQUENCE SET; Schema: agdc; Owner: agdc_admin
--

SELECT pg_catalog.setval('agdc.dataset_location_id_seq', 4, true);


--
-- Name: dataset_type_id_seq; Type: SEQUENCE SET; Schema: agdc; Owner: agdc_admin
--

SELECT pg_catalog.setval('agdc.dataset_type_id_seq', 4, true);


--
-- Name: metadata_type_id_seq; Type: SEQUENCE SET; Schema: agdc; Owner: agdc_admin
--

SELECT pg_catalog.setval('agdc.metadata_type_id_seq', 4, true);


--
-- Name: jobid_seq; Type: SEQUENCE SET; Schema: cron; Owner: postgres
--

SELECT pg_catalog.setval('cron.jobid_seq', 1, false);


--
-- Name: runid_seq; Type: SEQUENCE SET; Schema: cron; Owner: postgres
--

SELECT pg_catalog.setval('cron.runid_seq', 1, false);


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
-- Name: dix_ga_ls7e_ard_provisional_3_cloud_cover; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_cloud_cover ON agdc.dataset USING btree ((((metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 1));


--
-- Name: dix_ga_ls7e_ard_provisional_3_dataset_maturity; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_dataset_maturity ON agdc.dataset USING btree (((metadata #>> '{properties,dea:dataset_maturity}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 1));


--
-- Name: dix_ga_ls7e_ard_provisional_3_gqa; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_gqa ON agdc.dataset USING btree ((((metadata #>> '{properties,gqa:cep90}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 1));


--
-- Name: dix_ga_ls7e_ard_provisional_3_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 1));


--
-- Name: dix_ga_ls7e_ard_provisional_3_region_code; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_region_code ON agdc.dataset USING btree (((metadata #>> '{properties,odc:region_code}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 1));


--
-- Name: dix_ga_ls7e_ard_provisional_3_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls7e_ard_provisional_3_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text), agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 1));


--
-- Name: dix_ga_ls8c_ard_provisional_3_cloud_cover; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_cloud_cover ON agdc.dataset USING btree ((((metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 2));


--
-- Name: dix_ga_ls8c_ard_provisional_3_dataset_maturity; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_dataset_maturity ON agdc.dataset USING btree (((metadata #>> '{properties,dea:dataset_maturity}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 2));


--
-- Name: dix_ga_ls8c_ard_provisional_3_gqa; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_gqa ON agdc.dataset USING btree ((((metadata #>> '{properties,gqa:cep90}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 2));


--
-- Name: dix_ga_ls8c_ard_provisional_3_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 2));


--
-- Name: dix_ga_ls8c_ard_provisional_3_region_code; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_region_code ON agdc.dataset USING btree (((metadata #>> '{properties,odc:region_code}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 2));


--
-- Name: dix_ga_ls8c_ard_provisional_3_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_ls8c_ard_provisional_3_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text), agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 2));


--
-- Name: dix_ga_s2am_ard_provisional_3_cloud_cover; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_cloud_cover ON agdc.dataset USING btree ((((metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_s2am_ard_provisional_3_dataset_maturity; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_dataset_maturity ON agdc.dataset USING btree (((metadata #>> '{properties,dea:dataset_maturity}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_s2am_ard_provisional_3_gqa; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_gqa ON agdc.dataset USING btree ((((metadata #>> '{properties,gqa:cep90}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_s2am_ard_provisional_3_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_s2am_ard_provisional_3_region_code; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_region_code ON agdc.dataset USING btree (((metadata #>> '{properties,odc:region_code}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_s2am_ard_provisional_3_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2am_ard_provisional_3_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text), agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 3));


--
-- Name: dix_ga_s2bm_ard_provisional_3_cloud_cover; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_cloud_cover ON agdc.dataset USING btree ((((metadata #>> '{properties,eo:cloud_cover}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: dix_ga_s2bm_ard_provisional_3_dataset_maturity; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_dataset_maturity ON agdc.dataset USING btree (((metadata #>> '{properties,dea:dataset_maturity}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: dix_ga_s2bm_ard_provisional_3_gqa; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_gqa ON agdc.dataset USING btree ((((metadata #>> '{properties,gqa:cep90}'::text[]))::double precision)) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: dix_ga_s2bm_ard_provisional_3_lat_lon_time; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_lat_lon_time ON agdc.dataset USING gist (agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text), tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: dix_ga_s2bm_ard_provisional_3_region_code; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_region_code ON agdc.dataset USING btree (((metadata #>> '{properties,odc:region_code}'::text[]))) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: dix_ga_s2bm_ard_provisional_3_time_lat_lon; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX dix_ga_s2bm_ard_provisional_3_time_lat_lon ON agdc.dataset USING gist (tstzrange(LEAST(agdc.common_timestamp((metadata #>> '{properties,dtr:start_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), GREATEST(agdc.common_timestamp((metadata #>> '{properties,dtr:end_datetime}'::text[])), agdc.common_timestamp((metadata #>> '{properties,datetime}'::text[]))), '[]'::text), agdc.float8range(((metadata #>> '{extent,lat,begin}'::text[]))::double precision, ((metadata #>> '{extent,lat,end}'::text[]))::double precision, '[]'::text), agdc.float8range(((metadata #>> '{extent,lon,begin}'::text[]))::double precision, ((metadata #>> '{extent,lon,end}'::text[]))::double precision, '[]'::text)) WHERE ((archived IS NULL) AND (dataset_type_ref = 4));


--
-- Name: ix_agdc_dataset_dataset_type_ref; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX ix_agdc_dataset_dataset_type_ref ON agdc.dataset USING btree (dataset_type_ref);


--
-- Name: ix_agdc_dataset_location_dataset_ref; Type: INDEX; Schema: agdc; Owner: agdc_admin
--

CREATE INDEX ix_agdc_dataset_location_dataset_ref ON agdc.dataset_location USING btree (dataset_ref);


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
-- Name: job cron_job_policy; Type: POLICY; Schema: cron; Owner: postgres
--

CREATE POLICY cron_job_policy ON cron.job USING ((username = CURRENT_USER));


--
-- Name: job_run_details cron_job_run_details_policy; Type: POLICY; Schema: cron; Owner: postgres
--

CREATE POLICY cron_job_run_details_policy ON cron.job_run_details USING ((username = CURRENT_USER));


--
-- Name: job; Type: ROW SECURITY; Schema: cron; Owner: postgres
--

ALTER TABLE cron.job ENABLE ROW LEVEL SECURITY;

--
-- Name: job_run_details; Type: ROW SECURITY; Schema: cron; Owner: postgres
--

ALTER TABLE cron.job_run_details ENABLE ROW LEVEL SECURITY;

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
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: opendatacubeusername
--

ALTER DEFAULT PRIVILEGES FOR ROLE opendatacubeusername IN SCHEMA public REVOKE ALL ON TABLES  FROM opendatacubeusername;
ALTER DEFAULT PRIVILEGES FOR ROLE opendatacubeusername IN SCHEMA public GRANT SELECT ON TABLES  TO replicator;


--
-- PostgreSQL database dump complete
--

