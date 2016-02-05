// CF JQuery Hack
require(['jquery-noconflict'], function($) {

  //Ensure MooTools is where it must be
  Window.implement('$', function(el, nc){
    return document.id(el, nc, this.document);
  });

  var $ = window.jQuery;
  //jQuery goes here

  // *****
  // VALIDATION
  // *****

  // browser-independent cross-domain AJAX request
  function createCrossDomainRequest(url, handler) {
    if (window.XDomainRequest) { // IE8
      return new window.XDomainRequest();
    } else {
      return new XMLHttpRequest();
    }
  }

  var request = createCrossDomainRequest();
  var serverURL = 'vystadial.ms.mff.cuni.cz:4447';
  var validationErrMsg = 'Fluency validation is not working. You will not be able to submit ' +
      'the task. Check your internet connection and/or try using a different browser (e.g., the ' +
      'latest version of Chrome).';

  // call the validation server and return the result
  function requestExternalValidation(userText, requiredData) {

    // build request URL
    var url = 'https://' + serverURL + '/?rd=' + encodeURIComponent(requiredData.join()) +
        '&ut=' + encodeURIComponent(userText);

    // send the request
    if (request) {
      // 'false' makes the call synchronous, so send() won't return before it's finished
      request.open('GET', url, false);
      request.send();
    }
    else {
      alert("Could not contact the server. " + validationErrMsg);
      return null;
    }

    // return the reply
    if (request.status == 200) {
      var response = request.responseText;
      json = JSON.parse(response);
      return json;
    }
    else {
      alert("Error while contacting the server. " + validationErrMsg);
      return null;
    }
  }

  // local validation -- just check that all data are included in the answers
  function performLocalValidation(value, data){

    // check if disallowed characters are present
    if (value.match(/[^0-9A-Za-z '?.!;,:-]/)){
      return 'Your reply contains weird characters. ' +
          'Use only the English alphabet and basic punctuation.';
    }

    // check for missing information (case-insensitive)
    missingStr = '';
    lcValue = value.toLowerCase();
    for (var i = 0; i < data.length; ++i){
      lcData = data[i].toLowerCase();
      if (lcValue.indexOf(lcData) == -1){
        missingStr += ', ' + data[i];
      }
    }
    if (missingStr !== ''){
      return 'Your reply is missing the following information: ' +
          missingStr.substring(2);
    }

    // check for sufficient number of tokens
    toks = ' ' + value + ' ';  // pad with spaces for easy regexes
    for (var i = 0; i < data.length; ++i){
      toks = toks.replace(data[i], 'DATA' + i);
    }
    toks = toks.replace(/([?.!;,:-]+)/g, " $1 ");
    toks = toks.replace(/\s+/g, " ");
    toks = toks.substring(1, toks.length - 1);  // remove the padding spaces
    toks = toks.split(" ");

    if (toks.length < 2 * data.length || toks.length < data.length + 3){
      return 'Your reply is too short. Use full, fluent sentences.';
    }

    return null;
  }

  function getDataItemsFor(element){
    var res = [];
    $(element).closest('.html-element-wrapper').find('em.data').find('span').each(
        function(){ res.push($(this).text()) }
    );
    return res;
  }

  // main validation method, gather data and perform local and external validation
  function validate(element) {
    var value = element.value;
    var data = getDataItemsFor(element);

    if (performLocalValidation(value, data) !== null){
      return false;
    }

    // find the corresponding hidden field
    var fluencyField = $(element).closest('.html-element-wrapper').find('.fluency_assessment')[0];
    if (fluencyField.value){  // language ID validation already performed
      var fluencyData = JSON.parse(fluencyField.value);

      if (fluencyData.result == 'yes'){
        return true;  // once the validation passes, always return true
      }
      if (fluencyData.text == value){
        return false; // never run twice for the same text
      }
    }

    // run the external validation, return its result
    var fluencyData = requestExternalValidation(value, data);
    fluencyField.value = JSON.stringify(fluencyData);
    return fluencyData.result == 'yes';
  }

  // return error message based on local validation
  function getErrorMessage(element){
    var value = element.value;
    var data = getDataItemsFor(element);
    var result = performLocalValidation(value, data);

    if (result !== null){
      return result;
    }
    return 'Your reply is not fluent.';
  }

  // CrowdFlower-recommended custom validation
  // see https://success.crowdflower.com/hc/en-us/articles/201855879-Javascript-Guide-to-Customizing-a-CrowdFlower-Validator
  // This if/else block is used to hijack the functionality of an existing validator (specifically: yext_no_international_url)
  if (!_cf_cml.digging_gold) {
    CMLFormValidator.addAllThese([
      ['yext_no_international_url', {
        errorMessage: function(element) {
          return getErrorMessage(element);
        },
        validate: function(element, props) {
          // validate must return true or false
          return validate(element);
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

  // ****
  // UI
  // ****

  // insert things into text field at current cursor position
  // http://stackoverflow.com/questions/11076975/insert-text-into-textarea-at-cursor-position-javascript
  function insertAtCursor(myField, myValue) {
    //IE support
    if (document.selection) {
      myField.focus();
      sel = document.selection.createRange();
      sel.text = myValue;
    }
    //MOZILLA and others
    else if (myField.selectionStart || myField.selectionStart == '0') {
      var startPos = myField.selectionStart;
      var endPos = myField.selectionEnd;
      myField.value = myField.value.substring(0, startPos)
          + myValue
          + myField.value.substring(endPos, myField.value.length);
      myField.selectionStart = startPos + myValue.length;
      myField.selectionEnd = startPos + myValue.length;
    }
    else {
      myField.value += myValue;
    }
  }

  // make elements clickable
  function makeClickable(data, inputField){

    // convert the values to <span>s
    data.innerHTML = data.innerHTML.replace(/=([^,]+)(,|$)/g,
        '=<span>$1</span>$2');

    // make the spans insert their content to text field on click
    $(data).find('span').click(
      function(){
        insertAtCursor(inputField, $(this).html());
        inputField.focus();
        inputField.blur();  // force re-validation
        inputField.focus();
      }
    );
  }

  $(document).ready(function(){

    // make the instructions more explicit
    $('strong.confirm').html('confirm that you understand the question');
    $('strong.reply').html('answer the question');

    // prevent copy-paste from the instructions
    $('.html-element-wrapper').bind("copy paste",function(e) {
      e.preventDefault(); return false;
    });

    var dataInsts = $('.data');
    var inputFields = $('textarea.reply');
    for (var i = 0; i < dataInsts.length; ++i){
      makeClickable(dataInsts[i], inputFields[i]);
    }
    // this will make it crash if the validation server is inaccessible
    requestExternalValidation('', []);
  });
});

