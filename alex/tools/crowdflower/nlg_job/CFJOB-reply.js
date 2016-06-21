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

  hours = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
        'ten', 'eleven', 'twelve'];

  // return true if the given hour information is missing
  function missingHour(value, hour) {
    if (value.indexOf(hour) != -1){
      return false;
    }
    hour = hour.replace(/:00$/, '');
    if (value.match(new RegExp('\\b' + hour + '\\b', ''))){
      return false;
    }
    hour = hours[hour];
    if (value.match(new RegExp('\\b' + hour + '\\b', 'i'))){
      return false;
    }
    return true;
  }

  // return true if the given data item is missing from the value (reply text)
  function missingData(value, dataItem, slot) {
    if (dataItem == 'notfound'){ // *=notfound (apologize tasks)
      return !value.match(/\b(no|not|unable|impossible|hasn't|nowhere|cannot|none|don't|couldn't|can't|didn't|haven't)\b/);
    }
    else if (dataItem == 'next'){ // alternative
      return !value.match(/\b(next|later|after|subsequent|following|another)\b/);
    }
    else if (dataItem == 'dontcare'){
      return !value.match(/\b(don\'t care|anything|any|arbitrary)\b/);
    }
    else if (dataItem == '1' && slot == 'alternative'){
      return !value.match(/\b(one|1|1st|first)\b/);
    }
    else if (dataItem == '2' && slot == 'alternative'){
      return !value.match(/\b(two|2|2nd|second)\b/);
    }
    else if (dataItem == '3' && slot == 'alternative'){
      return !value.match(/\b(three|3|3rd|third)\b/);
    }
    else if (dataItem == '4' && slot == 'alternative'){
      return !value.match(/\b(four|4|4th|fourth)\b/);
    }
    else if (dataItem == '0' && slot == 'num_transfers'){ // num_transfers
      return !value.match(/\b(no|none|aren't|isn't|not|zero)\b/);
    }
    else if (dataItem == '1' && slot == 'num_transfers'){
      return !value.match(/\b(one|once|1|1x)\b/);
    }
    else if (dataItem == '2' && slot == 'num_transfers'){
      return !value.match(/\b(two|twice|2|2x)\b/);
    }
    else if (dataItem == '0:30'){
      return !value.match(/\b((30|thirty) +min(ute)?s|0:30|half|1\/2)\b/);
    }
    else if (dataItem == '0:10'){
      return !value.match(/\b((10|ten) +min(ute)?s|0:10)\b/);
    }
    else if (dataItem == '0:15'){
      return !value.match(/\b((15|fifteen) +min(ute)?s|0:15|quarter|1\/4)\b/);
    }
    else if (dataItem == '0:20'){
      return !value.match(/\b((20|twenty) +min(ute)?s|0:20)\b/);
    }
    else if (dataItem.match(/^[0-9]+:00$/)){
      return missingHour(value, dataItem);
    }
    else if (dataItem == 'am'){
      return !value.match(/\b(([0-9]?[0-9](:[0-9][0-9])?)?am|([0-9]?[0-9](:[0-9][0-9])?)?a.m.|a m|morning|forenoon|morn|dawn|morrow|daybreak|sunrise|ante meridian)\b/);
    }
    else if (dataItem == 'pm'){
      return !value.match(/\b(([0-9]?[0-9](:[0-9][0-9])?)?pm|([0-9]?[0-9](:[0-9][0-9])?)?p.m.|p m|evening|night|tonight|afternoon|dusk|eve|nightfall|sunset|siesta|post meridian)\b/);
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
    else if (dataItem.length == 1){ // Subway line names (must be separated by spaces)
      return !value.match(new RegExp('\\b' + dataItem + '\\b', 'i'));
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

      if (value.match(/\b(o[' ]?clock|today|tomorrow|day|tonight|evening|morning|afternoon)\b/i)){
        return 'time';
      }
      if ($.inArray('duration', data.slots) == -1 &&
          $.inArray('departure_time_rel', data.slots) == -1 &&
          value.match(/\b(hours?|minutes|time)\b/i) &&
          !value.match(/\b(later|next|this|last) time\b/i) && !value.match(/\btime later\b/i)){
        return 'time';
      }
    }

    // irrelevant time-related values
    hrs = value.match(/\b([0-9]+:[0-9]+[ap]m|[ap]m|[0-9]+:[0-9]+|[0-9]+[ap]m|o[' ]?clock)\b/ig);
    if (hrs !== null){
      for (var i = 0; i < hrs.length; ++i){
        if (hrs[i] == 'am' && value.match(/\bI am\b/i)){ // skip 'I am'
          continue;
        }
        alt_version = hrs[i].replace(/[ap]m$/i, '').replace(/\s*o[' ]?clock/i, ':00');
        if ($.inArray(hrs[i], data.values) == -1 && $.inArray(alt_version, data.values) == -1){
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
    if ($.inArray('from_stop', data.slots) == -1){
      if (value.match(/(from +((what|which)? +(origin|stop|place|street|location)|where)|where +from)/i)){
        return 'location';
      }
    }
    if ($.inArray('to_stop', data.slots) == -1 &&
        $.inArray('direction', data.slots) == -1){

      if (value.match(/(to +((what|which)? +(destination|stop|place|street|location)|where)|where +to)/i)){
        return 'location';
      }
    }

    // irrelevant vehicles (but leave Port Authority Bus Terminal)
    vehicles = value.match(/\b(train|subway|bus|tram|trolley)(?! terminal)\b/ig);
    if (vehicles !== null){
      for (var i = 0; i < vehicles.length; ++i){
        if ($.inArray(vehicles[i], data.values) == -1){
          return 'vehicle';
        }
      }
    }

    // do not enter all alternatives suggested
    if (value.match(/(next|later|after) (or|and) (next|later|after)/i)){
      return 'Use *just one* of the alternatives (next/later/after).';
    }
    if (value.match(/(am|morning) (or|and) (am|morning)/i)){
      return 'Use *just one* of the alternatives (am/morning).';
    }
    if (value.match(/(pm|afternoon|evening) (or|and) (pm|afternoon|evening)/i)){
      return 'Use *just one* of the alternatives (pm|afternoon|evening).';
    }

    // no "yes there is" if I want just confirmation
    if (data.taskTypes[0] == 'confirm' && (data.taskTypes.length == 1 || data.taskTypes[1] != 'reply')){
      if (value.match(/^((Yes|No|OK)( sir| madam)?,? *)?(there (is|are)|(I|it|we) (have|will|are|is)|you can)/i)){
        return 'Do not reply, just confirm what you heard';
      }
    }

    // we are supposed to confirm, not ask for confirmation
    if (data.taskTypes[0] == 'confirm' && value.match(/please confirm/i)){
      return 'Do not ask for confirmation but confirm yourself what you heard';
    }

    if (data.taskTypes[0] == 'confirm' && (data.taskTypes.length == 1 || data.taskTypes[1] != 'request')){
      if (value.match(/(do|can|did|would|are) you/i)){
        return 'Do not ask for confirmation but confirm yourself what you heard';
      }
    }

    // we are not supposed to ask unless the task is 'request'
    if ($.inArray('request', data.taskTypes) == -1 && value.match(/\b(what|where|how|what's|which)\b/i)){
      task = '';
      if ($.inArray('confirm', data.taskTypes) >= 0){
        task += 'and confirm what you heard';
      }
      if ($.inArray('reply', data.taskTypes) >= 0){
        task += 'and answer the question';
      }
      if ($.inArray('apologize', data.taskTypes) >= 0){
        task += 'and apologize that you cannot find what the user is looking for';
      }
      return 'Do not ask for additional information, ' + task.substring(4) + '.';
    }

    return ''; // everything OK
  }

  // checking for missing slots in 'apologize' tasks
  function checkMissingSlots(value, data){
    retVal = '';
    for (var i = 0; i < data.slots.length; ++i){
      if (data.slots[i] == 'to_stop' && !value.match(/\b(to|directions?|for|destination|connection|ride|transit|route|schedule)\b/i)){
        retVal += ' *to* ' + data.values[i];
      }
      else if (data.slots[i] == 'from_stop' && !value.match(/\b(from|directions|origin|connection|ride|transit|route|schedule)\b/i)){
        retVal += ' *from* ' + data.values[i];
      }
    }
    return retVal;
  }

  // local validation -- just check that all data are included in the answers
  function performLocalValidation(value, data){

    // check if disallowed characters are present
    if (value.match(/[^0-9A-Za-z '?.!;,:-]/)){
      return 'Your reply contains weird characters. ' +
        'Use only the English alphabet and basic punctuation.';
    }
    // normalize spaces to simplify regexes
    value = value.replace(/([?.!;:,-]+)(?![0-9])/g, "$1 "); // (avoid 0:00 0.0 numbers)
    value = value.replace(/\s+/g, " ");
    value = value.replace(/^ /, "");
    value = value.replace(/ $/, "");

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
    if ($.inArray('apologize', data.taskTypes) >= 0){
      var errMsg = checkMissingSlots(value, data);
      if (errMsg !== ''){
        return 'Please indicate clearly that you cannot find a connection/shedule/ride' + errMsg;
      }
    }

    // check for superfluous information
    var errMsg = checkSuperfluousInformation(value, data);
    if (errMsg !== ''){
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

    if (toks.length < 2 * data.values.length || toks.length < data.values.length + 2){
      return 'Your reply is too short. Use full, fluent sentences.';
    }

    return null;
  }

  function getDataItemsFor(element){
    var slots = [];
    var values = [];
    var taskTypes = [];
    $(element).closest('.html-element-wrapper').find('.raw_data').find('.slot').each(
        function(){ slots.push($(this).text()); }
        );
    $(element).closest('.html-element-wrapper').find('.raw_data').find('.val').each(
        function(){ values.push($(this).text()); }
        );
    $(element).closest('.html-element-wrapper').find('.instr').find('strong').each(
        function(){ taskTypes.push($(this).attr('class')); }
        );
    var context = $(element).closest('.html-element-wrapper').find('.user_utt')[0].innerText;

    return {slots: slots, values: values, taskTypes: taskTypes, context: context};
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
      myField.value = myField.value.substring(0, startPos) +
          myValue +
          myField.value.substring(endPos, myField.value.length);
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
      '', 'line', '', '',
    ];

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
        /([^ ]+)=([^,;]+)(?=[,;]|$)/g,
        function(match, p1, p2){
          if (p2 == 'next'){
            return p1 + '=<span class="fuzzy">next/later/after</span>';
          }
          if (p2 == 'dontcare'){
            return p1 + '=<span class="fuzzy">any/don\'t care</span>';
          }
          else if (p2 == 'am'){
            return p1 + '=<span class="fuzzy">am/morning</span>';
          }
          else if (p2 == 'pm'){
            return p1 + '=<span class="fuzzy">pm/afternoon/evening</span>';
          }
          else if (p1 == 'departure_time_rel' && p2.match(/^0:/)){
            return p1 + '=<span class="fuzzy">' + p2.substring(2) + ' minutes</span>';
          }
          else if (p1 == 'alternative' && p2.match(/^[1234]$/)){
            if (p2 == '1'){
              return p1 + '=<span class="fuzzy">1st</span>';
            }
            else if (p2 == '2'){
              return p1 + '=<span class="fuzzy">2nd</span>';
            }
            else if (p2 == '3'){
              return p1 + '=<span class="fuzzy">3rd</span>';
            }
            else if (p2 == '4'){
              return p1 + '=<span class="fuzzy">4th</span>';
            }
          }
          else if (p2.match(/^(notfound|\?|next|none|[012]|0:30)$/)){
            return p1 + '=<span class="fuzzy">' + p2 + '</span>';
          }
          return p1 + '=<span class="exact">' + p2 + '</span>';
        });

    // split confirm & reply into two lines
    data.innerHTML = data.innerHTML.replace(/(confirm|reply|request): /g, "<em>$1:</em> ");
    data.innerHTML = data.innerHTML.replace(/; <em>/, '<br/><em>');

    // shorten slot names
    for (var i = 0; i < slotNames.length; ++i){
      if (shorts[i] !== ''){
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

