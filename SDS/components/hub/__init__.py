#__all__ = ['',]

class Hub:
  def run(self):
    pass

class TextHub(Hub):
  """
    TextHub builds a text based testing enviroment for the SLU, DM, and NLG
    components.
    It reads text from standard input and passes it in SLU and it outputs
    the text generatet by a NLG component.
  """
  def run(self):
    pass

class SemHub(Hub):
  """
    TextHub builds a text based testing enviroment for the SLU, DM, and NLG
    components.
    It reads text from standard input and passes it in SLU and it outputs
    the text generatet by a NLG component.
  """
  def run(self):
    pass

class VOIP:
  def __init(self, user, password, callBack):
    pass

  def call(self, phoneNumber):
    pass

  def play(self, audio):
    pass

class VoipHub(Hub):
  """
    VoipHub builds full featured VOIP telephone system.
    It builds a pipeline of ASR, SLU, DM, NLG, TTS components.
    Then it connects ASR and TTS with the VOIP to handle audio input and output.
  """
  def run(self):
    pass

