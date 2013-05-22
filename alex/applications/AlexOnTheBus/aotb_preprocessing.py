import autopath
from alex.components.slu.base import SLUPreprocessing
from alex.components.asr.utterance import Utterance
from alex.utils.czech_stemmer import cz_stem

class AOTBSLUPreprocessing(SLUPreprocessing):
    def text_normalisation(self, utterance):
        utterance = super(AOTBSLUPreprocessing, self).text_normalisation(utterance)

        res = []
        for word in utterance:
            res += [cz_stem(word)]

        return Utterance(" ".join(res))