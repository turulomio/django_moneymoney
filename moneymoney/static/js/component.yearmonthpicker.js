// This component is part of the https://github.com/turulomio/reusingcode project
// Make a pull request to this project to update this file

class SelectorYearMonth extends HTMLElement {
  constructor() {
    super();
  }

  connectedCallback(){
    if (this.hasAttribute("title")==true){
        this.title=this.getAttribute("title");
    } else{
      this.title="Select a year and a month";
    }

    if (this.hasAttribute("url")==true){
      this.url=this.getAttribute("url");
    } else{
      this.title=null;
    }

    var today=new Date();

    if (this.hasAttribute("year_start")==true){
      this.year_start=parseInt(this.getAttribute("year_start"));
    }else {
      this.year_start=today.getFullYear()-3;
    }

    if (this.hasAttribute("year_end")==true){
      this.year_end=parseInt(this.getAttribute("year_end"));
    }else {
      this.year_end=today.getFullYear()+3;
    }
    
    if (this.hasAttribute("month_start")==true){
      this.month_start=parseInt(this.getAttribute("month_start"));
    }else {
      this.month_start=1;
    }
    
    if (this.hasAttribute("month_end")==true){
      this.month_end=parseInt(this.getAttribute("month_end"));
    }else {
      this.month_end=12;
    }    
    if (this.hasAttribute("year")==true){
      this.year=parseInt(this.getAttribute("year"));
    }else {
      this.year=today.getFullYear();
    }    
    if (this.hasAttribute("month")==true){
      this.month=parseInt(this.getAttribute("month"));
    }else {
      this.month=today.getMonth()+1;
    }

    this.label=document.createElement("label");
    this.label.innerHTML=this.title + " ";

    this.selYear=document.createElement("select");
    for (var i=0; i< this.year_end-this.year_start+1; i++){
      var option= document.createElement("option");
      option.value=this.year_start + i;
      option.text=this.year_start+i;
      this.selYear.appendChild(option);
    }


    this.selMonth=document.createElement("select");
    this.selMonth.innerHTML=`
    <option value="1">January</option>
    <option value="2">Febuary</option>
    <option value="3">March</option>
    <option value="4">April</option>
    <option value="5">May</option>
    <option value="6">June</option>
    <option value="7">July</option>
    <option value="8">August</option>
    <option value="9">September</option>
    <option value="10">October</option>
    <option value="11">November</option>
    <option value="12">December</option>`;


    this.cmdYearPrevious=document.createElement("button"); 
    this.cmdYearPrevious.innerHTML = "<<";
    this.cmdYearNext=document.createElement("button");
    this.cmdYearNext.innerHTML = ">>";
    this.cmdMonthPrevious=document.createElement("button");
    this.cmdMonthPrevious.innerHTML = "<";
    this.cmdMonthNext=document.createElement("button");
    this.cmdMonthNext.innerHTML = ">";
    this.cmdCurrent=document.createElement("button");
    this.cmdCurrent.innerHTML = "Current";
    if (this.url != null){
      this.cmdGo=document.createElement("button");
      this.cmdGo.innerHTML = "Go";

      this.cmdGo.addEventListener('click', (event) => {

        var newurl=this.url.concat(this.year.toString()).concat("/").concat((this.month).toString());
        window.location.replace(newurl);
      });
    }



    this.appendChild(this.label);
    this.appendChild(this.cmdYearPrevious);
    this.appendChild(this.cmdMonthPrevious);
    this.appendChild(this.selMonth);
    this.appendChild(this.selYear);
    this.appendChild(this.cmdMonthNext);
    this.appendChild(this.cmdYearNext);
    this.appendChild(this.cmdCurrent);
    this.appendChild(this.cmdGo);
    this.selYear.value=this.year;
    this.selMonth.value=this.month;


    this.cmdYearPrevious.addEventListener('click', (event) => {
      this._render(this.year,this.month,this.year-1,this.month);
    });
    this.cmdYearNext.addEventListener('click', (event) => {
      this._render(this.year,this.month,this.year+1,this.month);
    });
    this.cmdMonthPrevious.addEventListener('click', (event) => {
      if (this.month==1){
        this._render(this.year,this.month,this.year-1,12);
      } else {
        this._render(this.year,this.month,this.year,this.month-1);
      }
    });
    this.cmdMonthNext.addEventListener('click', (event) => {
      if (this.month==12){
        this._render(this.year,this.month,this.year+1,1);
      } else {
        this._render(this.year,this.month,this.year,this.month+1);
      }
    });
    this.cmdCurrent.addEventListener('click', (event) => {
        this._render(this.year,this.month,today.getFullYear(),today.getMonth()+1);
    });
    this.selMonth.addEventListener('change', (event) => {
        this._render(this.year,this.month,this.selYear.value,this.selMonth.value);
    });
    this.selYear.addEventListener('change', (event) => {
        this._render(this.year,this.month,this.selYear.value,this.selMonth.value);
    });
    
  }

  //Try to change or return the old position with an alert
  _render( old_year,old_month, new_year, new_month){
    if (new_year>this.year_end){
      this.year=old_year;
      this.month=old_month;
      alert("You can't set the next year");
    }
    else if (new_year==this.year_end && new_month>this.month_end){
      this.year=old_year;
      this.month=old_month;
      alert("You can't set the next month");
    }
    else if (new_year<this.year_start){
      this.year=old_year;
      this.month=old_month;
      alert("You can't set the previous year");
    }
    else if (new_year==this.year_start && new_month<this.month_start){
      this.year=old_year;
      this.month=old_month;
      alert("You can't set the previous month");
    }
    else {
      this.year=new_year;
      this.month=new_month;

    }
    this.selYear.value=this.year;
    this.selMonth.value=this.month;
  }

}

window.customElements.define('selector-yearmonth', SelectorYearMonth);
