
CREATE TABLE public.stockmarkets (
    id integer NOT NULL,
    name text NOT NULL,
    country character varying(5) NOT NULL,
    starts time without time zone NOT NULL,
    closes time without time zone NOT NULL,
    starts_futures time without time zone NOT NULL,
    closes_futures time without time zone NOT NULL,
    zone text NOT NULL
);


ALTER TABLE public.stockmarkets OWNER TO postgres;


-- Data for Name: stockmarkets; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.stockmarkets VALUES (1, 'Madrid Stock Exchange', 'es', '09:00:00', '17:38:00', '08:00:00', '20:00:00', 'Europe/Madrid');
INSERT INTO public.stockmarkets VALUES (11, 'Belgium Stock Exchange', 'be', '09:00:00', '17:38:00', '08:00:00', '17:40:00', 'Europe/Brussels');
INSERT INTO public.stockmarkets VALUES (12, 'Amsterdam Stock Exchange', 'nl', '09:00:00', '17:38:00', '08:00:00', '22:00:00', 'Europe/Amsterdam');
INSERT INTO public.stockmarkets VALUES (13, 'Dublin Stock Exchange', 'ie', '08:00:00', '16:38:00', '08:00:00', '20:00:00', 'Europe/Dublin');
INSERT INTO public.stockmarkets VALUES (14, 'Helsinki Stock Exchange', 'fi', '09:00:00', '18:38:00', '08:00:00', '20:00:00', 'Europe/Helsinki');
INSERT INTO public.stockmarkets VALUES (6, 'Milan Stock Exchange', 'it', '09:00:00', '17:38:00', '08:00:00', '20:00:00', 'Europe/Rome');
INSERT INTO public.stockmarkets VALUES (7, 'Tokyo Stock Exchange', 'jp', '09:00:00', '15:08:00', '08:00:00', '20:00:00', 'Asia/Tokyo');
INSERT INTO public.stockmarkets VALUES (5, 'Frankfurt Stock Exchange', 'de', '09:00:00', '17:38:00', '01:00:00', '22:00:00', 'Europe/Berlin');
INSERT INTO public.stockmarkets VALUES (2, 'NYSE Stock Exchange', 'us', '09:30:00', '16:38:00', '00:00:00', '23:59:00', 'America/New_York');
INSERT INTO public.stockmarkets VALUES (10, 'Europe Stock Exchange', 'ue', '09:00:00', '17:38:00', '01:00:00', '22:00:00', 'Europe/Brussels');
INSERT INTO public.stockmarkets VALUES (9, 'Lisbon Stock Exchange', 'pt', '09:00:00', '17:38:00', '08:00:00', '17:40:00', 'Europe/Lisbon');
INSERT INTO public.stockmarkets VALUES (4, 'London Stock Exchange', 'en', '09:00:00', '17:38:00', '08:00:00', '20:00:00', 'Europe/London');
INSERT INTO public.stockmarkets VALUES (8, 'Hong Kong Stock Exchange', 'cn', '09:30:00', '16:08:00', '08:00:00', '20:00:00', 'Asia/Hong_Kong');
INSERT INTO public.stockmarkets VALUES (3, 'Paris Stock Exchange', 'fr', '09:00:00', '17:38:00', '08:00:00', '22:00:00', 'Europe/Paris');
INSERT INTO public.stockmarkets VALUES (15, 'Not listed on official markets', 'earth', '09:00:00', '17:38:00', '08:00:00', '20:00:00', 'Europe/Madrid');
INSERT INTO public.stockmarkets VALUES (16, 'AMEX Stock Exchange', 'us', '09:30:00', '16:38:00', '00:00:00', '23:59:00', 'America/New_York');
INSERT INTO public.stockmarkets VALUES (17, 'Nasdaq Stock Exchange', 'us', '09:30:00', '16:38:00', '00:00:00', '23:59:00', 'America/New_York');
INSERT INTO public.stockmarkets VALUES (18, 'Luxembourg Stock Exchange', 'lu', '09:00:00', '17:38:00', '08:00:00', '20:00:00', 'Europe/Luxembourg');


--
-- Name: stockmarkets stockmarkets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stockmarkets
    ADD CONSTRAINT stockmarkets_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

