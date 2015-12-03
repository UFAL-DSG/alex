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

    if (glocation.lastIndexOf('US', 0) !== 0) {
        document.getElementById("locationWarning").innerHTML = "This Job can be completed only by "
            + "native speakers of English from USA. If it is found that this Job was completed from "
            + "other location than USA, then it will be automatically rejected.";
    }
}
google.load("search", "1",{callback: getLocation});

// this part is for calling synchronously my own web server
var success = false;
var lastResponse = null;

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
        var text = "No Invocation Took Place At All";
        alert(text);
    }
}

function handler(evtXHR) {
    if (invocation.readyState == 4) {
        if (invocation.status == 200) {
            outputResult();
        } else {
            alert("Invocation Errors Occurred");
        }
    }
}

// check 'success' (if response is 'yes' for a valid code)
// store last response in the lastResponse variable
function outputResult() {
    var response = invocation.responseText;
    json = JSON.parse(response);
    if (json.response == "yes")
        success = true;
    lastResponse = json.response;
}

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
    callOtherDomain(value);
    return success;
}

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
        var task = document.getElementById('task');
        task.innerHTML = '<strong>' + lastResponse + '</strong>';
    }
}

addOnloadEvent(load_task);
