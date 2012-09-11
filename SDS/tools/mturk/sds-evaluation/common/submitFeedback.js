/* 
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

function submitFeedback() {
    // check that all the input us provided
    if ( ($("input[name='Q1']").is(":checked")) &&
         ($("input[name='Q2']").is(":checked")) &&
         ($("input[name='Q3']").is(":checked")) &&
         ($("input[name='Q4']").is(":checked"))
        ) {
        var xmlFeedbackContent = getFeedback();
        var tokenValue = $("input[name='token']").val();

        // submit to voiphub
        $.post("submit.py",{token: tokenValue, xmlFeedback: xmlFeedbackContent},
            function(data) {

                //alert("Submit voiphub data: " + data);

                // after submiting to voiphub submit to mturk
                if (assignmentId != "ASSIGNMENT_ID_NOT_AVAILABLE" &&
                    assignmentId != "None") {

                    var mturk = "https://www.mturk.com/mturk/externalSubmit?"+
                        'assignmentId='+urlencode(assignmentId)+'&'+
                        'token='+urlencode(tokenValue)+'&'+
                        'xmlFeedback='+urlencode(xmlFeedbackContent);

                    window.location = mturk;
                }
                else {
                    alert("The feedback was submitted.\n\nPlease click on OK for the next task.");
                    window.location.reload(true)
                }
            });

        $("input[name='token']").val('');
    }
    else
        $("#feedback-error").text("Please fill in the feedback form.").addClass("feedback-error");

    return false;
}
