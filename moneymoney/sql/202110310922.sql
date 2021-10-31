-- Removed bad seq and set over 1000 for new concepts

DROP SEQUENCE IF EXISTS public.seq_conceptos ;
DROP SEQUENCE IF EXISTS public.concepts_seq;
CREATE SEQUENCE public.concepts_seq START WITH 1000;