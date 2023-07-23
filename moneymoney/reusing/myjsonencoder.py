from datetime import datetime, date, timedelta, time
from decimal import Decimal
from json import JSONEncoder, dumps, loads
from base64 import b64encode, b64decode

# Forma en que debe parsearse los Decimals
class DecimalsWay:
    Decimal=1  #Uses a String with decimal to detect decimals
    String=2
    Float=3

## Usa
class MyJSONEncoder(JSONEncoder):
    # Part of this code is from https://github.com/django/django/blob/main/django/core/serializers/json.py
    # JSONEncoder subclass that knows how to encode date/time, decimal types, and UUIDs.
    def _get_duration_components(self, duration):
        days = duration.days
        seconds = duration.seconds
        microseconds = duration.microseconds

        minutes = seconds // 60
        seconds %= 60


        hours = minutes // 60
        minutes %= 60

        return days, hours, minutes, seconds, microseconds
    
    def _duration_iso_string(self, duration):
        if duration < timedelta(0):
            sign = "-"
            duration *= -1
        else:
            sign = ""

        days, hours, minutes, seconds, microseconds = self._get_duration_components(duration)
        ms = ".{:06d}".format(microseconds) if microseconds else ""
        return "{}P{}DT{:02d}H{:02d}M{:02d}{}S".format(
            sign, days, hours, minutes, seconds, ms
        )
    
    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, date):
            return o.isoformat()
        elif isinstance(o, time):
            if o.utcoffset() is not None: #If it's aware
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, timedelta):
            return self._duration_iso_string(o)
        elif isinstance(o, Decimal):
            return f"Decimal('{o}')"
        elif o.__class__.__name__ in ("Promise", "__proxy__"): #django.utils.functional
            return str(o)
        elif isinstance(o, bytes):
            return b64encode(o).decode("UTF-8")
        elif o.__class__.__name__=="Percentage":
            return o.value
        elif o.__class__.__name__=="Currency":
            return o.amount
        else:
            return super().default(o)

## Usa decimals como floats normalmwente para JS
class MyJSONEncoderDecimalsAsString(MyJSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        else:
            return super().default(o)
            
## Usa decimals como floats normalmwente para JS
class MyJSONEncoderDecimalsAsFloat(MyJSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        else:
            return super().default(o)

                
def MyJSONEncoder_dumps(r, indent=4):
    return dumps(r, cls=MyJSONEncoder, indent=indent)
                
def MyJSONEncoderDecimalsAsString_dumps(r, indent=4):
    return dumps(r, cls=MyJSONEncoderDecimalsAsString, indent=indent)
                
def MyJSONEncoderDecimalsAsFloat_dumps(r, indent=4):
    return dumps(r, cls=MyJSONEncoderDecimalsAsFloat, indent=indent)

def get_date(s):
    try:
        return date.fromisoformat(s)
    except:
        return None 
        
def get_datetime(s):
    try:
        return datetime.fromisoformat(s)
    except:
        return None 
        
#    Parse the ISO8601 duration string as hours, minutes, seconds
def get_timedelta(str):
#    try:
## https://stackoverflow.com/questions/36976138/is-there-an-easy-way-to-convert-iso-8601-duration-to-timedelta
## Parse the ISO8601 duration as years,months,weeks,days, hours,minutes,seconds
## Returns: milliseconds
## Examples: "PT1H30M15.460S", "P5DT4M", "P2WT3H"
    def get_isosplit(str, split):
        if split in str:
            n, str = str.split(split, 1)
        else:
            n = '0'
        return n.replace(',', '.'), str  # to handle like "P0,5Y"

    str = str.split('P', 1)[-1]  # Remove prefix
    s_yr, str = get_isosplit(str, 'Y')  # Step through letter dividers
    s_mo, str = get_isosplit(str, 'M')
    s_wk, str = get_isosplit(str, 'W')
    s_dy, str = get_isosplit(str, 'D')
    _, str    = get_isosplit(str, 'T')
    s_hr, str = get_isosplit(str, 'H')
    s_mi, str = get_isosplit(str, 'M')
    s_sc, str = get_isosplit(str, 'S')
    n_yr = float(s_yr) * 365   # approx days for year, month, week
    n_mo = float(s_mo) * 30.4
    n_wk = float(s_wk) * 7
    dt = datetime.timedelta(days=n_yr+n_mo+n_wk+float(s_dy), hours=float(s_hr), minutes=float(s_mi), seconds=float(s_sc))
    print(dt)
    return int(dt.total_seconds()*1000) ## int(dt.total_seconds()) | dt
#    except:
#        return None 
        
def get_time(s):
    try:
        if not ":" in s:
            return None
        return time.fromisoformat(s)
    except:
        return None 
        
def get_bytes(s):
    try:
        return b64decode(s)
    except:
        return None
        
def get_Decimal(s):
    try:
        return eval(s)
    except:
        return None

def MyJSONEncoder_loads(s):
    return loads(s, object_hook=hooks_MyJSONEncoder)

def MyJSONEncoderDecimalsAsFloat_loads(s):
    return loads(s, object_hook=hooks_MyJSONEncoderAsFloat)        

def MyJSONEncoderDecimalsAsString_loads(s):
    return loads(s, object_hook=hooks_MyJSONEncoderAsString)
    
def guess_cast(o, decimal_way):
    if decimal_way==DecimalsWay.Decimal:
        r=get_Decimal(o)
        if r is not None:
            return  r

    r=get_date(o)
    if r is not None:
        return  r
        
    r=get_datetime(o)
    if r is not None:
        return  r
        
    r=get_time(o)
    if r is not None:
        return  r
        
    r=get_bytes(o)
    if r is not None:
        return  r
    
    return o
    
def hooks(iter_value, decimals_way):
    """
        Iterates a dict or list to cast decimals and dtaware in json.loads using objeck_hook
    """
    if isinstance(iter_value, dict):
        for k, v in iter_value.items():
            if isinstance(v, dict):
                iter_value[k]=hooks(v, decimals_way)
            elif isinstance(iter_value, list):
                for i in v:
                    i=hooks(v, decimals_way)
            else:
                iter_value[k]=guess_cast(v, decimals_way)
    elif isinstance(iter_value, list):
        for i in v:
            i=hooks(i, decimals_way)
    return iter_value
    
def hooks_MyJSONEncoder(iter_value):
    return hooks(iter_value, DecimalsWay.Decimal)
    
def hooks_MyJSONEncoderAsFloat(iter_value):
    return hooks(iter_value, DecimalsWay.Float)
    
def hooks_MyJSONEncoderAsString(iter_value):
    return hooks(iter_value, DecimalsWay.String)


if __name__ == '__main__':
    from datetime import timezone    
    d={}
    d["None"]=None
    d["Integer"]=12112
    d["Float"]=12121.1212
    d["Date"]=date.today()
    d["Datetime"]=datetime.now()
    d["Timedelta"]=timedelta(hours=4, days=2, minutes=12,  seconds=12)
    d["Time"]=time(12, 12, 12, 123456)
    d["Datetime aware"]=d["Datetime"].replace(tzinfo=timezone.utc)
    d["Bytes"]=b"Byte array"
    d["Decimal"]=Decimal("12.12123414")
    print ("Dictionary")
    print(d)
    print()
    print ("MyJSONEncoder_dumps")
    print (MyJSONEncoder_dumps(d))
    print()
    print ("MyJSONEncoder_loads")
    print(MyJSONEncoder_loads(MyJSONEncoder_dumps(d)))
    print()
    print ("MyJSONEncoderDecimalsAsFloat_dumps")
    print (MyJSONEncoderDecimalsAsFloat_dumps(d))
    print()
    print ("MyJSONEncoderDecimalsAsFloat_loads")
    print(MyJSONEncoderDecimalsAsFloat_loads(MyJSONEncoderDecimalsAsFloat_dumps(d)))
    print()
    print ("MyJSONEncoderDecimalsAsString_dumps")
    print (MyJSONEncoderDecimalsAsString_dumps(d))
    print()
    print ("MyJSONEncoderDecimalsAsString_loads")
    print(MyJSONEncoderDecimalsAsString_loads(MyJSONEncoderDecimalsAsString_dumps(d)))
    print()
