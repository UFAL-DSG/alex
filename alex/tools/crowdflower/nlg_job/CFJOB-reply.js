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

  function missingData(value, dataItem, slot) {
    if (dataItem == 'notfound'){ // *=notfound (apologize tasks)
      return !value.match(/\b(no|not|none|don't)\b/);
    }
    else if (dataItem == 'next'){ // alternative
      return !value.match(/\b(next|later|after|subsequent|following|another)\b/);
    }
    else if (dataItem == '0'){ // num_transfers
      return !value.match(/\b(no|none|aren't|isn't|not|zero)\b/);
    }
    else if (dataItem == '1'){
      return !value.match(/\b(one|once|1|1x)\b/);
    }
    else if (dataItem == '2'){
      return !value.match(/\b(two|twice|2|2x)\b/);
    }
    else if (dataItem == '0:30'){
      return !value.match(/\b(30 min(ute)?s|0:30|half|1\/2)\b/);
    }
    else if (dataItem == '?'){ // request tasks
      if (!value.match(/\b(what|where|how|what's|which)\b/)){
        return true;
      }
      if (slot.match(/stop/) && !value.match(/\b(where|origin|destination|from|to|stop)\b/)){
        return true;
      }
      return false;
    }
    else {
      return value.indexOf(dataItem) == -1;
    }
  }

  stopsList = ['Astor Place',
         'Bleecker Street',
         'Bowery',
         'Bowling Green',
         'Broad Street',
         'Bryant Park',
         'Canal Street',
         'Cathedral Parkway',
         'Central Park',
         'Chambers Street',
         'City College',
         'City Hall',
         'Columbia University',
         'Columbus Circle',
         'Cortlandt Street',
         'Delancey Street',
         'Dyckman Street',
         'East Broadway',
         'Essex Street',
         'Franklin Street',
         'Fulton Street',
         'Grand Central',
         'Grand Street',
         'Harlem',
         'Herald Square',
         'Houston Street',
         'Hudson Yards',
         'Hunter College',
         'Inwood',
         'Lafayette Street',
         'Lincoln Center',
         'Marble Hill',
         'Museum of Natural History',
         'New York University',
         'Park Place',
         'Penn Station',
         'Port Authority Bus Terminal',
         'Prince Street',
         'Rector Street',
         'Rockefeller Center',
         'Roosevelt Island',
         'Sheridan Square',
         'South Ferry',
         'Spring Street',
         'Times Square',
         'Union Square',
         'Wall Street',
         'Washington Square',
         'World Trade Center'];

  function checkSuperfluousInformation(value, data){

    // time-related words in DAs not concerning time
    if ($.inArray('departure_time', data.slots) == -1 &&
        $.inArray('arrival_time', data.slots) == -1 &&
        $.inArray('ampm', data.slots) == -1){

      if (value.match(/\b(o'clock|hours?|today|tomorrow|day|tonight|evening|morning|afternoon)\b/i)){
        return 'time';
      }
      if ($.inArray('duration', data.slots) == -1 &&
          value.match(/\b(minutes|time)\b/) &&
          !value.match(/\b(later|next|this|last) time\b/) && !value.match(/\btime later\b/)){
        return 'time';
      }
    }

    // irrelevant time-related values
    hrs = value.match(/\b([0-9]+:[0-9]+[ap]m|[ap]m|[0-9]+:[0-9]+|[0-9]+[ap]m|o'?clock)\b/ig);
    if (hrs != null){
      for (var i = 0; i < hrs.length; ++i){
        if ($.inArray(hrs[i], data.values) == -1){
          return 'time';
        }
      }
    }

    // irrelevant stops
    for (var i = 0; i < stopsList.length; ++i){
      if (value.match(new RegExp(stopsList[i], 'gi')) && $.inArray(stopsList[i], data.values) == -1){
        return 'location';
      }
    }

    // irrelevant stop-related words
    if ($.inArray('from_stop', data.slots) == -1 &&
        $.inArray('to_stop', data.slots) == -1 &&
        $.inArray('direction', data.slots) == -1){

      if (value.match(/(from|to)( what|which)? stop/)){
        return 'location';
      }
    }

    // irrelevant vehicles (but leave Port Authority Bus Terminal)
    vehicles = value.match(/\b(train|subway|bus|tram|trolley)(?! terminal)\b/ig);
    if (vehicles != null){
      for (var i = 0; i < vehicles.length; ++i){
        if ($.inArray(vehicles[i], data.values) == -1){
          return 'vehicle';
        }
      }
    }

    // no "yes there is" if I want just confirmation
    if (data.taskTypes.length == 1 && data.taskTypes[0] == 'confirm'){
      if (value.match(/^ *((Yes|No),? *)?(there (is|are)|(you|I|it) (will|are|is))/i)){
        return 'Do not reply, just confirm what you heard';
      }
    }
    return ''; // everything OK
  }

  // local validation -- just check that all data are included in the answers
  function performLocalValidation(value, data){

    // check if disallowed characters are present
    if (value.match(/[^0-9A-Za-z '?.!;,:-]/)){
      return 'Your reply contains weird characters. ' +
          'Use only the English alphabet and basic punctuation.';
    }

    // check for missing information (case-insensitive)
    missing = [];
    lcValue = value.toLowerCase();
    for (var i = 0; i < data.values.length; ++i){
      lcData = data.values[i].toLowerCase();
      if (missingData(lcValue, lcData, data.slots[i])){
        missing.push(data.values[i] == '?' ? data.slots[i] + '=?' : data.values[i]);
      }
    }
    if (missing.length > 0){
      return 'Your reply is missing the following information: ' + missing.join(', ');
    }

    // check for superfluous information
    var errMsg = checkSuperfluousInformation(value, data);
    if (errMsg != ''){
      return 'Your reply contains superfluous information: ' + errMsg;
    }

    // check for sufficient number of tokens
    toks = ' ' + value + ' ';  // pad with spaces for easy regexes
    for (var i = 0; i < data.values.length; ++i){
      toks = toks.replace(data.values[i], 'DATA' + i);
    }
    toks = toks.replace(/([?.!;,:-]+)/g, " $1 ");
    toks = toks.replace(/\s+/g, " ");
    toks = toks.substring(1, toks.length - 1);  // remove the padding spaces
    toks = toks.split(" ");

    if (toks.length < 2 * data.values.length || toks.length < data.values.length + 3){
      return 'Your reply is too short. Use full, fluent sentences.';
    }

    return null;
  }

  function getDataItemsFor(element){
    var slots = [];
    var values = [];
    var taskTypes = [];
    $(element).closest('.html-element-wrapper').find('.raw_data').find('.slot').each(
        function(){ slots.push($(this).text()) }
    );
    $(element).closest('.html-element-wrapper').find('.raw_data').find('.val').each(
        function(){ values.push($(this).text()) }
    );
    $(element).closest('.html-element-wrapper').find('.instr').find('strong').each(
        function(){ taskTypes.push($(this).attr('class')) }
    );

    return {slots: slots, values: values, taskTypes: taskTypes};
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
    var fluencyData = requestExternalValidation(value, data.values);
    fluencyField.value = JSON.stringify(fluencyData);
    return fluencyData.result == 'yes';
  }

  // return error message based on local validation
  function getErrorMessage(element){
    var value = element.value;
    var data = getDataItemsFor(element);
    var result = performLocalValidation(value, data);

    // + log all validation data (in a very crude fashion, but still)
    var validLogField = $(element).closest('.html-element-wrapper').find('.validation_log')[0];
    if (result !== null){
      validLogField.innerHTML += " /// \"" + element.value + "\" --- " + result;
      return result;
    }
    validLogField.innerHTML += " /// \"" + element.value + "\" --- not fluent";
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

  var slotNames = ['*', 'num_transfers', 'from_stop', 'to_stop', 'direction',
      'departure_time', 'arrival_time', 'departure_time_rel', 'duration', 'distance',
      'vehicle', 'line', 'ampm', 'alternative',
    ];
  var shorts = ['', '', 'from', 'to', 'dir',
      '', '', '', '', '',
      '', 'line', 'ampm', '',
    ];

  function createTimer(objId, alts){
    setInterval(function(){ swapAlt(objId, alts); }, 1000);
  }

  // make clickable, format content
  function prepareDataItems(data, inputField){

    var rawData = data.innerHTML;
    rawData = rawData.replace(/=([^,;]+)(?=[,;]|$)/g, '=<span class="val">$1</span>');
    for (var i = 0; i < slotNames.length; ++i){
      rawData = rawData.replace(slotNames[i] + '=',
          '<span class="slot">' + slotNames[i] + '</span>=');
    }
    $(data).after('<div class="raw_data" style="display:none;">' + rawData + '</div>');

    // convert the values to <span>s
    data.innerHTML = data.innerHTML.replace(
        /=([^,;]+)(?=[,;]|$)/g,
        function(match, p1){
          if (p1 == 'next'){
            return '=<span class="fuzzy">next/later/after</span>';
          }
          else if (p1.match(/^(notfound|\?|next|none|[012]|0:30)$/)){
            return '=<span class="fuzzy">' + p1 + '</span>';
          }
          return '=<span class="exact">' + p1 + '</span>';
        });

    // split confirm & reply into two lines
    data.innerHTML = data.innerHTML.replace(/(confirm|reply|request): /g, "<em>$1:</em> ");
    data.innerHTML = data.innerHTML.replace(/; <em>/, '<br/><em>');

    for (var i = 0; i < slotNames.length; ++i){
      if (shorts[i] != ''){
        data.innerHTML = data.innerHTML.replace(slotNames[i] + '=',
            '<span class="slot-name">' + shorts[i] + '</span>=');
      }
      else {
        data.innerHTML = data.innerHTML.replace(slotNames[i] + '=',
            '<span class="slot-name"></span>');
      }
    }

    // make the spans insert their content to text field on click
    $(data).find('span.exact').click(
      function(){
        insertAtCursor(inputField, $(this).html());
        inputField.focus();
        inputField.blur();  // force re-validation
        inputField.focus();
      }
    );
  }

  $(document).ready(function(){

    // split double instructions
    confirmReply = $('strong.confirm-reply');
    confirmReply.attr('class', 'confirm');
    confirmReply.after(' and <strong class="reply"></strong>');
    confirmRequest = $('strong.confirm-request');
    confirmRequest.attr('class', 'confirm');
    confirmRequest.after(' and <strong class="request"></strong>');

    // make the instructions more explicit
    $('strong.confirm').html('confirm that you understand');
    $('strong.reply').html('answer the question');
    $('strong.reply').after(' in ');
    $('strong.request').html('request additional information');
    $('strong.request').after(' about ');
    $('strong.apologize').html('apologize that you cannot find what you were asked for');
    $('strong.apologize').after(' in ');

    // prevent copy-paste from the instructions
    $('.html-element-wrapper').bind("copy paste",function(e) {
      e.preventDefault(); return false;
    });

    var dataInsts = $('.data');
    var inputFields = $('textarea.reply');
    for (var i = 0; i < dataInsts.length; ++i){
      prepareDataItems(dataInsts[i], inputFields[i]);
    }
    // this will make it crash if the validation server is inaccessible
    requestExternalValidation('', []);
  });
});


