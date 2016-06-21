// this part is for obtaining location to show warning about eligibility of contributor
var glocation = "";
function getLocation() {
    if (google.loader.ClientLocation) {
        glocation += google.loader.ClientLocation.address.country_code;
        glocation += ":";
        glocation += google.loader.ClientLocation.address.region;
        glocation += ":";
        glocation += google.loader.ClientLocation.address.city;
    }

    var re = /^(US|GB|CA|IE|AU)/;
    if (glocation.lastIndexOf('US', 0) !== 0) {
        document.getElementById("locationWarning").innerHTML = "This Job can be completed only by "
            + "native speakers of English from the USA, United Kingdom, Canada, Ireland, and Australia. "
            + "If it is found that this Job was completed from "
            + "any other location, then it will be automatically rejected.";
        document.getElementById("locationWarning").style.display = 'block';
    }
}
google.load("search", "1",{callback: getLocation});

//
// Helper functions for handling synchronous calls to our own server
// (getting tasks, validating codes)
//

var success = false;
var lastResponse = null;
var lastData = null;

// browser-independent cross-domain AJAX request
function createCrossDomainRequest(url, handler) {
    if (window.XDomainRequest) { // IE8
        return new window.XDomainRequest();
    } else {
        return new XMLHttpRequest();
    }
}
var invocation = createCrossDomainRequest();
var server_url = 'vystadial.ms.mff.cuni.cz:4443';
var valid_err_msg = 'The validation codes probably will not work. Check your internet connection' +
        'and/or try using a different browser (e.g., the latest version of Chrome).';


function callOtherDomain(value) {
    if (success)  // end early
        return;
    var url = 'https://' + server_url + '/?q=' + value;
    if (invocation) {
        if (window.XDomainRequest) { // IE8
            invocation.onload = outputResult;
            // false here makes the call synchronous
            invocation.open("GET", url, false);
            invocation.send();
        } else {
            invocation.open('GET', url, false);
            invocation.onreadystatechange = handler;
            invocation.send();
        }
    } else {
        var text = "Could not contact code validation server. " + valid_err_msg;
        alert(text);
    }
}

function handler(evtXHR) {
    if (invocation.readyState == 4) {
        if (invocation.status == 200) {
            outputResult();
        } else {
            alert("Error while contacting the validation server. " + valid_err_msg);
        }
    }
}

// This sets all inputs except the code field to enabled/disabled
// (only after the code is successfully verified, other inputs are enabled)
function set_input_disabled(value){
    var inputs = document.getElementsByTagName('input');
    // value for others + code field (true == all disabled except code field, and vice versa)
    for (var i = 0; i < inputs.length; ++i){
        if (inputs[i].className.indexOf('code_field') > - 1){
            // we use readonly for the code field so that it actually passes the data
            inputs[i].readonly = value ? '' : 'readonly';
        }
        else {
            inputs[i].disabled = value ? 'disabled' : '';
        }
    }
    document.getElementsByTagName('textarea')[0].disabled = value;
}

// Helper function: find input field with a particular class name
function get_input_field(name){
    var inputs = document.getElementsByTagName('input');
    for (var i = 0; i < inputs.length; ++i){
         if (inputs[i].className.indexOf(name) > - 1){
             return inputs[i];
         }
    }
    return null;
}

// check 'success' (if response is 'yes' for a valid code)
// store last response in the lastResponse variable
function outputResult() {
    var response = invocation.responseText;
    json = JSON.parse(response);
    if (json.response == "yes"){
        success = true;
        if (json.data){
            logdir_input = get_input_field('call_log_dir');
            logdir_input.value = json.data;
        }
        set_input_disabled(false); // enable all inputs
    }
    lastResponse = json.response;
    if (json.data){
        lastData = json.data;
    }
}

// CrowdFlower-recommended custom validation
// see https://success.crowdflower.com/hc/en-us/articles/201855879-Javascript-Guide-to-Customizing-a-CrowdFlower-Validator
// This if/else block is used to hijack the functionality of an existing validator (specifically: yext_no_international_url)
if (!_cf_cml.digging_gold) {
    CMLFormValidator.addAllThese([
        ['yext_no_international_url', {
            errorMessage: function() {
                return ('THIS CODE IS NOT VALID.');
            },
            validate: function(element, props) {
                // METHOD_TO_VALIDATE must return true or false
                return METHOD_TO_VALIDATE(element);
            }
        }]
    ]);
}
else {
    CMLFormValidator.addAllThese([
        ['yext_no_international_url', {
            validate: function(element, props) {
                return true;
            }
        }]
    ]);
}

// This is the method that will evaluate your validation
// value is the user submitted content of the form element you are validating
function METHOD_TO_VALIDATE(element) {
    var value = element.value;
    var re = /^[0-9]{4}$/;
    if (!re.test(value)){
        return false;
    }
    callOtherDomain(value);
    return success;
}

//
// Page initialization
//

// This is for loading a random task from the server on page load
function addOnloadEvent(fnc){
    if ( typeof window.addEventListener != "undefined" )
        window.addEventListener( "load", fnc, false );
    else if ( typeof window.attachEvent != "undefined" ) {
        window.attachEvent( "onload", fnc );
    }
    else {
        if ( window.onload !== null ) {
            var oldOnload = window.onload;
            window.onload = function ( e ) {
                oldOnload( e );
                window[fnc]();
            };
        }
        else
            window.onload = fnc;
    }
}

function load_task(){
    callOtherDomain('task');
    if (lastResponse !== null){
        var task_elem = document.getElementById('task');
        task_elem.innerHTML = '<strong>' + lastResponse + '</strong>';
    }
    task_text = get_input_field('task_text');
    task_text.value = lastResponse;
    task_text = get_input_field('task_data');
    task_text.value = lastData;
}

function init_page(){
    set_input_disabled(true);
    load_task();
}

addOnloadEvent(init_page);

//
// This adds collapse-uncollapse changing arrows
//
require(['jquery-noconflict'], function($) {
    //Ensure MooTools is where it must be
    Window.implement('$', function(el, nc){
    return document.id(el, nc, this.document);
});

var $ = window.jQuery;
//jQuery goes here

function toggle_collapse(e){
    var indicator = $(e.target).prev('.collapse-header').find('.toggle-indicator');
    if (e.type == 'show'){
        indicator.html('▴');
    }
    else {
        indicator.html('▾');
    }
}

// add toggle events for collapse headers
$(".collapse").on('show.bs.collapse', toggle_collapse);
$(".collapse").on('hide.bs.collapse', toggle_collapse);

// ensure the top-level instruction div is shown (un-collapsed)
$(".well").slideDown('fast');

});

