The frontend for VAD should not include energy (C0) coefficient since then the VAD would depend on the volume
of the audio and whispered speech would not be detected.

It looks like that the English VAD works well even for Czech.
