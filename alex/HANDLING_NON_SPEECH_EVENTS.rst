Handling non-speech events in Alex
==================================

The document describes handling non-speech events in Alex.

ASR
----

The ASR can generate either:

- a valid utterance
- the ``_noise_`` word to denote that the input was some noise or other sound which is not a regular word
- the ``_silence_`` word to denote that the input was silence
- the ``_other_`` word to denote that the input was something else that was lost during speech processing approximations
  such as N-best list enumeration or when the ASR did not provided any result. This is because we do not know what the
  input was and it can be both something important or worth ignoring. As such, it deserve special treatment in
  the system

SLU
----

The SLU can generate either:

- a ordinary dialogue act
- the ``null()`` act which should be ignored by the DM, and the system should respond with ``silence()``
- the ``silence()`` act which denote that the user was silent, a probably reasonable system response is ``silence()`` as well
- the ``other()`` act which denote that the input was something else that was lost during processing


The SLU should map:

- ``_noise_`` to ``null()`` - noise can be ignored in general
- ``_silence_`` to ``silence()`` - silence will be processed in the DM
- ``_other_`` to ``other()`` - other hypotheses will be handled by the DM, mostly by responding "I did not get that. Can
  you ... ?"


DM
----

The DM can generate either:

- a normal dialogue act
- the ``silence()`` dialogue act

The DM should map:

- ``null()`` to ``silence()`` - because the ``null()`` act denote that the input should be ignored; however there is a
  problem with this, read the note below for current workaround for this
- ``silence()`` to ``silence()`` or a normal dialogue act - the DM should be silent or to ask the user "Are still there?"
- ``other()`` to ``notunderstood()`` - to show the user that we did not understood the input and that the input should
  be rephrased instead of just being repeated.

**PROBLEM** As of now, both handcrafted and trained SLUs cannot correctly classify the ``other()`` dialogue act. It has
a very low recall for this DA. Instead of the ``other()`` DA it returns the ``null()`` DA. Therefore,  the ``null()``
act is processed in DMs as if it was the ``other()`` DA.