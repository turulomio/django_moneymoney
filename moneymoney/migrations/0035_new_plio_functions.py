# Generated by Django 4.1.7 on 2023-02-25 18:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('moneymoney', '0034_new_pl_total_balance_function'),
    ]

    operations = [
        migrations.RunSQL("""
CREATE OR REPLACE FUNCTION public.pl_total_balance(p_at_datetime timestamp with time zone, user_currency text)
 RETURNS text
 LANGUAGE plpython3u
AS $function$
from decimal import Decimal
from json import dumps,loads
from moneymoney_pl.core import MyDjangoJSONEncoder

plan_accounts=plpy.prepare('SELECT * from  accounts_balance($1,$2)',["timestamp with time zone","text"])
accounts=plpy.execute(plan_accounts, (p_at_datetime,user_currency))
accounts_user=accounts[0]['accounts_balance']

plan_investments=plpy.prepare('SELECT * FROM pl_investment_operations($1,$2,$3,$4)',["timestamp with time zone","text","integer[]","integer"])
investments=loads(plpy.execute(plan_investments,(p_at_datetime, user_currency, None, 3))[0]["pl_investment_operations"])

r= { 
    "accounts_user": accounts_user, 
    "investments_user": investments["sum_total_io_current"]["balance_user"],
    "total_user": accounts_user+Decimal(investments["sum_total_io_current"]["balance_user"]),
    "investments_invested_user": investments["sum_total_io_current"]["invested_user"],
    "datetime": p_at_datetime,
    },

return dumps(r, cls=MyDjangoJSONEncoder)
$function$
"""),
        migrations.RunSQL("""
CREATE OR REPLACE FUNCTION public.pl_investment_operations(p_at_datetime timestamp with time zone, currency_user text, investments_ids integer[] DEFAULT NULL::integer[], mode integer DEFAULT 3)
 RETURNS text
 LANGUAGE plpython3u
AS $function$
# Mode1. Show all, Mode2. Show totals and sums. Mode3. Show sums

from moneymoney_pl import core
from json import dumps

cf_plan=plpy.prepare('SELECT * FROM currency_factor($1,$2,$3)',["timestamp with time zone","text","text"])
quote_plan=plpy.prepare("select quote from quote($1, $2)",("integer","timestamp with time zone"))
if investments_ids is None:
    data_plan=plpy.prepare('SELECT products.id as products_id, investments.id as investments_id, multiplier, accounts.currency as currency_account, products.currency as currency_product, productstypes_id from accounts, investments, products, leverages where accounts.id=investments.accounts_id and investments.products_id=products.id and leverages.id=products.leverages_id' )
    plan=plpy.prepare('SELECT * from public.investmentsoperations where datetime<$1 order by datetime', ("timestamp with time zone",))
else:
    data_plan=plpy.prepare('SELECT products.id as products_id, investments.id as investments_id, multiplier, accounts.currency as currency_account, products.currency as currency_product, productstypes_id from accounts, investments, products, leverages where accounts.id=investments.accounts_id and investments.products_id=products.id and leverages.id=products.leverages_id and investments.id = any($1)', ("integer[]",))
    plan=plpy.prepare('SELECT * from public.investmentsoperations where datetime<$1 and investments_id= any ($2) order by datetime', ("timestamp with time zone", "integer[]"))

# Lazy
if investments_ids is None:
    t=core.calculate_ios_lazy(p_at_datetime, plpy.execute(data_plan), plpy.execute(plan, (p_at_datetime,)) , currency_user)
else:
    t=core.calculate_ios_lazy(p_at_datetime, plpy.execute(data_plan, (investments_ids,)), plpy.execute(plan, (p_at_datetime, investments_ids)), currency_user)


# Get quotes and factors
for products_id, dt in t["lazy_quotes"].keys():
    quote=plpy.execute(quote_plan, (products_id, dt))[0]['quote']
    t["lazy_quotes"][(products_id,dt)]=quote if quote is not None else 0

for from_,  to_, dt in t["lazy_factors"].keys():
    factor=plpy.execute(cf_plan, [dt, from_, to_])[0]['currency_factor']
    t["lazy_factors"][(from_, to_, dt)]=factor if factor is not None else 0

# Finish
t=core.calculate_ios_finish(t, mode)

return dumps(t, cls=core.MyDjangoJSONEncoder, indent=4)
$function$
"""),


        migrations.RunSQL("""drop function if exists public.investment_operations;"""),
        migrations.RunSQL("""drop function if exists public.investment_operations_totals;"""),
        migrations.RunSQL("""drop function if exists public.tt_investment_operations;"""),
    ]

