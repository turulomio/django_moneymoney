-- Removed products high_low column
alter table public.products add column ticker_yahoo text;
alter table public.products add column ticker_morningstar text;
alter table public.products add column ticker_google text;
alter table public.products add column ticker_quefondos text;
alter table public.products add column ticker_investingcom text;
