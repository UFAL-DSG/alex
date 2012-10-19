import sys
import os.path

# Add the directory containing the SDS package to python path
path, directory = os.path.split(os.path.abspath(__file__))
while directory and directory != 'SDS':
    path, directory = os.path.split(path)
if directory == 'SDS':
    sys.path.append(path)


class Hub:
    def run(self):
        pass

class VoipHub(Hub):
    """
      VoipHub builds full featured VOIP telephone system.
      It builds a pipeline of ASR, SLU, DM, NLG, TTS components.
      Then it connects ASR and TTS with the VOIP to handle audio input and output.
    """
    def run(self):
        pass
