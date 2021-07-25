// This component is part of the https://github.com/turulomio/reusingcode project
// Make a pull request to this project to update this file

// This component shows a button
// After clicking makes and ajax connection
// parameters:
//   - id. Name of the element 
//   - closed. Doesn't show, By default is showed. Attribute without value

// IMPORTANT
// TO ACCESS ModalWindow innerHTML 
// var lblResult=document.querySelector("#sellingpriceResult");


class ModalWindow extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback(){
        this.template=document.createElement("template");
        this.template.innerHTML=`<style>
    body {font-family: Arial, Helvetica, sans-serif;}

    /* The Modal (background) */
    .modal {
    display: none; /* Hidden none, Modal: block*/
    position: fixed; /* Stay in place */
    z-index: 1; /* Sit on top */
    padding-top: 100px; /* Location of the box */
    left: 0;
    top: 0;
    width: 100%; /* Full width */
    height: 100%; /* Full height */
    overflow: auto; /* Enable scroll if needed */
    background-color: rgb(0,0,0); /* Fallback color */
    background-color: rgba(0,0,0,0.4); /* Black w/ opacity */
    }

    /* Modal Content */
    .modal-content {
    background-color: #fefefe;
    margin: auto;
    padding: 20px;
    border: 1px solid #888;
    width: 80%;
    }

    /* The Close Button */
    #close {
    color: #aaaaaa;
    float: right;
    font-size: 28px;
    font-weight: bold;
    }

    #close:hover,
    #close:focus {
    color: #000;
    text-decoration: none;
    cursor: pointer;
    }
    </style>
    <!-- The Modal -->
    <div id="myModal" class="modal">
        <!-- Modal content -->
        <div class="modal-content">
            <span id="close">&times;</span>
            <div id="innermodal"><slot></slot></div>
        </div>
    </div>
    `;
        this.shadow=this.attachShadow({mode: 'closed'});
        this.shadow.appendChild(this.template.content.cloneNode(true));
        this.span=this.shadow.querySelector("#close");
        this.modal=this.shadow.querySelector("#myModal");
        
        
        if (this.hasAttribute("closed")==false){// Doesn't work in constructor and I don't know why.
            this.modal.style.display = "block";
        }
        
        
        // When the user clicks on <span> (x), close the modal
        var this_=this;
        this.span.onclick = function() {
            this_.close();
        }
    }
    

    show() {
        this.modal.style.display="block";
        if (this.hasAttribute("closed")){
            this.removeAttribute("closed");
        }
    }
  
    close() {
        this.modal.style.display="none";
        if (this.hasAttribute("closed")==false){
            this.setAttribute("closed","");
        }
    }
}
window.customElements.define('modal-window', ModalWindow);
