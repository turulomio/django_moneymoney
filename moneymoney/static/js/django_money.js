
function localtime(value){
    if (value){
        var dateFormat = 'YYYY-MM-DD HH:mm:ss';
        var testDateUtc = moment.utc(value);
        var localDate = testDateUtc.local();
        return (localDate.format(dateFormat)); // 2015-30-01 02:00:00
    }
    console.log("REALLY");
    return null;
}   

const Range= class{
    constructor(value,percentage_down_decimal){
        this.value=value;
        this.percentage_down_decimal=percentage_down_decimal;
    }
    
    range_highest_value(){
        var points_to_next_high= this.value/(1-this.percentage_down_decimal)-this.value;
        return this.value+points_to_next_high/2;
    }
    
    range_lowest_value(){
        var points_to_next_low=this.value-this.value*(1-this.percentage_down_decimal);
        return this.value-points_to_next_low/2;
    }
        
    isInside(value){
        if (value<this.range_highest_value() && value>=this.range_lowest_value()){
            return true;
        } else {
            return false;
        }
    }
};

const RangeManager = class {
    constructor(guide_value, percentage_down_decimal) {
        this.percentage_down_decimal= percentage_down_decimal;
        this.ranges=[]
        var max_=guide_value;
        var min_=guide_value;
            
        var range_highest=max_*(1+this.percentage_down_decimal*10);//5 times up value
        var range_lowest=min_*(1-this.percentage_down_decimal*10);//5 times down value

        if (range_lowest<0.001) {//To avoid infinity loop
            range_lowest=0.001;
        }

        this.highest_range_value=10000000;
        var current_value=this.highest_range_value;
        while (current_value>range_lowest){
            if (current_value>=range_lowest && current_value<=range_highest){
                this.ranges.push(new Range(current_value, this.percentage_down_decimal));            
            }
            current_value=current_value*(1-this.percentage_down_decimal);
        }
    }
    
    print() {
        console.log(this.ranges);
    }
    
    get_range_index(value){
        for (var i = 0; i < this.ranges.length; i++) {
            if (this.ranges[i].isInside(value)){
                return i;
            }
        }
    }
    
    get_range(value){
        return this.ranges[this.get_range_index(value)];
    }
    
    // near 1 above, -1 below
    get_near_range(value, near){
        var index= this.get_range_index(value);
        return this.ranges[index-near];
    }
};


// Function to use "{0} {1}".format(a, b) style
String.prototype.format = function() {
    var formatted = this;
    for (var i = 0; i < arguments.length; i++) {
        var regexp = new RegExp('\\{'+i+'\\}', 'gi');
        formatted = formatted.replace(regexp, arguments[i]);
    }
    return formatted;
};

function currency_symbol(currency){
    if (currency=='EUR'){
        return '€';
    } 
    else if (currency=='USD'){
        return'$';
    }
    else if (currency=='u'){
        return'u';
    }
    else {
            return "???";
    }
}

function my_round(num, decimals = 2) {
    return Math.round(num*Math.pow(10, decimals))/Math.pow(10, decimals)
}

function percentage_generic_string(num, locale, decimals=2){
    if (isNaN(num)) return "- - - %"
    return "{0} %".format(my_round(num*100,decimals).toLocaleString(locale,{ minimumFractionDigits: decimals,  }));
}

function percentage_generic_html(num, locale, decimals=2){
    if (num>=0 || isNaN(num)){
        return "<span>{0}</span>".format(percentage_generic_string(num, locale, decimals))
    } else {
        return "<span class='vuered'>{0}</span>".format(percentage_generic_string(num, locale, decimals));
    }
}
function currency_generic_string(num, currency, locale, decimals=2){
    return "{0} {1}".format(my_round(num,decimals).toLocaleString(locale, { minimumFractionDigits: decimals,  }), currency_symbol(currency));
}

function currency_generic_html(num, currency, locale, decimals=2){
    if (num>=0){
        return currency_generic_string(num, currency, locale, decimals)
    } else {
        return "<span class='vuered'>{0}</span>".format(currency_generic_string(num, currency, locale, decimals));
    }
}

//Returns a float with . 
//1.234,56 € => 1234.56
//1,234.56USD => 1234.56
//1,234,567€ => 1234567
//1.234.567 => 1234567
//1,234.567 => 1234.567
//1.234 => 1234 // might be wrong - best guess
//1,234 => 1234 // might be wrong - best guess
//1.2345 => 1.2345
//0,123 => 0.123

function parseNumber(strg){
    strg = strg.toString().replace(',', '.');
    return parseFloat(strg);
}

// Function used in several project pages. Adding or updating strategies
function strategy_update_labels(cmbType){
    var additional1 = $('label[for="id_additional1"]');
    var additional2 = $('label[for="id_additional2"]');
    var additional3 = $('label[for="id_additional3"]');
    var additional4 = $('label[for="id_additional4"]');
    var additional5 = $('label[for="id_additional5"]');
    var additional6 = $('label[for="id_additional6"]');
    var additional7 = $('label[for="id_additional7"]');
    var additional8 = $('label[for="id_additional8"]');
    var additional9 = $('label[for="id_additional9"]');
    var additional10 = $('label[for="id_additional10"]');
    if (cmbType.selectedIndex=="0"){//Generic
        additional1.html(gettext("Additional 1"));
        additional2.html(gettext("Additional 2"));
        additional3.html(gettext("Additional 3"));
        additional4.html(gettext("Additional 4"));
        additional5.html(gettext("Additional 5"));
        additional6.html(gettext("Additional 6"));
        additional7.html(gettext("Additional 7"));
        additional8.html(gettext("Additional 8"));
        additional9.html(gettext("Additional 9"));
        additional10.html(gettext("Additional 10"));
        additional1.parent().parent().show();
        additional2.parent().parent().show();
        additional3.parent().parent().show();
        additional4.parent().parent().show();
        additional5.parent().parent().show();
        additional6.parent().parent().show();
        additional7.parent().parent().show();
        additional8.parent().parent().show();
        additional9.parent().parent().show();
        additional10.parent().parent().show();
    } else if (cmbType.selectedIndex=="1"){//Generic
        additional1.parent().parent().hide();
        additional2.parent().parent().hide();
        additional3.parent().parent().hide();
        additional4.parent().parent().hide();
        additional5.parent().parent().hide();
        additional6.parent().parent().hide();
        additional7.parent().parent().hide();
        additional8.parent().parent().hide();
        additional9.parent().parent().hide();
        additional10.parent().parent().hide();
    } else if (cmbType.selectedIndex=="2"){//Pairs in same account
        additional1.html(gettext("Worse product"));
        additional2.html(gettext("Best product"));
        additional3.html(gettext("Account"));
        additional1.parent().parent().show();
        additional2.parent().parent().show();
        additional3.parent().parent().show();
        additional4.parent().parent().hide();
        additional5.parent().parent().hide();
        additional6.parent().parent().hide();
        additional7.parent().parent().hide();
        additional8.parent().parent().hide();
        additional9.parent().parent().hide();
        additional10.parent().parent().hide();
    } else if (cmbType.selectedIndex=="3"){//Product ranges
        additional1.html(gettext("Product"));
        additional2.html(gettext("Percentage between ranges x1000"));
        additional3.html(gettext("Percentage gains x1000"));
        additional4.html(gettext("Amount"));
        additional5.html(gettext("Recomendation method"));
        additional6.html(gettext("Only first"));
        additional7.html(gettext("Account"));
        additional1.parent().parent().show();
        additional2.parent().parent().show();
        additional3.parent().parent().show();
        additional4.parent().parent().show();
        additional5.parent().parent().show();
        additional6.parent().parent().show();
        additional7.parent().parent().show();
        additional8.parent().parent().hide();
        additional9.parent().parent().hide();
        additional10.parent().parent().hide();
    }
    
}

function openInNewTab(href) {
  Object.assign(document.createElement('a'), {
    target: '_blank',
    href: href,
  }).click();
}

function common_vue_properties(){
    return {
        el: '#app',
        mixins: [mixin],
        delimiters: ['[[', ']]'],
        vuetify: new Vuetify({
            theme: {
                themes: {
                    light: {
                        primary: '#3a3987',
                    },
                },
            }
        }),
        
    }
}
function common_vue_properties_without_mixin(){
    return {
        el: '#app',
        delimiters: ['[[', ']]'],
        vuetify: new Vuetify({
            theme: {
                themes: {
                    light: {
                        primary: '#3a3987',
                    },
                },
            }
        }),
        
    }
}

function myheaders(){
    return {
        headers:{
//             'Accept-Language': `${this.$i18n.locale}-${this.$i18n.locale}`,
            'Content-Type':'application/json'
        }
    }
}
function if_null_script(value){
    if (value == null){
        return "-"
    }
    return value
}
function if_null_zero(value){
    if (value == null){
        return 0
    }
    return value
}
function if_null_empty(value){
    if (value == null){
        return ""
    }
    return value
}


function RulesIntegerRequired(maxdigits=10){
    return [
        v => !!v || gettext('Number is required'),
        v => (v && v.toString().length <=maxdigits) || gettext(`Number must be at most ${maxdigits} characters`),
        v => (v && !isNaN(parseInt(v))) || gettext('Must be a integer number')
    ]
}

function RulesFloatRequired(maxdigits=10){
    return [
        v => !!v || gettext('Number is required'),
        v => (v && v.toString().length <=maxdigits) || gettext(`Number must be at most ${maxdigits} characters`),
        v => (v && !isNaN(parseFloat(v))) || gettext('Must be a number')
    ]
}

function listobjects_sum(lo,key){
    return lo.reduce((accum,item) => accum + item[key], 0)
}

function listobjects_average_ponderated(lo,key1, key2){
    var prod=0;
    var total=0;
    var i;
    for (i = 0; i < lo.length; i++) {
        prod=prod+lo[i][key1]*lo[i][key2]
        total=total+lo[i][key2]
    } 
    return prod/total
}
