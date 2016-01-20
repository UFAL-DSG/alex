
Building PTIEN CrowdFlower Jobs
===============================

This is a description of how to create a CrowdFlower Job that requires contributors to call our PTI service.

Getting started
---------------

There are multiple ways to get started, the best way is to match appropriate template for your project. Since there is no template for a Job that involves solvers to call a phone number and talk for a while, we have to create a Job from scratch.

Click the **Get started** button on a **Survey Job** panel at the `New Job <https://crowdflower.com/jobs/new>`_ page. This option will not require you to insert any data.

Fill in the Title.

Use the **Show Your Data** field to insert images, links, lists and add questions, typically to describe a survey. Use this field construct a feedback form. There needs to be at least one question created. This can be also done programmatically.

To switch to advanced code editor press the **Switch to CML Editor** button. This will allow you to write your own questions via CML tags. CML `Documentation <https://success.crowdflower.com/hc/en-us>`_ can be conveniently accessed through a presented link. Furthermore You can write HTML tags in there. It will be all processed and injected into a div, once the Job is created or previewed.

At the bottom of the page there is a **Show Custom CSS/JS** button. It will reveal two extra text areas in which you can put your custom styles and javascript code. The JS code is injected into a try/catch block of a function executed when the DOM is loaded.

Use the **Instructions** field to add your instructions. You can use the code icon (rightmost) to insert custom HTML. Any custom Javascript and CSS entered into the fields above will also apply here.

PTI Job description
-------------------

We have created a Job that includes a description of the Job, instructions for the caller, example call and a statement of consent. All of those text parts are situated in a collapsible divs. The job itself contains the phone number, a description of the task to talk about (retrieved from our server) and a few survey questions about the quality of the call.

To recreate the job, please copy:

- `CFJOB-PTIEN.html` into the CML field
- `CFJOB-PTIEN.css` into the custom CSS field
- `CFJOB-PTIEN.js` into the custom Javascript field
- `CFJOB-PTIEN.instructions.html` into the Instructions field

The HTML part of the job is really straightforward. The collapsible divs are modified versions of those in CML Documentation. There is a HTML script tag for loading Google location service. And the feedback form is hidden by **only-if** logic also explained in the documentation.

Apart from its usual utilization, CSS part is coupled with the collapsibility of divs.

The most interesting part of this Job is the JS section. There is a Google location call introduced. It shows a red warning text that emphasizes the US only contributors requirement. There is implemented a **Custom validator** used to validate a four digit number text field that opens up the feedback form. Incidentally a cross domain request function is implemented here.


Custom validator
----------------

The idea is that a CF contributor will call provided number to our PTI service and talk with it for a while in the terms of given task. After the dialogue is finished by saying “Thank You. Good Bye”, the dialogue system will generate a four digit code and it will say it three times before hanging up. At the same time it sends this code to our Python Web Server which will store it in a set of valid codes. The contributor puts this code in a text field with custom validator that triggers each time focus is off the text field. Custom validator functionality is hijacked via JS in a way described in CF Documentation. The validate function needs to return boolean. We use it to call other domain via HTTPS protocol. This is important because no HTTP requests nor JS scripts located on unsecured sites are permitted. In our case, we query our Python Server with the four digit code as a parameter. The server returns a JSON revealing the genuinity of provided code. If the code is genuine the custom validator passes and consequently the feedback form required to finish the Job is shown. A successful validation of a key is remembered because the cross domain request is synchronous and it is unnecessary to keep validating the code over and over. 

Asynchronous validation is an option worth considering. It would eliminate a web browser freeze effect. However, for simplicity and clarity we opted for the synchronous request.

Building Transcription CrowdFlower Jobs
=======================================

The system is very similar to PTIEN call jobs, even simpler. You just need to gather the call files and launch a Transcription job. You can use the instructions, task HTML, custom CSS, and Javascript provided here.

Gathering the audio files
-------------------------

To copy the required files from recorded calls to a server, such as `ufallab`, you can use the following Bash command::

  find /net/projects/vystadial/data/call-logs/2015-04-22-ptien/new/ -iname 'vad-*.wav' | \
      perl -pe 'use File::Copy "cp"; chomp; my $file = $_; $file =~ s/.*new\///; my $dir = $file; $dir =~ s/\/.*//; if (! -d $dir){ mkdir $dir; } cp($_, $file); $_ = $file . "\n";'

Then create a filelist::

  echo 'url' > filelist.csv
  find ./ -iname '*.wav' | sed 's/^\./http:\/\/ufallab.ms.mff.cuni.cz\/\~user\/path/' >> filelist.csv

Note that this is a "CSV" file even though it does not contain any commas (single-column only).

Creating the CF job
-------------------

Just select a **Transcription job** at the `New Job <https://crowdflower.com/jobs/new>`_ page. Load the `filelist.csv` file at the **Data** step.

In the **Design**, copy the files provided:

- `CFJOB-transcription.html` into the CML field
- `CFJOB-transcription.css` into the custom CSS field
- `CFJOB-transcription.js` into the custom Javascript field
- `CFJOB-transcription.instructions.html` into the Instructions field


