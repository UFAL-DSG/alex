#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.

import numpy as np

from collections import defaultdict
from itertools import izip, product
from operator import itemgetter, mul

from alex import utils
from alex.components.slu.exception import SLUException
from alex.ml.hypothesis import Hypothesis, NBList, NBListException
# TODO: The following import is a temporary workaround for moving classes
# originally defined here to that module.  Instead, refer to the new module's
# definitions everywhere where this module would have been used.
from alex.ml.features import *


SENTENCE_START = '<s>'
SENTENCE_END = '</s>'


def load_utterances(utt_fname, limit=None):
    """Loads a dictionary of utterances from a given file. The file is assumed
    to contain lines of the following form:

    [whitespace..]<key>[whitespace..]=>[whitespace..]<utterance>[whitespace..]

    Arguments:
        utt_fname -- path towards the file to read the utterances from
        limit -- limit on the number of utterances to read

    Returns a dictionary with utterances (instances of Utterance) as values.

    """
    with open(utt_fname) as utt_file:
        utterances = {}
        count = 0
        for line in utt_file:
            count += 1
            if limit is not None and count > limit:
                break

            line = line.strip()
            if not line:
                continue

            parts = line.split("=>")

            key = parts[0].strip()
            utt = parts[1].strip()

            utterances[key] = Utterance(utt)

    return utterances


class UtteranceException(SLUException):
    pass


class UtteranceNBListException(SLUException):
    pass


class UtteranceConfusionNetworkException(SLUException):
    pass


class ASRHypothesis(Hypothesis):
    """This is the base class for all forms of probabilistic ASR hypotheses
    representations."""
    pass


class Utterance(object):
    # TODO: Since Utterance basically represents a (is-a) list, it should
    # inherit from the builtin `list', I reckon. This might be a bit tricky,
    # though, because of the way built-in types are constructed.

    def __init__(self, surface):
        self.utterance = surface.split()

    def __str__(self):
        return ' '.join(self.utterance)

    def __contains__(self, s):
        try:
            self.index(s)
        except ValueError:
            return False

        return True

    def __lt__(self, other):
        return self.utterance < other.utterance

    def __le__(self, other):
        return self.utterance <= other.utterance

    def __eq__(self, other):
        if isinstance(other, Utterance):
            return self.utterance == other.utterance
        elif isinstance(other, basestring):
            return self.utterance == other.split()
        return False

    def __ne__(self, other):
        return not self.__eq__(other.utterance)

    def __gt__(self, other):
        return self.utterance > other.utterance

    def __ge__(self, other):
        return self.utterance >= other.utterance

    def __len__(self):
        return len(self.utterance)

    def __getitem__(self, idx):
        return self.utterance[idx]

    def __iter__(self):
        for word in self.utterance:
            yield word

    def isempty(self):
        return len(self.utterance) == 0

    # TODO cache(1)
    def index(self, phrase):
        """Returns the word index of the start of first occurence of `phrase'
        within this utterance. If none is found, ValueError is raised.

        Arguments:
            phrase -- a list of words constituting the phrase sought

        """
        assert len(phrase) > 0
        # All through this method, we assume a short length of `phrase', with
        # little or none repeated word tokens.

        # Compute the maximal skip in case of incomplete match.
        initial = phrase[0]
        for word_count, word in enumerate(phrase[1:], start=1):
            if word == initial:
                max_skip = word_count
                break
        else:
            max_skip = len(phrase)

        # last index where the match can start
        last_idx = len(self.utterance) - len(phrase)
        # Iterate over the utterance.
        match_idx = 0
        while match_idx <= last_idx:
            # If the initial word matches,
            if self.utterance[match_idx] == initial:
                # Check the subsequent words too.
                for phrase_idx in xrange(1, len(phrase)):
                    if self.utterance[match_idx + phrase_idx] !=\
                            phrase[phrase_idx]:
                        break
                else:
                    # Match found.
                    return match_idx
                # If subsequent words do not match, skip them.
                match_idx += min(max_skip, phrase_idx)
            else:
                match_idx += 1
        # No match found.
        raise ValueError('Missing "{phrase}" in "{utt}"'
                         .format(phrase=phrase, utt=self.utterance))

    def replace(self, orig, replacement, return_startidx=False):
        # If `orig' does not occur in self, do nothing, return self.
        try:
            orig_pos = self.index(orig)
        except ValueError:
            ret_utt = self
            orig_pos = -1
        else:
            # If `orig' does occur in self, construct a new utterance with `orig'
            # replaced by `replacement' and return that.
            ret_utt = Utterance('')
            if not isinstance(replacement, list):
                replacement = list(replacement)
            ret_utt.utterance = (self.utterance[:orig_pos] + replacement +
                            self.utterance[orig_pos + len(orig):])
        return (ret_utt, orig_pos) if return_startidx else ret_utt

    def lower(self):
        """Transforms words of this utterance to lower case.

        BEWARE, this method is destructive, it lowercases self.

        """
        for word_idx in range(len(self.utterance)):
            self.utterance[word_idx] = self.utterance[word_idx].lower()
        return self

    def iter_with_boundaries(self):
        """Iterates the sequence [SENTENCE_START, word1, ..., wordlast,
        SENTENCE_END].

        """
        yield SENTENCE_START
        for word in self.utterance:
            yield word
        yield SENTENCE_END

    def iter_ngrams(self, n, with_boundaries=False):
        min_len = n - with_boundaries * 2
        # If the n-gram so-so fits into the utterance.
        if len(self.utterance) <= min_len:
            if len(self.utterance) == min_len:
                if with_boundaries:
                    yield [SENTENCE_START] + self.utterance + [SENTENCE_END]
                else:
                    yield self.utterance[:]
            return
        # Usual cases.
        if with_boundaries and len(self.utterance) > min_len:
            yield [SENTENCE_START] + self.utterance[:n - 1]
        for start_idx in xrange(len(self.utterance) - n + 1):
            yield self.utterance[start_idx:start_idx + n]
        if with_boundaries:
            yield self.utterance[-(n - 1):] + [SENTENCE_END]


# TODO Document.
# TODO Extend to AbstractedLattice.
# TODO Write tests.
class AbstractedUtterance(Utterance, Abstracted):
    other_val = ('[OTHER]', )

    def __init__(self, surface):
        self._abstr_idxs = list()  # sorted in an increasing order
        Utterance.__init__(self, surface)
        Abstracted.__init__(self)

    def __cmp__(self, other):
        if isinstance(other, AbstractedUtterance):
            my_key = (self.utterance, self._abstr_idxs)
            their_key = (other.utterance, other._abstr_idxs)
            return ((my_key >= their_key) - (their_key >= my_key))
        else:
            return 1

    def __hash__(self):
        return hash((tuple(self.utterance), tuple(self._abstr_idxs)))

    @classmethod
    def from_utterance(cls, utterance):
        """Constructs a new AbstractedUtterance from an existing Utterance."""
        abutt = AbstractedUtterance('')
        abutt.utterance = utterance.utterance
        return abutt

    @classmethod
    def make_other(cls, type_):
        return ('{t}-OTHER'.format(t=type_[0]), )

    def join_typeval(self, type_, val):
        return (self.splitter.join((type_[0], ' '.join(val))), )

    def iter_typeval(self):
        for idx in self._abstr_idxs:
            yield (self.utterance[idx], )

    def iter_triples(self):
        for combined_el, in self.iter_typeval():
            split = combined_el.split(self.splitter, 2)
            try:
                type_, value = split
            except ValueError:
                value = ''
                type_ = split[0] if combined_el else ''
            # XXX Change the order of return values to combined_el, type_,
            # value.
            yield (combined_el, ), tuple(value.split(' ')), (type_, )

    def phrase2category_label(self, phrase, catlab):
        """Replaces the phrase given by `phrase' by a new phrase, given by
        `catlab'.  Assumes `catlab' is an abstraction for `phrase'.

        """
        combined_el = self.splitter.join((' '.join(catlab),
                                          ' '.join(phrase)))
        return self.replace(phrase, (combined_el, ))

    def replace(self, orig, replacement):
        """Replaces the phrase given by `orig' by a new phrase, given by
        `replacement'.

        """
        replaced, startidx = Utterance.replace(self, orig, replacement,
                                               return_startidx=True)
        # XXX This won't work nicely with concrete features, where the
        # utterance will have multiple words as one -- the whole phrase
        # abstracted from.
        if startidx == -1:
            return self
        else:
            # If any replacement took place, reflect it in self.utterance and
            # self._abstr_idxs.
            ab_replaced = AbstractedUtterance.from_utterance(replaced)
            shift = 1 - len(orig)  # the replaced element is now one word
            inserted_new = False
            for idx in self._abstr_idxs:
                # If that word was affected by the replacement,
                if idx >= startidx:
                    # Make sure the index of the newly replaced phrase is
                    # inserted into its place.
                    if not inserted_new:
                        ab_replaced._abstr_idxs.append(startidx)
                        inserted_new = True
                    # Unless that word was replaced away itself,
                    if idx > startidx + len(orig):
                        # Note its new index.
                        ab_replaced._abstr_idxs.append(idx + shift)
                else:
                    ab_replaced._abstr_idxs.append(idx)
            # Make sure the index of the newly replaced phrase has been
            # inserted into its place.
            if not inserted_new:
                ab_replaced._abstr_idxs.append(startidx)
            self._abstr_idxs = ab_replaced._abstr_idxs
        return ab_replaced

# Helper methods for the Abstracted class.
AbstractedUtterance.replace_typeval = AbstractedUtterance.replace


class UtteranceFeatures(Features):
    """Represents the vector of features for an utterance.

    The class also provides methods for manipulation of the feature vector,
    including extracting features from an utterance.

    Currently, only n-gram (including skip n-grams) features are implemented.

    Attributes:
        type: type of features ('ngram')
        size: size of features (an integer)
        features: mapping { feature : value of feature (# occs) }

    """
    def __init__(self, type='ngram', size=3, utterance=None):
        """Creates a vector of utterance features if `utterance' is provided.
        Otherwise, just saves the type and size of features requested.

        Keyword arguments:
            - type: the type of features as a string; currently only 'ngram' is
                implemented
            - size: maximum order of the (n-gram) features.  For skip n-grams,
                this is the distance between the first and last word plus one.
                Moreover, skip n-grams are considered only up to the length 4.
            - utterance: the utterance for which to extract the features;
                If utterance is None (the default), an all-zeroes vector is
                created.

                Otherwise, utterance must be an instance of Utterance.

        """
        # This initialises the self.features field.
        super(UtteranceFeatures, self).__init__()

        self.type = type
        self.size = size

        if utterance is not None:
            self.parse(utterance)

    def parse(self, utterance):
        """Extracts the features from `utterance'."""
        if utterance.isempty():
            self.features['__empty__'] += 1.0
        elif self.type == 'ngram':
            # Compute shorter n-grams.
            for word in utterance:
                self.features[(word, )] += 1.
            if self.size >= 2:
                for ngram in utterance.iter_ngrams(2, with_boundaries=True):
                    self.features[tuple(ngram)] += 1.
            # Compute n-grams and skip n-grams for size 3.
            if self.size >= 3:
                for ngram in utterance.iter_ngrams(3, with_boundaries=True):
                    self.features[tuple(ngram)] += 1.
                    self.features[(ngram[0], '*1', ngram[2])] += 1.
            # Compute n-grams and skip n-grams for size 4.
            if self.size >= 4:
                for ngram in utterance.iter_ngrams(4, with_boundaries=True):
                    self.features[tuple(ngram)] += 1.
                    self.features[(ngram[0], '*2', ngram[3])] += 1.
            # Compute longer n-grams.
            for length in xrange(5, self.size + 1):
                for ngram in utterance.iter_ngrams(length,
                                                   with_boundaries=True):
                    self.features[tuple(ngram)] += 1.
        else:
            raise NotImplementedError(
                "Features can be extracted only from an empty utterance or "
                "for the `ngrams' feature type.")

        # FIXME: This is a debugging behaviour. Condition on DEBUG or `verbose'
        # etc. or raise it as an exception.
        if len(self.features) == 0:
            print '(EE) Utterance with no features: "{utt}"'.format(
                utt=utterance.utterance)


class UtteranceHyp(ASRHypothesis):
    """Provide an interface for 1-best hypothesis from the ASR component."""
    def __init__(self, prob=None, utterance=None):
        self.prob = prob
        self.utterance = utterance

    def __str__(self):
        return "%.3f %s" % (self.prob, self.utterance)

    def get_best_utterance(self):
        return self.utterance


class UtteranceNBList(ASRHypothesis, NBList):
    """Provides functionality of n-best lists for utterances.

    When updating the n-best list, one should do the following.

    1. add utterances or parse a confusion network
    2. merge and normalise, in either order

    Attributes:
        n_best: the list containing pairs [prob, utterance] sorted from the
                most probable to the least probable ones

    """
    def __init__(self):
        NBList.__init__(self)

    def get_best_utterance(self):
        """Returns the most probable utterance.

        DEPRECATED. Use get_best instead.

        """
        return self.get_best()

    def get_best(self):
        if self.n_best[0][1] == '__other__':
            return self.n_best[1][1]
        return self.n_best[0][1]

    # TODO Replace with NBList.normalise.
    def scale(self):
        """Scales the n-best list to sum to one."""
        return NBList.normalise(self)

    def normalise(self):
        """The N-best list is extended to include the "__other__" utterance to
        represent those utterance hypotheses which are not included in the
        N-best list.

        DEPRECATED. Use add_other instead.

        """
        return self.add_other()

    def add_other(self):
        try:
            return NBList.add_other(self, Utterance('__other__'))
        except NBListException as ex:
            # DEBUG
            import ipdb; ipdb.set_trace()
            raise UtteranceNBListException(ex)

    # XXX It is now a class invariant that the n-best list is sorted.
    def sort(self):
        """DEPRECATED, going to be removed."""
        return self
        # self.n_best.sort(reverse=True)


class UtteranceNBListFeatures(Features):
    # TODO Document.
    def __init__(self, type='ngram', size=3, utt_nblist=None):
        # This initialises the self.features field.
        super(UtteranceNBListFeatures, self).__init__()

        self.type = type
        self.size = size

        if utt_nblist is not None:
            self.parse(utt_nblist)

    def parse(self, utt_nblist):
        """This should be called only once during the object's lifetime,
        preferrably from within the initialiser.
        """
        first_utt_feats = None
        for hyp_idx, hyp in enumerate(utt_nblist):
            prob, utt = hyp
            utt_feats = UtteranceFeatures(type=self.type,
                                          size=self.size,
                                          utterance=utt)
            if first_utt_feats is None:
                first_utt_feats = utt_feats
            for feat, feat_val in utt_feats.iteritems():
                # Include the first rank of features occurring in the n-best list.
                if (0, feat) not in self.features:
                    self.features[(0, feat)] = float(hyp_idx)
                # Include the weighted features of individual hypotheses.
                self.features[(1, feat)] += prob * feat_val
        # Add features of the top utterance
        if first_utt_feats is None:
            self.features[(2, None)] = 1.
        else:
            self.features[(2, 'prob')] = utt_nblist[0][0]
            for feat, feat_val in first_utt_feats.iteritems():
                self.features[(2, feat)] = feat_val


# TODO Abstract to ml.features.ConfusionNetwork (not a typed one).
# TODO Make UtteranceConfusionNetwork inherit from Abstracted. It is already
# handled in dailrclassifier._extract_feats_from_one.  Once the class is
# defined, try providing input from ASR in the form of the
# AbstractedConfusionNetwork, extracting features from its instantiations and
# subsequently processing these as usual.
class UtteranceConfusionNetwork(ASRHypothesis, Abstracted):
    """Word confusion network

    Attributes:
        cn: a list of alternatives of the following signature
            [word_index-> [ alternative ]]

    XXX Are the alternatives always sorted wrt their probability in
    a decreasing order?

    """

    def __init__(self):
        self.cn = []

    def __str__(self):
        s = []
        for alts in self.cn:
            ss = []
            for p, w in alts:
                ss.append("(%.3f : %s) " % (p, w if w else '-'))
            s.append(' '.join(ss))

        return '\n'.join(s)

    def __len__(self):
        return len(self.cn)

    def __getitem__(self, i):
        return self.cn[i]

    def __iter__(self):
        for i in self.cn:
            yield i

    # Abstracted implementations.
    # TODO
    def iter_instantiations(self):
        return

    def iter_typeval(self, type_, val):
        return

    def iter_triples(self, type_, val):
        return

    def instantiate(self, type_, val, do_abstract=False):
        return self

    # Other methods.
    def isempty(self):
        return not self.cn
    def add(self, words):
        """Adds the next word with its alternatives."""
        self.cn.append(words)

    def get_best_utterance(self):
        utterance = []
        for alts in self.cn:
            utterance.append(alts[0][1])

        return ' '.join(utterance).strip()

    def get_best_hyp(self):
        utterance = []
        prob = 1.0
        for alts in self.cn:
            utterance.append(alts[0][1])
            prob *= alts[0][0]

        # FIXME Make an utterance constructor that accepts the sentence already
        # tokenized. Doing it this way may not preserve segmentation into
        # phrases (if they contain whitespace).
        utterance = ' '.join(utterance).strip()
        return (prob, Utterance(utterance))

    def get_prob(self, hyp_index):
        """Return a probability of the given hypothesis."""

        prob = 1.0
        for i, alts in zip(hyp_index, self.cn):
            prob *= alts[i][0]

        return prob

    def get_next_worse_candidates(self, hyp_index):
        """Returns such hypotheses that will have lower probability. It assumes
        that the confusion network is sorted."""
        worse_hyp = []

        for i in range(len(hyp_index)):
            wh = list(hyp_index)
            wh[i] += 1
            if wh[i] >= len(self.cn[i]):
                # this generate inadmissible word hypothesis
                continue

            worse_hyp.append(tuple(wh))

        return worse_hyp

    def get_hyp_index_utterence(self, hyp_index):
        s = [alts[i][1] for i, alts in zip(hyp_index, self.cn)]

        return Utterance(' '.join(s))

    def get_utterance_nblist(self, n=10, expand_upto_total_prob_mass=0.9):
        """Parses the confusion network and generates N-best hypotheses.

        The result is a list of utterance hypotheses each with a with assigned
        probability.  The list also include the utterance "__other__" for not
        having the correct utterance in the list.
        """
        # print "Confnet:"
        # print self
        # print

        open_hyp = []
        closed_hyp = {}

        # create index for the best hypothesis
        best_hyp = tuple([0] * len(self.cn))
        best_prob = self.get_prob(best_hyp)
        open_hyp.append((best_prob, best_hyp))

        i = 0
        while open_hyp and i < n:
            i += 1

            current_prob, current_hyp_index = open_hyp.pop(0)

            if current_hyp_index not in closed_hyp:
                # process only those hypotheses which were not processed so far

                closed_hyp[current_hyp_index] = current_prob

                # print "current_prob, current_hyp_index:", current_prob,
                # current_hyp_index

                for hyp_index in self.get_next_worse_candidates(
                        current_hyp_index):
                    prob = self.get_prob(hyp_index)
                    open_hyp.append((prob, hyp_index))

                open_hyp.sort(reverse=True)

        nblist = UtteranceNBList()
        for idx in closed_hyp:
            nblist.add(closed_hyp[idx], self.get_hyp_index_utterence(idx))

        # print nblist
        # print

        nblist.merge()
        nblist.normalise()
        nblist.sort()

        # print nblist
        # print

        return nblist

    def merge(self):
        """Adds up probabilities for the same hypotheses.

        TODO: not implemented yet
        """
        pass

    def prune(self, prune_prob=0.001):
        pruned_cn = []
        for alts in self.cn:
            if not alts[0][1] and alts[0][0] > 1.0 - prune_prob:
                # prune out silences
                continue

            pruned_alts = []
            for p, w in alts:
                if p < prune_prob:
                    continue
                else:
                    pruned_alts.append([p, w])

            if pruned_alts[0][1] == "" and len(pruned_alts) == 1:
                # I pruned out all alternatives except for silence,
                # then skip this
                continue

            pruned_cn.append(alts)

        self.cn = pruned_cn

    def normalise(self):
        """Makes sure that all probabilities adds up to one."""
        for alts in self.cn:
            sum = 0.0
            for p, w in alts:
                sum += p

            for i in range(len(alts)):
                alts[i][0] /= sum

    def sort(self):
        """Sort the alternatives for each word according their probability."""

        for alts in self.cn:
            alts.sort(reverse=True)


    def iter_ngrams_fromto(self, from_=None, to=None):
        """Iterates n-gram hypotheses between the indices `from_' and `to_'."""
        cn_splice = self.cn[from_:to]
        partition = reduce(mul,
                           (sum(prob for (prob, word) in alts)
                            for alts in cn_splice),
                           1.)
        options = [xrange(len(alts)) for alts in cn_splice]
        for option_seq in product(*options):
            hyp_seq = [alts[option]
                       for (alts, option) in izip(cn_splice, option_seq)]
            measure = reduce(mul, map(itemgetter(0), hyp_seq), 1.)
            ngram = map(itemgetter(1), hyp_seq)
            yield (measure / partition, ngram)

    def iter_ngrams(self, n, with_boundaries=False):
        min_len = n - with_boundaries * 2
        # If the n-gram so-so fits into the cn.
        if len(self.cn) <= min_len:
            if len(self.cn) == min_len:
                if with_boundaries:
                    for prob, ngram in self.iter_ngrams_fromto():
                        yield (prob, [SENTENCE_START] + ngram + [SENTENCE_END])
                else:
                    for ngram_hyp in self.iter_ngrams_fromto():
                        yield ngram_hyp
            return
        # Usual cases.
        if with_boundaries and len(self.cn) > min_len:
            for prob, ngram in self.iter_ngrams_fromto(0, n - 1):
                yield (prob, [SENTENCE_START] + ngram)
        for start_idx in xrange(len(self.cn) - n + 1):
            for ngram_hyp in self.iter_ngrams_fromto(start_idx, start_idx + n):
                yield ngram_hyp
        if with_boundaries:
            for prob, ngram in self.iter_ngrams_fromto(-(n - 1), None):
                yield (prob, ngram + [SENTENCE_END])


# TODO Document.
# TODO Extend to AbstractedLattice.
# TODO Write tests.class UtteranceConfusionNetworkFeatures(Features):
class UtteranceConfusionNetworkFeatures(Features):
    """Represents features extracted from an utterance hypothesis in the form
    of a confusion network.  These are simply a probabilistic generalisation of
    simple utterance features.  Only n-gram (incl. skip n-gram) features are
    currently implemented.

    """

    def __init__(self, type='ngram', size=3, confnet=None):
        """Creates a vector of confnet features if `confnet' is provided.
        Otherwise, just saves the type and size of features requested.

        Keyword arguments:
            - type: the type of features as a string; currently only 'ngram' is
                implemented
            - size: maximum order of the (n-gram) features.  For skip n-grams,
                this is the distance between the first and last word plus one.
                Moreover, skip n-grams are considered only up to the length 4.
            - confnet: the confnet for which to extract the features;
                If confnet is None (the default), an all-zeroes vector is
                created.

                Otherwise, confnet must be an instance of
                UtteranceConfusionNetwork.

        """
        # This initialises the self.features field.
        super(UtteranceConfusionNetworkFeatures, self).__init__()

        self.type = type
        self.size = size

        if confnet is not None:
            self.parse(confnet)

    def parse(self, confnet):
        """Extracts the features from `confnet'."""
        if confnet.isempty():
            self.features['__empty__'] += 1.0
        elif self.type == 'ngram':
            # Compute shorter n-grams.
            for alts in confnet:
                for prob, word in alts:
                    self.features[(word, )] += prob
            if self.size >= 2:
                for prob, ngram in confnet.iter_ngrams(
                        2, with_boundaries=True):
                    self.features[tuple(ngram)] += prob
            # Compute n-grams and skip n-grams for size 3.
            if self.size >= 3:
                for prob, ngram in confnet.iter_ngrams(
                        3, with_boundaries=True):
                    self.features[tuple(ngram)] += prob
                    self.features[(ngram[0], '*1', ngram[2])] += prob
            # Compute n-grams and skip n-grams for size 4.
            if self.size >= 4:
                for prob, ngram in confnet.iter_ngrams(
                        4, with_boundaries=True):
                    self.features[tuple(ngram)] += prob
                    self.features[(ngram[0], '*2', ngram[3])] += prob
            # Compute longer n-grams.
            for length in xrange(5, self.size + 1):
                for prob, ngram in confnet.iter_ngrams(
                        length, with_boundaries=True):
                    self.features[tuple(ngram)] += prob
        else:
            raise NotImplementedError(
                "Features can be extracted only from an empty confnet or "
                "for the `ngrams' feature type.")

        if len(self.features) == 0:
            raise UtteranceConfusionNetworkException(
                    'No features extracted from the confnet:\n{}'.format(
                        confnet))
