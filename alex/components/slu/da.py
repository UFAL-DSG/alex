#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008/.

from __future__ import unicode_literals

import copy
import codecs

from operator import xor
from collections import defaultdict

from alex.corpustools.wavaskey import load_wavaskey, save_wavaskey
from alex.components.slu.exceptions import SLUException, DialogueActException, DialogueActItemException, \
    DialogueActConfusionNetworkException
from alex.ml.exceptions import NBListException
from alex.ml.features import Abstracted
from alex.ml.hypothesis import Hypothesis, NBList, ConfusionNetwork
from alex.utils.text import split_by


def load_das(das_fname, limit=None, encoding='UTF-8'):
    """
    Loads a dictionary of DAs from a given file.

    The file is assumed to contain lines of the following form:

        [[:space:]..]<key>[[:space:]..]=>[[:space:]..]<DA>[[:space:]..]

    or just (without keys):

        [[:space:]..]<DA>[[:space:]..]

    Arguments:
        das_fname -- path towards the file to read the DAs from
        limit -- limit on the number of DAs to read
        encoding -- the file encoding

    Returns a dictionary with DAs (instances of DialogueAct) as values.

    """
    return load_wavaskey(das_fname, DialogueAct, limit, encoding)


def save_das(file_name, das, encoding = 'UTF-8'):
    save_wavaskey(file_name, das, encoding)

class DialogueActItem(Abstracted):
    """
    Represents dialogue act item which is a component of a dialogue act.

    Each dialogue act item is composed of

        1) dialogue act type - e.g. inform, confirm, request, select, hello

        2) slot name and value pair - e.g. area, pricerange, food for name and
                                      centre, cheap, or Italian for value

    Attributes:
        dat: dialogue act type (a string)
        name: slot name (a string or None)
        value: slot value (a string or None)

    """
    splitter = ':'

    # TODO Rename dai to dai_str for sake of clarity.  Move it to the first
    # position in the argument list, so that __init__ recovers a DAI object
    # repr() would have stored (once __repr__ is implemented so).
    def __init__(self, dialogue_act_type=None, name=None, value=None,
                 dai=None, attrs=None, alignment=None):
        """
        Initialise the dialogue act item. Assigns the default values to
        dialogue act type (dat), slot name (name), and slot value (value).

        :param dialogue_act_type: dialogue act type
        :type dialogue_act_type: string
        :param name: slot name
        :type name: string
        :param value: slot value
        :type value: string
        :param dai: string representation of this DAI
        :type dai: string
        :param attrs: TODO: Document what the `attrs' kwarg is for, please.

        :param alignment: list of word indices this DAI corresponds to
        :type alignment: set[int] | None
        """
        # Store the arguments.
        self._dat = dialogue_act_type
        self._name = name
        self._value = value
        # XXX! What is this for?!
        self._attrs = {} if attrs is None else attrs
        self._alignment = alignment

        # Bookkeeping.
        self._orig_values = set()
        self._unnorm_values = set()
        self._str = None

        if dai:
            self.parse(dai)

        Abstracted.__init__(self)

    def __hash__(self):
        # Identity of a DAI is determined by its textual representation.
        # That means, if two DAIs have the same DA type, slot name, and slot
        # value, they hash to the same spot.
        return hash(unicode(self))

    def __cmp__(self, other):
        self_str, other_str = unicode(self), unicode(other)
        return (self_str >= other_str) - (self_str <= other_str)

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __repr__(self):
        return str(self)

    def __unicode__(self):
        # Cache the value for repeated calls of this method are expected.
        # This check is needed for the DAI gets into a partially constructed
        # state during copy.deepcopying.

        try:
            str_self = self._str
        except AttributeError:
            return ''
        if str_self is None:
            try:
                orig_val = next(iter(self._orig_values))
                self._str = ('{type_}({name}="{val}{spl}{orig}")'
                             .format(type_=self._dat,
                                     name=self._name or '',
                                     val=self._value,
                                     spl=DialogueActItem.splitter,
                                     orig=orig_val))
            except StopIteration:
                eq_val = ('="{val}"'.format(val=self._value)
                          if self._value else '')
                self._str = ("{type_}({name}{eq_val})"
                             .format(type_=self._dat,
                                     name=self._name or '',
                                     eq_val=eq_val))

        return self._str

    def iter_typeval(self):
        if self.has_category_label():
            for orig_val in self._orig_values:
                yield DialogueActItem.splitter.join((self.value, orig_val))

    def replace_typeval(self, orig, replacement):
        new_dai = copy.deepcopy(self)
        new_dai._str = None
        if self.value:
            insts = (DialogueActItem.splitter.join((self.value, orig))
                     for orig in self._orig_values)
            if orig in insts:
                if DialogueActItem.splitter in replacement:
                    _type, _value = replacement.split(
                        DialogueActItem.splitter, 2)
                    new_dai._value = _type
                    new_dai._orig_values = set([_value])
                else:
                    new_dai._value = replacement
                    new_dai._orig_values = set([_value])
        return new_dai

    @property
    def dat(self):
        return self._dat

    @dat.setter
    def dat(self, newval):
        self._dat = newval
        self._str = None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, newval):
        self._name = newval
        self._str = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, newval):
        self._value = newval
        self._str = None

    @property
    def orig_values(self):
        return self._orig_values

    @property
    def unnorm_values(self):
        return self._unnorm_values or self._orig_values or set((self._value, ))

    @property
    def alignment(self):
        return self._alignment if not self.is_null() else {-1}

    def has_category_label(self):
        """whether the current DAI value is the category label"""
        return bool(self._orig_values)  # whether there was an original value
                                        # that got substituted (assumably by
                                        # a category label)

    def is_null(self):
        """whether this object represents the 'null()' DAI"""
        return (self._dat == 'null'
                and self._name is None
                and self._value is None)

    def extension(self):
        """Returns an extension of self, i.e., a new DialogueActItem without
        hidden fields, such as the original value/category label.

        """
        return DialogueActItem(dialogue_act_type=self._dat,
                               name=self._name,
                               value=self._value)

    def _update_unnorm_values(self):
        """Makes sure all original values have been stored in
        self._unnorm_values.

        """
        if not self._unnorm_values:
            if self._orig_values:
                self._unnorm_values.update(self._orig_values)
            else:
                self._unnorm_values.add(self._value)

    def get_unnorm_values(self):
        """Retrieves the original unnormalised vaues of this DAI."""
        self._update_unnorm_values()
        return self._unnorm_values

    def add_unnorm_value(self, newval):
        """Registers `newval' as another alternative unnormalised value for the
        value of this DAI's slot.

        """
        self._update_unnorm_values()
        self._unnorm_values.add(newval)

    def merge_unnorm_values(self, other):
        """Merges unnormalised values of `other' to unnormalised values of
        `self'.

        """
        self._update_unnorm_values()
        # Add the requested new unnormalised value.
        self._unnorm_values.update(other.unnorm_values)

    # The original value is always in self._value or in self._orig_values.  In
    # the latter case, self._value contains the category label.
    #
    # In contrast to self._orig_values, self._orig_label is defined only after
    # a call to category_label2value, and it may be the value of
    # `self._orig_label' and `self._value' simultaneously.

    def value2category_label(self, label=None):
        """Use this method to substitute a category label for value of this
        DAI.

        """
        self._orig_values.add(self._value)
        if label is None:
            try:
                self.value = self._orig_label
            except AttributeError:
                raise DialogueActItemException(
                    'No label has ever been assigned to this DAI, and none '
                    '(or None) was supplied as an argument.')
        else:
            self.value = label

    def category_label2value(self, catlabs=None):
        """Use this method to substitute back the original value for the
        category label as the value of this DAI.

        Arguments:
            catlabs: an optional mapping of category labels to tuples (slot
                     value, surface form), as obtained from
                     alex.components.slu:SLUPreprocessing

                     If this object does not remember its original value, it
                     takes it from the provided mapping.

        """
        newval = None
        try:
            # Try to use the remembered value.
            if bool(self._orig_values):
                newval = self._orig_values.pop()
        except AttributeError:
            # Be tolerant to older models, which break the current contract.
            pass
        if newval is not None:
            pass
        # Try to use the argument.
        elif catlabs is not None and self._value in catlabs:
            newval = catlabs[self._value][0]
        # Else, do nothing.
        else:
            return

        # Do the swap.
        self._orig_label = self._value
        self.value = newval

    def value2normalised(self, normalised):
        """Use this method to substitute a normalised value for value of this
        DAI.

        """
        self._unnorm_values.add(self._value)
        self.value = normalised

    def normalised2value(self):
        """Use this method to substitute back an unnormalised value for the
        normalised one as the value of this DAI.

        Returns True iff substitution took place.  Returns False if no more
        unnormalised values are remembered as a source for the normalised
        value.

        """
        # Try to use the remembered value.
        if bool(self._unnorm_values):
            self.value = self._unnorm_values.pop()
            return True
        else:
            return False

    def parse(self, dai_str):
        """
        Parses the dialogue act item in text format into a structured form.
        """
        dai_str = dai_str.strip()

        try:
            first_par_idx = dai_str.index('(')
        except ValueError:
            raise DialogueActItemException(
                'Parsing error in: "{dai}". Missing opening parenthesis.'
                .format(dai=dai_str))

        self._dat = dai_str[:first_par_idx]

        # Remove the parentheses, parse slot name and value.
        dai_nv = dai_str[first_par_idx + 1:-1]
        if dai_nv:
            name_val = split_by(dai_nv, splitter='=', quotes='"')
            if len(name_val) == 1:
                # There is only a slot name.
                self._name = name_val[0]
            elif len(name_val) == 2:
                # There is a slot name and a value.
                self._name = name_val[0]
                self._value = name_val[1]
                if self._value and self._value[0] in ["'", '"']:
                    self._value = self._value[1:-1]
            else:
                raise DialogueActItemException(
                    "Parsing error in: {dai_str}: {atval}".format(
                        dai_str=dai_str, atval=name_val))

        self._str = None
        return self


class DialogueAct(object):
    """
    Represents a dialogue act (DA), i.e., a set of dialogue act items (DAIs).

    The DAIs are stored in the `dais' attribute, sorted w.r.t. their string
    representation.  This class is not responsible for discarding a DAI which
    is repeated several times, so that you can obtain a DA that looks like
    this:

        inform(food="chinese")&inform(food="chinese")

    Attributes:
        dais: a list of DAIs that constitute this dialogue act

    """
    # XXX For developers:
    # When altering self._dais, just make sure self._dais_sorted is updated
    # too.

    def __init__(self, da_str=None):
        """Initialises this DA.

        Arguments:
            da: a string representation of a DA to parse and initialise this
                object from

        """
        self._dais = []
        """:type : list[DialogueActItem]"""

        if da_str is not None:
            if not isinstance(da_str, basestring):
                raise DialogueActException("DialogueAct can only be "
                                           "constructed from a basestring.")
            self.parse(da_str)

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
        return '&'.join(unicode(dai) for dai in self._dais)

    def __contains__(self, dai):
        return ((isinstance(dai, DialogueActItem) and dai in self._dais) or
                (isinstance(dai, basestring)
                 and any(dai == unicode(my_dai) for my_dai in self._dais)))

    def __cmp__(self, other):
        if isinstance(other, DialogueAct):
            if self._dais == other.dais:
                return 0
            self_str = unicode(self)
            mydais_sorted = (self._dais if self._dais_sorted else
                             sorted(self._dais))
            theirdais_sorted = (other._dais if other._dais_sorted else
                                sorted(other._dais))
            return ((mydais_sorted >= theirdais_sorted) -
                    (theirdais_sorted >= mydais_sorted))
        elif isinstance(other, basestring):
            mydais_sorted = sorted(self._dais)
            self_sorted = DialogueAct()
            self_sorted._dais = mydais_sorted
            self_str = unicode(self_sorted)
            return (self_str >= other) - (other >= self_str)
        else:
            DialogueActException("Unsupported comparison type.")

    def __hash__(self):
        return reduce(xor, map(hash, enumerate(self._dais)), 0)

    def __len__(self):
        return len(self._dais)

    def __getitem__(self, idx):
        return self._dais[idx]

    def __setitem__(self, idx, val):
        assert isinstance(val, DialogueActItem)
        self._dais[idx] = val
        self._dais_sorted = False

    def __iter__(self):
        for dai in self._dais:
            yield dai

    @property
    def dais(self):
        return self._dais

    def has_dat(self, dat):
        """Checks whether any of the dialogue act items has a specific dialogue
        act type.

        """
        return any(dai.dat == dat for dai in self._dais)

    def has_only_dat(self, dat):
        """Checks whether all the dialogue act items has a specific dialogue
        act type.

        """
        return all(dai.dat == dat for dai in self._dais)

    def parse(self, da_str):
        """
        Parses the dialogue act from text.

        If any DAIs have been already defined for this DA, they will be
        overwritten.

        """
        if self._dais:
            del self._dais[:]
        dais = split_by(da_str, splitter='&', opening_parentheses='(',
                        closing_parentheses=')', quotes='"')
        self._dais.extend(DialogueActItem(dai=dai) for dai in dais)
        self._dais_sorted = False

    def append(self, dai):
        """Append a dialogue act item to the current dialogue act."""
        if isinstance(dai, DialogueActItem):
            self._dais.append(dai)
            self._dais_sorted = False
        else:
            raise DialogueActException(
                "Only DialogueActItems can be appended.")

    def extend(self, dais):
        if not all(isinstance(obj, DialogueActItem) for obj in dais):
            raise DialogueActException("Only DialogueActItems can be added.")
        self._dais.extend(dais)
        self._dais_sorted = False
        return self

    def get_slots_and_values(self):
        """Returns all slot names and values in the dialogue act."""
        return [[dai.name, dai.value] for dai in self._dais if dai.value]

    def sort(self):
        """Sorts own DAIs and merges the same ones."""
        self._dais.sort()
        self._dais_sorted = True
        self.merge_same_dais()
        return self

    def merge(self, da):
        """Merges another DialogueAct into self.  This is done by concatenating
        lists of the DAIs, and sorting and merging own DAIs afterwards.

        If sorting is not desired, use `extend' instead.

        """
        if not isinstance(da, DialogueAct):
            raise DialogueActException("DialogueAct can only be merged with another DialogueAct")
        self._dais.extend(da.dais)
        self.sort()
        return self

    def merge_same_dais(self):
        """Merges same DAIs.  I.e., if they are equal on extension but differ
        in original values, merges the original values together, and keeps the
        single DAI.  This method causes the list of DAIs to be sorted.

        """
        if len(self._dais) < 2:
            return

        if not self._dais_sorted:
            self._dais.sort()
            self._dais_sorted = True

        new_dais = list()
        prev_dai = self._dais[0]
        for dai in self._dais[1:]:
            if prev_dai == dai:
                dai.merge_unnorm_values(prev_dai)
            else:
                new_dais.append(prev_dai)
            prev_dai = dai
        else:
            new_dais.append(dai)
        self._dais = new_dais
        return self



class SLUHypothesis(Hypothesis):
    """This is the base class for all forms of probabilistic SLU hypotheses
    representations.

    """
    pass


class DialogueActHyp(SLUHypothesis):
    """Provides functionality of 1-best hypotheses for dialogue acts."""

    def __init__(self, prob=None, da=None):
        self.prob = prob
        self.da = da

    def __str__(self):
        return unicode(self).encode('ascii', 'replace')

    def __unicode__(self):
        return "%.3f %s" % (self.prob, unicode(self.da))

    def get_best_da(self):
        return self.da

    def get_da_nblist(self):
        # AUTHOR: Oplatek
        # REASON: webhub supposed that slu_hyp must have get_da_nblist method see error
        # SOLUTION: get_da_nblist will return nblist get_best_da(self) -> TEMPORARY-> FIXME
        # Error:
        #  File "/a/LRC_TMP/oplatek/vystadial/alex/components/hub/slu.py", line 119, in run
        #  self.read_asr_hypotheses_write_slu_hypotheses()
        #  File "/a/LRC_TMP/oplatek/vystadial/alex/components/hub/slu.py", line 98, in read_asr_hypotheses_write_slu_hypotheses
        #  self.cfg['Logging']['session_logger'].slu("user", slu_hyp.get_da_nblist(), slu_hyp)
        # The error occured when running webhub.py.
        return DialogueActNBList().add(1.0, self.get_best_da())


class DialogueActNBList(SLUHypothesis, NBList):
    """Provides functionality of N-best lists for dialogue acts.

    When updating the N-best list, one should do the following.

    1. add DAs or parse a confusion network
    2. merge and normalise, in either order

    Attributes:
        n_best: the list containing pairs [prob, DA] sorted from the most
                probable to the least probable ones

    """

    def __init__(self):
        NBList.__init__(self)

    def get_best_da(self):
        """Returns the most probable dialogue act.

        DEPRECATED. Use get_best instead.

        """
        return self.n_best[0][1]

    def get_best_nonnull_da(self):
        """Return the best dialogue act (with the highest probability)."""

        for p, da in self.n_best:
            if da[0].dat != "null":
                return da

        return self.get_best_da()

    # TODO Replace with NBList.normalise.
    def scale(self):
        """Scales the n-best list to sum to one."""
        return NBList.normalise(self)

    def normalise(self):
        """The N-best list is extended to include the "other()" dialogue act to
        represent those semantic hypotheses which are not included in the
        N-best list.

        DEPRECATED. Use add_other instead.

        """
        return self.add_other()

    def add_other(self):
        try:
            return NBList.add_other(self, DialogueAct('other()'))
        except NBListException as e:
            raise DialogueActNBListException(e)

    def merge(self):
        """Adds up probabilities for the same hypotheses.  Takes care to keep
        track of original, unnormalised DAI values.  Returns self."""
        if len(self.n_best) <= 1:
            return
        else:
            new_n_best = self.n_best[:1]

            for cur_idx in xrange(1, len(self.n_best)):
                cur_hyp = self.n_best[cur_idx]
                for new_idx, new_hyp in enumerate(new_n_best):
                    if new_hyp[1] == cur_hyp[1]:
                        # Merge, add the probabilities.
                        new_da = new_hyp[1]
                        for dai in cur_hyp[1]:
                            new_dais = (new_dai for new_dai in new_da if
                                        new_dai == dai)
                            for new_dai in new_dais:
                                new_dai._unnorm_values.update(
                                    dai._unnorm_values)
                        new_hyp[0] += cur_hyp[0]
                        break
                else:
                    new_n_best.append(cur_hyp)

        self.n_best = sorted(new_n_best, reverse=True)
        return self

    def get_confnet(self):
        confnet = DialogueActConfusionNetwork()

        for prob, da in self.n_best:
            for dai in da:
                confnet.add_merge(prob, dai, combine='add')

        confnet.sort()
        return confnet


    # XXX It is now a class invariant that the n-best list is sorted.
    def sort(self):
        """DEPRECATED, going to be removed."""
        return self
        # self.n_best.sort(reverse=True)

    def has_dat(self, dat):
        return any(map(lambda hyp: hyp[1].has_dat(dat), self.n_best))


class DialogueActConfusionNetwork(SLUHypothesis, ConfusionNetwork):
    """
    Dialogue act item confusion network. This is a very simple implementation
    in which all dialogue act items are assumed to be independent.  Therefore,
    the network stores only posteriors for dialogue act items.

    This can be efficiently stored as a list of DAIs each associated with its
    probability.  The alternative for each DAI is that there is no such DAI in
    the DA. This can be represented as the null() dialogue act and its
    probability is 1 - p(DAI).

    If there are more than one null() DA in the output DA, then they are
    collapsed into one null() DA since it means the same.

    Please note that in the confusion network, the null() dialogue acts are not
    explicitly modelled.

    """
    def __init__(self):
        ConfusionNetwork.__init__(self)

    def __unicode__(self):
        # DAs in a DA confnet are in no particular order, so we sort them here.
        ret = []
        for prob, dai in sorted(self, reverse=True):
            ret.append("{prob:.3f} {dai!s}".format(prob=prob, dai=unicode(dai)))

        return "\n".join(ret)

    def __repr__(self):
        return unicode(self)

    def items(self):
        return list(self)

    def get_best_da(self):
        """Return the best dialogue act (one with the highest probability)."""
        da = DialogueAct()
        for prob, dai in self:
            if prob >= 0.5:
                da.append(dai)

        if len(da) == 0:
            da.append(DialogueActItem('null'))

        return da

    def get_best_nonnull_da(self):
        """
        Return the best dialogue act (with the highest probability) ignoring the best null() dialogue act item.

        Instead of returning the ``null()`` act, it returns the most probable DAI with a defined slot name.

        """

        res = self.get_best_da()

        if res[0].dat == "null":
            da = DialogueAct()
            for prob, dai in sorted(self, reverse=True):
                if dai.name is not None and len(dai.name) > 0:
                    da.append(dai)
                    break

            if len(da) == 0:
                da.append(DialogueActItem('null'))

            res = da

        return res

    def get_best_da_hyp(self, use_log=False, threshold=None, thresholds=None):
        """Return the best dialogue act hypothesis.

        Arguments:
            use_log: whether to express probabilities on the log-scale
                     (otherwise, they vanish easily in a moderately long
                     confnet)
            threshold: threshold on probabilities -- items with probability
                       exceeding the threshold will be present in the output
                       (default: 0.5)
            thresholds: threshold on probabilities -- items with probability
                       exceeding the threshold will be present in the output.
                       This is a mapping {dai -> threshold}, and if supplied,
                       overwrites settings of `threshold'.  If not supplied, it
                       is ignored.

        """
        if thresholds is None:
            threshold = threshold if threshold is not None else .5
            thresholds = defaultdict(lambda: threshold)
        da = DialogueAct()
        if use_log:
            from math import log
            logprob = 0.
        else:
            prob = 1.0
        for edge_p, dai in self:
            if edge_p > thresholds[dai]:
                da.append(dai)
                # multiply with probability of presence of a dialogue act
                if use_log:
                    logprob += log(edge_p)
                else:
                    prob *= edge_p
            else:
                # multiply with probability of exclusion of the dialogue act
                if use_log:
                    logprob += log(1. - edge_p)
                else:
                    prob *= (1. - edge_p)

        if len(da) == 0:
            da.append(DialogueActItem('null'))

        # (FIXME) DialogueActHyp still thinks it uses linear-scale
        # probabilities.
        return DialogueActHyp(logprob if use_log else prob, da)

    def _get_prob(self, hyp_index, cn=None):
        """Return a probability of the given hypothesis."""

        if not cn:
            cn = self

        prob = 1.0
        for i, (p, dai) in zip(hyp_index, cn):
            if i == 0:
                prob *= p
            else:
                prob *= (1 - p)

        return prob

    def _get_next_worse_candidates(self, hyp_index, cn=None):
        """
        Returns such hypotheses that will have lower probability.

        """
        if not cn:
            cn = list(self)
        worse_hyp = []

        for i in range(len(hyp_index)):
            wh = list(hyp_index)
            wh[i] += 1
            if cn[i][0] < 0.5 and wh[i] >= 2:
                wh[i] = 0

            if wh[i] >= 2:
                # this generate inadmissible da hypothesis
                # because there are only two alternatives - the DAI and the
                # null() dialogue act
                continue

            worse_hyp.append(tuple(wh))

        return worse_hyp

    def _get_hyp_index_dialogue_act(self, hyp_index, cn=None):
        if not cn:
            cn = self

        da = DialogueAct()
        for i, (p, dai) in zip(hyp_index, cn):
            if i == 0:
                da.append(dai)

        if len(da) == 0:
            da.append(DialogueActItem('null'))

        return da

    def get_da_nblist(self, n=10, prune_prob=0.005):
        """Parses the input dialogue act item confusion network and generates N-best hypotheses.

        The result is a list of dialogue act hypotheses each with a with
        assigned probability.  The list also include a dialogue act for not
        having the correct dialogue act in the list - other().

        Generation of hypotheses will stop when the probability of the hypotheses is smaller then the ``prune_prob``.

        """

        #print "cn", [(p, unicode(dai)) for p, dai in self.cn]

        open_hyp = []
        closed_hyp = {}

        cn = sorted(self, reverse=True)

        for j, (p, dai) in enumerate(cn):
            if p < 0.5:
                i = j
                break
        else:
            i = len(cn)

        # create index for the best hypothesis
        best_hyp = tuple([0,] * i + [1,] * (len(cn) - i))
        best_prob = self._get_prob(best_hyp, cn=cn)
        open_hyp.append((best_prob, best_hyp))
        #print "i, bp, bh", i, best_prob, best_hyp

        i = 0
        while open_hyp and i < n*100:
            i += 1

            current_prob, current_hyp_index = open_hyp.pop(0)

            if current_hyp_index not in closed_hyp:
                # process only those hypotheses which were not processed so far

                closed_hyp[current_hyp_index] = current_prob
                # print "current_prob, current_hyp_index:", current_prob, current_hyp_index

                for hyp_index in self._get_next_worse_candidates(current_hyp_index, cn=cn):
                    # print hyp_index
                    prob = self._get_prob(hyp_index, cn=cn)
                    open_hyp.append((prob, hyp_index))

                open_hyp.sort(reverse=True)

            if len(closed_hyp) >= n:
                break

        nblist = DialogueActNBList()
        for idx in closed_hyp:
            # print "p = ",closed_hyp[idx], "hyp = ", self._get_hyp_index_dialogue_act(idx)
            nblist.add(closed_hyp[idx], self._get_hyp_index_dialogue_act(idx, cn=cn))

        #print nblist
        #print

        nblist.merge()
        nblist.add_other()

        #print nblist
        #print

        return nblist




    @classmethod
    def make_from_da(self, da):
        cn = DialogueActConfusionNetwork()
        for dai in da:
            cn.add(1.0, dai)
        return cn


def merge_slu_nblists(multiple_nblists):
    """Merge multiple dialogue act N-best lists."""

    merged_nblists = DialogueActNBList()

    for prob_nblist, nblist in multiple_nblists:
        if not isinstance(nblist, DialogueActNBList):
            raise SLUException("Cannot merge something that is not DialogueActNBList.")
        nblist.merge()
        nblist.add_other()

        for prob, da in nblist:
            merged_nblists.add(prob_nblist * prob, da)

    merged_nblists.merge()
    merged_nblists.add_other()

    return merged_nblists


def merge_slu_confnets(confnet_hyps):
    """Merge multiple dialogue act confusion networks."""

    merged = DialogueActConfusionNetwork()

    for prob_confnet, confnet in confnet_hyps:
        if not isinstance(confnet, DialogueActConfusionNetwork):
            raise SLUException("Cannot merge something that is not a DialogueActConfusionNetwork.")

        for prob, dai in confnet:
            # it is not clear why I wanted to remove all other() dialogue acts
            # if dai.dat == "other":
            #     continue

            merged.add_merge(prob_confnet * prob, dai, combine='add')

    merged.sort()

    return merged
