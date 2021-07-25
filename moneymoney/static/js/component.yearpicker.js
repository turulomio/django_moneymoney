// This component is part of the https://github.com/turulomio/reusingcode project
// Make a pull request to this project to update this file

class SelectorYear extends HTMLElement {
  constructor() {
    super();
  }

  connectedCallback(){
    if (this.hasAttribute("title")==true){
        this.title=this.getAttribute("title");
    } else{
      this.title="Select a year";
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

    if (this.hasAttribute("year")==true){
      this.year=parseInt(this.getAttribute("year"));
    }else {
      this.year=today.getFullYear();
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


    this.cmdYearPrevious=document.createElement("button"); 
    this.cmdYearPrevious.innerHTML = "<";
    this.cmdYearNext=document.createElement("button");
    this.cmdYearNext.innerHTML = ">";
    this.cmdCurrent=document.createElement("button");
    this.cmdCurrent.innerHTML = "Current";
    if (this.url != null){
      this.cmdGo=document.createElement("button");
      this.cmdGo.innerHTML = "Go";

      this.cmdGo.addEventListener('click', (event) => {

        var newurl=this.url.concat(this.year.toString()).concat("/");
        window.location.replace(newurl);
      });
    }



    this.appendChild(this.label);
    this.appendChild(this.cmdYearPrevious);
    this.appendChild(this.selYear);
    this.appendChild(this.cmdYearNext);
    this.appendChild(this.cmdCurrent);
    this.appendChild(this.cmdGo);
    this.selYear.value=this.year;


    this.cmdYearPrevious.addEventListener('click', (event) => {
      this._render(this.year,this.year-1);
    });
    this.cmdYearNext.addEventListener('click', (event) => {
      this._render(this.year,this.year+1);
    });
    this.cmdCurrent.addEventListener('click', (event) => {
        this._render(this.year,today.getFullYear());
    });
    this.selYear.addEventListener('change', (event) => {
        this._render(this.year,this.selYear.value);
    });
  }

  //Try to change or return the old position with an alert
  _render( old_year, new_year,){
    if (new_year>this.year_end){
      this.year=old_year;
      alert("You can't set the next year");
    }
    else if (new_year<this.year_start){
      this.year=old_year;
      alert("You can't set the previous year");
    }
    else {
      this.year=new_year;
    }
    this.selYear.value=this.year;
  }

}

window.customElements.define('selector-year', SelectorYear);
