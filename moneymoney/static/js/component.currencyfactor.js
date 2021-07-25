/* 
    This class is used as a currency factor input in django
    tags:
        - from. Currency ID: EUR, USD, ...
        - to. Currency ID
        - value
        
        To convert dolar to euros from is $ y to €
*/
class InputCurrencyFactor extends HTMLInputElement {
    constructor() {
        super();
    }

    connectedCallback(){
        if (this.hasAttribute("from")){// Doesn't work in constructor and I don't know why.
            this.from=this.getAttribute("from");
        } else {
            alert("You must set 'from' attribute");
        }
        if (this.hasAttribute("to")){// Doesn't work in constructor and I don't know why.
            this.to=this.getAttribute("to");
        } else {
            alert("You must set 'to' attribute");
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

        this.inputfrom=document.createElement("input");
        this.inputto=document.createElement("input");
        this.labelfrom=document.createElement("label");
        this.labelfrom.innerHTML=currency_symbol(this.from);
        this.labelto=document.createElement("label");
        this.labelto.innerHTML=currency_symbol(this.to);

        if (this.hasAttribute("value")){// Doesn't work in constructor and I don't know why.
            this.value=this.getAttribute("value");
            this.inputfrom.value=1;
            this.inputto.value=this.value;
        } else {
            alert("You must set 'value' attribute");
        }
        
        this.inputfrom.addEventListener('change', (event) => {
            this.calculate();
        });

        this.inputto.addEventListener('change', (event) => {
            this.calculate();
        });

        
        this.div.appendChild(this.inputfrom);
        this.div.appendChild(this.labelfrom);
        this.div.appendChild(this.inputto);
        this.div.appendChild(this.labelto);
        this.div.style.display="flex";

        this.insertAdjacentElement("afterend", this.button);
        this.button.insertAdjacentElement("afterend",this.div);
        
        this.calculate();
    }

    calculate(){
        this.value=my_round(parseFloat(this.inputto.value/this.inputfrom.value), 10);
    }

  changeDisplay(){
    if (this.div.hidden==true){
      this.hidden=true;
      this.div.hidden=false;
      this.button.innerHTML="<";
    } else {
      this.hidden=false;
      this.div.hidden=true;
      this.button.innerHTML=">";
    }
  }
};

window.customElements.define('input-currency-factor', InputCurrencyFactor, {extends: 'input'});
