-- Added several fields like average_price_investments, invested_investment...

CREATE OR REPLACE FUNCTION public.investment_operations_totals(p_investment_id integer, p_at_datetime timestamp with time zone, user_currency text) RETURNS TABLE(io text, io_current text, io_historical text)
    LANGUAGE plpython3u
    AS $_$
from decimal import Decimal
plan=plpy.prepare('SELECT * FROM investment_operations($1,$2,$3)',["integer", "timestamp with time zone","text"])
data=plpy.execute(plan, (p_investment_id,p_at_datetime,user_currency))[0]
io=eval(data['io'])
io_current=eval(data['io_current'])
io_historical=eval(data['io_historical'])
#plpy.warning(str(io_current))

sumador= lambda l, key: sum(d[key] if d[key] is not None else 0 for d  in l)
sumadorproducto= lambda l, key1, key2: sum(d[key1]*d[key2] if d[key1] is not None and d[key2] is not None else 0 for d in l)

d_io={
    "price":sumador(io, 'price'),
}

shares=sumador(io_current, 'shares')
average_price_investment=0 if shares==0 else sumadorproducto(io_current, 'price_investment','shares')/shares

d_io_current={
    "balance_user":sumador(io_current, 'balance_user'),
    "balance_investment":sumador(io_current, 'balance_investment'),
    "balance_futures_user":sumador(io_current, 'balance_futures_user'),
    "gains_gross_user":sumador(io_current, 'gains_gross_user'),
    "gains_net_user":sumador(io_current, 'gains_gross_user'),
    "shares": shares,
    "average_price_investment": average_price_investment,
    "invested_user":sumador(io_current, 'invested_user'),
    "invested_investment":sumador(io_current, 'invested_investment'),
}

d_io_historical={
    "commissions_account":sumador(io_historical, 'commissions_account'),
    "gains_net_user":sumador(io_historical, 'gains_net_user'),
}

return [{ "io": str(d_io), "io_current": str(d_io_current),"io_historical":str(d_io_historical)}]
$_$;

