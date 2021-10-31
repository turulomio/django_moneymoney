-- Removed bad seq and set over 1000 for new concepts
insert into public.concepts (id, name, operationstypes_id, editable) values( 10, 'Paysheet', 2, false) on conflict (id) do update set name='Paysheet', editable=false;
insert into public.concepts (id, name, operationstypes_id, editable) values( 44, 'Adjustments. Negative', 1, false) on conflict (id) do update set name='Adjustments. Negative',editable=false;
insert into public.concepts (id, name, operationstypes_id, editable) values( 100, 'Adjustments. Positive', 2, false) on conflict (id) do update set name='Adjustments. Positive', editable=false;
insert into public.concepts (id, name, operationstypes_id, editable) values( 200, 'Unknown', 1, false) on conflict (id) do update set name='Unknown', editable=false;
