// This component is part of the https://github.com/turulomio/reusingcode project
// Make a pull request to this project to update this file

// This component shows a button
// After clicking makes and ajax connection
// parameters:
//   - id. Name of the element 
//   - url. Ajax request url
//   - buttontext. Button text
//   - showbuttonafter. Attribute without value. If missing hides the button after connection
//   - csrf_token
class AjaxButton extends HTMLElement {
  constructor() {
    super();
  }

  connectedCallback(){
    if (this.hasAttribute("id")==true){
        this.id=this.getAttribute("id");
    } else{
      this.id="ajax_button";
    }
    

    if (this.hasAttribute("url")==true){
      this.url=this.getAttribute("url");
    } else{
      alert("An ajax-button component must have an url attribute");
    }

    if (this.hasAttribute("buttontext")==true){
      this.buttontext=this.getAttribute("buttontext");
    } else{
      this.buttontext="Press me";
    }

    if (this.hasAttribute("csrf_token")==true){
      this.csrf_token=this.getAttribute("csrf_token");
    } else{
      alert("An ajax-button component must have a csrf_token attribute");
    }

    if (this.hasAttribute("showbuttonafter")==false){
      this.showbuttonafter=false;
    } else{
      this.showbuttonafter=true;
    }

    this.form=document.createElement("form");
    this.form.setAttribute("method", "post");
    this.appendChild(this.form);

    this.button=document.createElement("button");
    this.button_id=this.id+"_button";
    this.button.setAttribute("id", this.button_id);
    this.button.setAttribute("type", "submit");
    this.button.innerHTML=this.buttontext;
    this.form.appendChild(this.button);

    this.div=document.createElement("div");
    this.div_id=this.id+"_div";
    this.div.setAttribute("id", this.id+"_div");
    this.appendChild(this.div);

    this.button.addEventListener('click', (event) => this.ajax_method(event,this));
  }

  //This_ is needed due to scope reasons
  ajax_method(event, this_){
        event.preventDefault();
        $.ajax({
            type: "POST",
            url: this_.url,
            data: {
                 csrfmiddlewaretoken: this_.csrf_token,
            },
            success: function(result) {
                $("#"+this_.id+"_div").html(result);
                if (this_.showbuttonafter==false){
                  $("#"+this_.button_id).hide();
                }
           },
           error: function(result) {
                $("#"+this_.div_id).html('<p>"Something is wrong"</p>');
           }
        });
  }
  
 
}
window.customElements.define('ajax-button', AjaxButton);
