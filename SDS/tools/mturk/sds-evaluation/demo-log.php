<?php

$did = $_REQUEST["dialogueID"];

# (%'s used as pcre delimiter, as it won't occur elsewhere)
#$safedid = '%^/data/dial/classic/Aug09VoIP-CamInfo/[A-Za-z0-9_-]+$%';
$safedid = '%^/data/dial/classic/[/A-Za-z0-9_-]+$%';

if (!preg_match($safedid, $did)) {
   echo "attempt to specify an illegal dialogueID.";
   echo "($did)";
   return;
}

$fn = $did."/feedback.xml";


if (file_exists($fn)) {
    echo "Feedback was already recorded.";
    return;
}

$file=fopen($fn,"x");

if (!$file) {
    echo "Unable to open file: ".$fn;
    return;
}

fwrite($file,$_REQUEST["xmlFeedback"]);
fclose($file);

echo "Feedback ".$fn." saved";

?>
