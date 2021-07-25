
class InputDate extends HTMLInputElement {
  constructor() {
    super();
  }

  connectedCallback(){
    if (this.hasAttribute("locale")){// Doesn't work in constructor and I don't know why.
        this.locale=this.getAttribute("locale");
    }else{
        this.locale="en";
    }
    if (this.locale=="es"){
      this.firstDay=1;
    } else {
      this.firstDay=0;
    }




    jQuery(this).datepicker({
      constrainInput: true,   // prevent letters in the input field
      inline:false,
      format: 'Y-m-d',
    });
    if (this.locale=="es"){
      $.datepicker.regional['es'] = {
        monthNames: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
        monthNamesShort: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
        dayNames: ['Domingo', 'Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado'],
        dayNamesShort: ['Dom', 'Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab'],
        dayNamesMin: ['Do', 'Lu', 'Ma', 'Mc', 'Ju', 'Vi', 'Sa'],
        dateFormat: 'yy-m-d',
        firstDay: 1, 
      }
      $.datepicker.setDefaults($.datepicker.regional['es']);
    }
  }
}

window.customElements.define('input-date', InputDate, {extends: 'input'});
