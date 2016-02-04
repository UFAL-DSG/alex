// CrowdFlower-recommended custom validation
// see https://success.crowdflower.com/hc/en-us/articles/201855879-Javascript-Guide-to-Customizing-a-CrowdFlower-Validator
// This if/else block is used to hijack the functionality of an existing validator (specifically: yext_no_international_url)
if (!_cf_cml.digging_gold) {
    CMLFormValidator.addAllThese([
        ['yext_no_international_url', {
            errorMessage: function() {
                return ('Field contains illegal characters. Use only letters a-z and the following: ( ) \' - ');
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
    // normalize -- lowercase, trim whitespace
    var value = element.value.toLowerCase();
    value = value.replace(/^\s+|\s+$/g,'');
    value = value.replace(/\s+/g, ' ');
    // return this as the final value
    element.value = value;

    // check if the field doesn't contain illegal characters
    var re = /^[()' a-z-]*$/;
    if (!re.test(value)){
        return false;
    }
    
    return true;
}



