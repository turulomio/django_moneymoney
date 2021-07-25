from django.utils.translation import ugettext_lazy as _
def list_dt_to_jsarray(l):
    r="["
    for dt in l:
        r=r+f"new Date({dt.year}, {dt.month}, {dt.day}, {dt.hour}, {dt.minute}, {dt.second},  0),"
    r=r[:-1]+"]"
    print(r)
    return r
    
def dt_to_js(dt):
    return f"new Date({dt.year}, {dt.month}, {dt.day}, {dt.hour}, {dt.minute}, {dt.second},  0)"

def data_to_js(list_dt, list_values):
    r="["
    for i in range(list_dt):
        d="{"
        d=d+f" x: {dt_to_js(list_dt[i])},"
        d=d+f" y: {list_values[i]},"
        d=d+"}", 
    r=r[:-1]+"]"
    return r


def listdict_to_chartdata(listdict, key_x,  key_y):
    r="["
    for row in listdict:
        r=r+"{"
        r=r+f" x: {dt_to_js(row[key_x])},"
        r=r+f" y: {row[key_y]},"
        r=r+"},"
    r=r[:-1]+"]"
    return r
    
def listdict_with_ohcl_to_chartdata(listdict, key_date="date", key_open="open",  key_close="close", key_low="low",  key_high="high"):
    r="["
    for row in listdict:
        r=r+"{"
        r=r+f" t: new Date({row[key_date].year}, {row[key_date].month}, {row[key_date].day}, 0, 0, 0), "
        r=r+f" o: {row[key_open]},"
        r=r+f" h: {row[key_high]},"
        r=r+f" c: {row[key_close]},"
        r=r+f" l: {row[key_low]},"
        r=r+"},"
    r=r[:-1]+"]"
    return r


## CHART.JS
def chart_lines_total(listdict, local_currency):
    return f"""
<div style="width:75%;">
    <canvas id="canvas"></canvas>
</div>
<script>
    var timeFormat = 'YYYY-MM-DD HH:mm:SS';
    var config = {{
        type: 'line',
        data: {{
            labels: [],
            datasets: [
                {{
                    label: "{_("Total assets")}", 
                    data: {listdict_to_chartdata(listdict, "datetime", "total_user")},
                    backgroundColor:'rgb(255,0,0)',
                    borderColor: 'rgb(200,0,0)',
                    fill: false,
                }},
                {{
                    label: "{_("Invested assets")}", 
                    data: {listdict_to_chartdata(listdict, "datetime", "invested_user")},
                    backgroundColor:'rgb(0,255,0)',
                    borderColor: 'rgb(0,200,0)',
                    fill: false,
                }}, 
                {{
                    label: "{_("Investments assets")}", 
                    data: {listdict_to_chartdata(listdict, "datetime", "investments_user")},
                    backgroundColor:'rgb(0,0,255)',
                    borderColor: 'rgb(0,0,200)',
                    fill: false,
                }}, 
                {{
                    label: "{_("Accounts assets")}", 
                    data: {listdict_to_chartdata(listdict, "datetime", "accounts_user")},
                    backgroundColor:'rgb(0,255,255)',
                    borderColor: 'rgb(0,200,200)',
                    fill: false,
                }}, 
            ]
        }},
        options: {{
            title: {{
                display: true, 
                text: '{_("Total assets chart")}'
            }},
                scales: {{
                    xAxes: [{{
                        type: 'time',
                        distribution: 'series',
                        time: {{
                            unit: 'month', 
                            parser: timeFormat,
                        }},
                        scaleLabel: {{
                            display: true,
                        }}, 
                    }}],
                    yAxes: [{{
                        scaleLabel: {{
                            display: true,
                            labelString: '{local_currency}'
                        }}, 
                        ticks: {{
                            min: 0
                        }}, 
                    }}]
                }}
            }}
        }};

                        var ctx = document.getElementById('canvas').getContext('2d');
                        window.myLine = new Chart(ctx, config);
        </script>"""
## CHART.JS
def chart_product_quotes_historical(listdict, product):
    ## OJO CHART.JS DEBE ESTAR EN MISMA VERSION QUE FINANCIAL
    return f"""
<div style="width:75%;">
    <canvas id="canvas"></canvas>
</div>
<script>

var ctx = document.getElementById('canvas').getContext('2d');
var chart = new Chart(ctx, {{
        type: 'ohlc',
        data: {{
            datasets: [{{
                label: 'CHRT - Chart.js Corporation',
                data: {listdict_with_ohcl_to_chartdata(listdict)},

            }}]
        }}
}});
</script>"""
