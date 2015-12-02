
Building PTIEN CrowdFlower Jobs
===============================

This is a description of how to create a CrowdFlower Job that requires contributors to call our PTI service.

Getting started
---------------

There are multiple ways to get started, the best way is to match appropriate template for your project. Since there is no template for a Job that involves solvers to call a phone number and talk for a while, we have to create a Job from scratch.

Click the **Get started** button on a **Survey Job** panel at a `New Job <https://crowdflower.com/jobs/new>`_ page. This option will not require you to insert any data. You can go ahead and fill the Title and Instructions if you want. Both of these fields can not be left blank. The Instructions field however does not have any capability to change styles or insert items and stuff like that. That is why in most cases you will want to briefly refer to the real instructions implemented down below. 

The last field is **Show Your Data** field in which you can insert images, links, lists and add questions, typically to describe a survey. We should want to use the questions at the utmost to construct a feedback form. There needs to be at least one question created. This can be also done programmatically.

To switch to advanced code editor press the **Switch to CML Editor** button. This will allow you to write your own questions via CML tags. CML `Documentation <https://success.crowdflower.com/hc/en-us>`_ can be conveniently accessed through a presented link. Furthermore You can write HTML tags in there. It will be all processed and injected into a div, once the Job is created or previewed.

At the bottom of the page there is a **Show Custom CSS/JS** button. It will reveal two extra text areas in which you can put your custom styles and javascript code. The JS code is injected into a try/catch block of a function executed when the DOM is loaded.

PTI Job description
-------------------

We have created a Job that includes a description of the Job, instructions for the caller, example call and a statement of consent. All of those text parts are situated in a collapsible divs. Then there is a theme for the contributor to speak about in a box and already mentioned feedback form that is accessible once a valid four digit code is inserted.

HTML part of the job is really straight forward. The collapsible divs are modified versions of those in CML Documentation. There is a HTML script tag for loading Google location service. And the feedback form is hidden by **only-if** logic also explained in the documentation.

Apart from its usual utilization, CSS part is coupled with the collapsibility of divs.

The most interesting part of this Job is the JS section. There is a Google location call introduced. It shows a red warning text that emphasizes the US only contributors requirement. There is implemented a **Custom validator** used to validate a four digit number text field that opens up the feedback form. Incidentally a cross domain request function is implemented here.

Custom validator
----------------

The idea is that a CF contributor will call provided number to our PTI service and talk with it for a while in the terms of given task. After the dialogue is finished by saying “Thank You. Good Bye”, the dialogue system will generate a four digit code and it will say it three times before hanging up. At the same time it sends this code to our Python Web Server which will store it in a set of valid codes. The contributor puts this code in a text field with custom validator that triggers each time focus is off the text field. Custom validator functionality is hijacked via JS in a way described in CF Documentation. The validate function needs to return boolean. We use it to call other domain via HTTPS protocol. This is important because no HTTP requests nor JS scripts located on unsecured sites are permitted. In our case, we query our Python Server with the four digit code as a parameter. The server returns a JSON revealing the genuinity of provided code. If the code is genuine the custom validator passes and consequently the feedback form required to finish the Job is shown. A successful validation of a key is remembered because the cross domain request is synchronous and it is unnecessary to keep validating the code over and over. 

Asynchronous validation is an option worth considering. It would eliminate a web browser freeze effect. However, for simplicity and clarity we opted for the synchronous request.
