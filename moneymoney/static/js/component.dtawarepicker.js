// This class is used as a datetime input in django

class InputDatetime extends HTMLInputElement {
  constructor() {
    super();
    this.format_naive="YYYY-MM-DD HH:mm:ss";
    this.format_aware="YYYY-MM-DD HH:mm:ssZ";
  }

  connectedCallback(){
    if (this.hasAttribute("locale")){// Doesn't work in constructor and I don't know why.
        this.locale=this.getAttribute("locale");
    }else{
        this.locale="en";
    }
    
    if (this.hasAttribute("localzone")){
      this.localzone=this.getAttribute("localzone");
    }else{
      this.localzone="UTC";
    }

    
    this.parentNode.style.display="flex";//td
    
    this.div=document.createElement("div")
    this.div.hidden=true;
    
    this.button=document.createElement("button");
    this.button.setAttribute("type","button");
    this.button.innerHTML=">";
    this.button.addEventListener("click", (event) => {
        this.changeDisplay();
    });

    this.buttonToday=document.createElement("button");
    this.buttonToday.setAttribute("type","button");
    this.buttonToday.innerHTML="Today";
    this.buttonToday.addEventListener("click", (event) => {
      var dtaware=moment.tz(this.localzone);
      this.string2widget(dtaware.format("YYYY-MM-DD HH:mm:ss"));
      this.value=this.widget2string();
      
    });


    this.input=document.createElement("input");


    this.inputms=document.createElement("input")
    this.inputms.addEventListener('change', (event) => {
      this.value=this.widget2string();
    });

    this.select=document.createElement("select"); 
    for (let zone of moment.tz.names()) {
      this.select.innerHTML=this.select.innerHTML.concat(`<option value="${zone}">${zone}</option>`);
    }
    this.select.addEventListener('change', (event) => {
      this.value=this.widget2string();
    });

    this.select.value=this.localzone;

    this.div.appendChild(this.input);
    this.div.appendChild(this.inputms);
    this.div.appendChild(this.select);
    this.div.appendChild(this.buttonToday);
    this.div.style.display="flex";

    if (this.locale=="es"){
      this.firstDay=1;
    } else {
      this.firstDay=0;
    }

    jQuery(this.input).datetimepicker({
      inline:false,
      format:'Y-m-d H:i:s',
      dayOfWeekStart: this.firstDay,
    });
    
    var this_=this;
    jQuery(this.input).on('change', function () {
       this_.value=this_.widget2string();
     });
    
    jQuery.datetimepicker.setLocale(this.locale);

    this.insertAdjacentElement("afterend",this.button) ;
    this.button.insertAdjacentElement("afterend",this.div) ;
  }

  //Converts 3 widgets value to a string
  widget2string(){
    var dtaware=moment.tz(this.input.value, this.select.value);
    var date=dtaware.format("YYYY-MM-DD HH:mm:ss");
    var tz=dtaware.format("Z");
    return date.concat(".")+this.inputms.value + tz;
  }

  //Converts string to 3 widgets values 
  string2widget(s){
    var spl=s.split(".");
    if (spl.length==1){//Without ms 
      var dt=s.substring(0,19);
      var ms=0;
    } else {
        var dt=spl[0];
        var ms=spl[1].split("+")[0];        
    }
    this.input.value=dt;
    this.inputms.value=ms;
  }

  changeDisplay(){
    if (this.div.hidden==true){
      this.hidden=true;
      this.string2widget(this.value);
      this.div.hidden=false;
      this.button.innerHTML="<";
    } else {
      this.hidden=false;
      this.div.hidden=true;
      this.button.innerHTML=">";
    }
  }
}

window.customElements.define('input-datetime', InputDatetime, {extends: 'input'});
