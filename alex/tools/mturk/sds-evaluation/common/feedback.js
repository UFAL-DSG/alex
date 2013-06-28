/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

function stripSpaces(x) {
    return (x.replace(/^\W+/,'')).replace(/\W+$/,'');
}

function urlencode(s) {
    s = encodeURIComponent(s);
    return s.replace(/~/g,'%7E').replace(/%20/g,'+');
}

function disableByName(name) {
    var elems = $('input, select, textarea, button');
    for (var i = 0; i < elems.length; i++) {
        if (elems[i].name == name)
            elems[i].disabled=true;
    }
}

function enableByName(name) {
    var elems = $('input, select, textarea, button');
    for (var i = 0; i < elems.length; i++) {
        if (elems[i].name == name)
            elems[i].disabled=false;
    }
}

function disableFeedback() {
    $("#feedback").addClass("disabled");
    disableByName('Q1');
    disableByName('Q2');
    disableByName('Q3');
    disableByName('Q4');
    disableByName('comments');
    disableByName('contact');
    disableByName('submit');
}

function disableToken() {
    disableByName('token');
}
function enableFeedback() {
    $("#feedback").removeClass("disabled");
    enableByName('Q1');
    enableByName('Q2');
    enableByName('Q3');
    enableByName('Q4');
    enableByName('comments');
    enableByName('contact');
    enableByName('submit');
}

function validateToken(str)
{
    if (str.length==0)
    {
        document.getElementById("tokenvalid").innerHTML="Invalid";
        document.getElementById("tokenvalid").style.border="1px solid #A5ACB2";
        document.getElementById("tokenvalid").style.background="red";

        disableFeedback();
        $("#token").addClass("invalid");
        $("#token").removeClass("valid");

        return;
    }
    if (window.XMLHttpRequest)
    {// code for IE7+, Firefox, Chrome, Opera, Safari
        xmlhttp=new XMLHttpRequest();
    }
    else
    {// code for IE6, IE5
        xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
    }
    xmlhttp.onreadystatechange=function()
    {
        if (xmlhttp.readyState==4 && xmlhttp.status==200)
        {
            response = stripSpaces(xmlhttp.responseText);

            if (response == "Invalid") {
                document.getElementById("tokenvalid").innerHTML=response;
                document.getElementById("tokenvalid").style.background="red";
                disableFeedback();
                $("#token").addClass("invalid");
                $("#token").removeClass("valid");
            }
            else if (response == "Valid") {
                document.getElementById("tokenvalid").innerHTML=response;
                document.getElementById("tokenvalid").style.background="#00FF00";
                enableFeedback();
                $("#token").removeClass("invalid");
                $("#token").addClass("valid");
            }
            else {
                document.getElementById("tokenvalid").innerHTML="Error"
                document.getElementById("tokenvalid").style.background="red";
                disableFeedback();
                $("#token").addClass("invalid");
                $("#token").removeClass("valid");
            }

            document.getElementById("tokenvalid").style.border="1px solid #A5ACB2";
            document.getElementById("tokenvalid").style.padding="3px";
        }
    }
    xmlhttp.open("GET","validate-token.py?token="+str,true);
    xmlhttp.setRequestHeader("If-Modified-Since", "Thu, 1 Jan 1970 00:00:00 GMT");
    xmlhttp.setRequestHeader("Cache-Control", "no-cache");
    xmlhttp.send();
}

function workerOuterIp() {return "";}
function workerInnerIp() {return "";}

function workerDn() {
    var gloc = ""
    if (google.loader.ClientLocation) {
      gloc += google.loader.ClientLocation.address.country_code;
      gloc += ":";
      gloc += google.loader.ClientLocation.address.region;
      gloc += ":";
      gloc += google.loader.ClientLocation.address.city;
      return gloc;
    }
    return "-noloc-";
}

function getFeedback() {
    var token = $("input[name='token']").val();
    var Q1 = $("input[name='Q1']:checked").val();
    var Q2 = $("input[name='Q2']:checked").val();
    var Q3 = $("input[name='Q3']:checked").val();
    var Q4 = $("input[name='Q4']:checked").val();
    var comments = $("textarea[name='comments']").val();

    var xmlFeedback = "";

    xmlFeedback += "<feedback>\n";
    xmlFeedback += "<question id=\"1\" name=\"Did you find all the information "+
        "you were looking for?\">" + Q1 + "</question>\n";
    xmlFeedback += "<question id=\"2\" name=\"The system understood me well.\">"
        + Q2 + "</question>\n";
    xmlFeedback += "<question id=\"3\" name=\"The phrasing of the system's "+
        "responses was good.\">" + Q3 + "</question>\n";
    xmlFeedback += "<question id=\"4\" name=\"The system's voice was of good "+
        "quality.\">" + Q4 + "</question>\n";
    xmlFeedback += "<comments>" + comments + "</comments>\n";
    xmlFeedback += "<contact></contact>\n";

    // the task specification and mturk assignment
    xmlFeedback += "<token>"+token+"</token>\n";
    xmlFeedback += "<dialogueId></dialogueId>\n";  // proper dialogueId will be inserted on the server side based on the token
    xmlFeedback += "<assignmentId>" + assignmentId + "</assignmentId>\n";
    xmlFeedback += "<workerId>" + workerId + "</workerId>\n";
    xmlFeedback += "<hitId>" + hitId + "</hitId>\n";
    xmlFeedback += "<workerOuterIp>" + workerOuterIp() + "</workerOuterIp>\n";
    xmlFeedback += "<workerInnerIp>" + workerInnerIp() + "</workerInnerIp>\n";
    xmlFeedback += "<workerDn>" + workerDn() + "</workerDn>\n";
    xmlFeedback += "<goal>" + goal + "</goal>\n";
    xmlFeedback += "<task>" + task + "</task>\n";

    xmlFeedback += "</feedback>\n";

    return xmlFeedback;
}

function updateSelectedStyle() {
    $('input:radio').removeClass('focused').next().removeClass('focused');
    $('input:radio:checked').addClass('focused').next().addClass('focused');
}

$(document).ready(function() {
    $('input:radio').focus(updateSelectedStyle);
    $('input:radio').blur(updateSelectedStyle);
    $('input:radio').change(updateSelectedStyle);
})
