#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008/.

from collections import defaultdict
from operator import xor

from alex.utils.text import split_by
from alex.utils.exception import SLUException, DialogueActException, \
    DialogueActItemException, DialogueActNBListException, \
    DialogueActConfusionNetworkException


def load_das(das_fname, limit=None):
    """Loads a dictionary of DAs from a given file. The file is assumed to
    contain lines of the following form:

    [whitespace..]<key>[whitespace..]=>[whitespace..]<DA>[whitespace..]

    Arguments:
        das_fname -- path towards the file to read the DAs from
        limit -- limit on the number of DAs to read

    Returns a dictionary with DAs (instances of DialogueAct) as values.

    """
    with open(das_fname) as das_file:
        das = defaultdict(list)
        count = 0
        for line in das_file:
            count += 1
            if limit and count > limit:
                break

            line = line.strip()
            if not line:
                continue

            parts = line.split("=>")

            key = parts[0].strip()
            sem = parts[1].strip()

            das[key] = DialogueAct(sem)

    return das


def save_das(file_name, das):
    f = open(file_name, 'w+')

    for u in sorted(das):
        f.write(u)
        f.write(" => ")
        f.write(str(das[u]) + '\n')

    f.close()


class DialogueActItem(object):
    """Represents dialogue act item which is a component of a dialogue act.
    Each dialogue act item is composed of

        1) dialogue act type - e.g. inform, confirm, request, select, hello

        2) slot name and value pair - e.g. area, pricerange, food for name and
                                      centre, cheap, or Italian for value

    Attributes:
        dat: dialogue act type (a string)
        name: slot name (a string)
        value: slot value (a string)

    """
    def __init__(self, dialogue_act_type=None, name=None, value=None,
                 dai=None):
        """Initialise the dialogue act item. Assigns the default values to
        dialogue act type (dat), slot name (name), and slot value (value).

        """
        # Store the arguments.
        self._dat = dialogue_act_type
        self._name = name
        self._value = value

        # Bookkeeping.
        self._orig_values = set()
        self._unnorm_values = set()
        self._str = None

        if dai:
            self.parse(dai)

    def __hash__(self):
        # Identity of a DAI is determined by its textual representation.
        # That means, if two DAIs have the same DA type, slot name, and slot
        # value, they hash to the same spot.
        return hash(str(self))

    def __cmp__(self, other):
        self_str, other_str = str(self), str(other)
        return (self_str >= other_str) - (self_str <= other_str)

    def __str__(self):
        # Cache the value for repeated calls of this method are expected.
        if self._str is None:
            eq_val = '="{val}"'.format(val=self._value) if self._value else ''
            self._str = ("{type_}({name}{eq_val})"
                         .format(type_=self._dat,
                                 name=self._name or '',
                                 eq_val=eq_val))
        return self._str

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
    def unnorm_values(self):
        return self._unnorm_values or self._orig_values or set((self._value, ))

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

    # TODO This should perhaps be a class method.
    def parse(self, dai_str):
        """Parses the dialogue act item in text format into a structured form.
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
                if self._value[0] in ["'", '"']:
                    self._value = self._value[1:-1]
            else:
                raise DialogueActItemException(
                    "Parsing error in: {dai_str}: {atval}".format(
                        dai_str=dai_str, atval=name_val))

        self._str = None
        return self


class DialogueAct(object):
    """Represents a dialogue act (DA), i.e., a set of dialogue act items
    (DAIs).  The DAIs are stored in the `dais' attribute, sorted w.r.t. their
    string representation.  This class is not responsible for discarding a DAI
    which is repeated several times, so that you can obtain a DA that looks
    like this:

        inform(food="chinese")&inform(food="chinese")

    """

    def __init__(self, da=None):
        """Initialises this DA.

        Arguments:
            da: a string representation of a DA to parse and initialise this
                object from

        """
        self.dais = []

        if da is not None:
            self.parse(da)

    def __str__(self):
        return '&'.join(str(dai) for dai in self.dais)

    def __contains__(self, dai):
        return ((isinstance(dai, DialogueActItem) and dai in self.dais) or
                (isinstance(dai, str)
                 and any(map(lambda my_dai: dai == str(my_dai), self.dais))))

    def __cmp__(self, other):
        if isinstance(other, DialogueAct):
            if self.dais == other.dais:
                return 0
            self_str = str(self)
            return (self.dais >= other.dais) - (other.dais >= self.dais)
        elif isinstance(other, str):
            self_str = str(self)
            return (self_str >= other) - (other >= self_str)
        else:
            DialogueActException("Unsupported comparison type.")

    def __hash__(self):
        return reduce(xor, map(hash, enumerate(self.dais)), 0)

    def __len__(self):
        return len(self.dais)

    def __getitem__(self, idx):
        return self.dais[idx]

    def __iter__(self):
        for dai in self.dais:
            yield dai

    def has_dat(self, dat):
        """Checks whether any of the dialogue act items has a specific dialogue
        act type.

        """
        return any(map(lambda dai: dai.dat == dat, self.dais))

    def has_only_dat(self, dat):
        """Checks whether all the dialogue act items has a specific dialogue
        act type.

        """
        return all(map(lambda dai: dai.dat == dat, self.dais))

    # TODO Make into a class method.
    def parse(self, da):
        """Parse the dialogue act in text format into the structured form.  If
        any DAIs have been already defined for this DA, they will be
        overwritten.

        """
        if self.dais:
            del self.dais[:]
        dais = sorted(split_by(da, splitter='&', opening_parentheses='(',
                               closing_parentheses=')', quotes='"'))
        self.dais.extend(DialogueActItem(dai=dai) for dai in dais)

    def append(self, dai):
        """Append a dialogue act item to the current dialogue act."""
        if isinstance(dai, DialogueActItem):
            insert_idx = len(self.dais)
            while insert_idx > 0:
                insert_idx -= 1
                if dai >= self.dais[insert_idx]:
                    if dai == self.dais[insert_idx]:
                        self.dais[insert_idx].merge_unnorm_values(dai)
                        return self
                    insert_idx += 1
                    break
            self.dais.insert(insert_idx, dai)
            return self
        else:
            raise DialogueActException(
                "Only DialogueActItems can be appended.")

    def extend(self, dais):
        if not all(map(lambda obj: isinstance(obj, DialogueActItem), dais)):
            raise DialogueActException("Only DialogueActItems can be added.")
        self.dais.extend(dais)
        self.sort()
        return self

    def get_slots_and_values(self):
        """Returns all slot names and values in the dialogue act."""
        return [[dai.name, dai.value] for dai in self.dais if dai.value]

    def sort(self):
        self.dais.sort()
        self.merge_same_dais()
        return self

    def merge(self, da):
        """Merges another DialogueAct into self."""
        if not isinstance(da, DialogueAct):
            raise DialogueActException("DialogueAct can only be merged with "
                                       "another DialogueAct")
        self.dais.extend(da.dais)
        self.sort()
        return self

    def merge_same_dais(self):
        """Merges same DAIs.  I.e., if they are equal on extension but differ
        in original values, merges the original values together, and keeps the
        single DAI.

        """
        if len(self.dais) < 2:
            return

        new_dais = list()
        prev_dai = self.dais[0]
        for dai in self.dais[1:]:
            if prev_dai == dai:
                dai.merge_unnorm_values(prev_dai)
            else:
                new_dais.append(prev_dai)
            prev_dai = dai
        else:
            new_dais.append(dai)
        self.dais = new_dais
        return self


class SLUHypothesis(object):
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
        return "%.3f %s" % (self.prob, self.da)

    def get_best_da(self):
        return self.da


class DialogueActNBList(SLUHypothesis):
    """Provides functionality of N-best lists for dialogue acts.

    When updating the N-best list, one should do the following.

    1. add utterances or parse a confusion network
    2. merge and normalise, in either order

    Do NOT add the 'other()' DA more than once, else the `normalise' method
    will raise an exception.

    """

    def __init__(self):
        self.n_best = []

    def __str__(self):
        return '\n'.join('{p:.3f} {da}'.format(p=p, da=da)
                         for p, da in self.n_best)

    def __len__(self):
        return len(self.n_best)

    def __getitem__(self, i):
        return self.n_best[i]

    def __iter__(self):
        for hyp in self.n_best:
            yield hyp

    def __cmp__(self, other):
        return (self.n_best >= other.n_best) - (other.n_best >= self.n_best)

    def get_best_da(self):
        """Returns the most probable dialogue act."""
        return self.n_best[0][1]

    def add(self, probability, da):
        """Finds the last hypothesis with a lower probability and inserts the
        new item before that one.

        """
        insert_idx = len(self.n_best)
        while insert_idx > 0:
            insert_idx -= 1
            if probability <= self.n_best[insert_idx][0]:
                insert_idx += 1
                break
        self.n_best.insert(insert_idx, [probability, da])

    def merge(self):
        """Adds up probabilities for the same hypotheses."""
        if len(self.n_best) <= 1:
            return
        else:
            new_n_best = [self.n_best[0]]

            for cur_idx in xrange(1, len(self.n_best)):
                for new_idx in xrange(len(new_n_best)):
                    if new_n_best[new_idx][1] == self.n_best[cur_idx][1]:
                        # Merge, add the probabilities.
                        new_n_best[new_idx][0] += self.n_best[cur_idx][0]
                        break
                else:
                    new_n_best.append(self.n_best[cur_idx])

        self.n_best = sorted(new_n_best, reverse=True)
        return self

    def scale(self):
        """The N-best list will be scaled to sum to one."""
        tot = float(sum(p for p, da in self.n_best))
        for hyp_idx in xrange(len(self.n_best)):
            # Null act is already there (we assume), therefore just normalise.
            self.n_best[hyp_idx][0] /= tot
        return self

    # FIXME: This method name, especially next to the `scale' method, is quite
    # confusing.  Rename them.
    def normalise(self):
        """The N-best list is extended to include the "other()" dialogue act to
        represent those semantic hypotheses which are not included in the
        N-best list.

        """
        tot = 0.0
        other_da_idx = -1
        for hyp_idx in range(len(self.n_best)):
            tot += self.n_best[hyp_idx][0]

            if self.n_best[hyp_idx][1] == 'other()':
                if other_da_idx != -1:
                    raise DialogueActNBListException(
                        'Dialogue act list includes multiple null() ' + \
                        'dialogue acts: {nb!s}'.format(nb=self.n_best))
                other_da_idx = hyp_idx

        # If the 'other()' dialogue act is absent,
        if other_da_idx == -1:
            if tot > 1.0:
                raise DialogueActNBListException(
                    'Sum of probabilities in dialogue act list > 1.0: ' + \
                    '{s:8.6f}'.format(s=tot))
            # Append the 'other()' DA.
            prob_other = 1.0 - tot
            self.n_best.append([prob_other, DialogueAct('other()')])
        # If the 'other()' dialogue act was present,
        else:
            # Just normalise the probs.
            for hyp_idx in range(len(self.n_best)):
                self.n_best[hyp_idx][0] /= tot

        return self

    # XXX It is now a class invariant that the n-best list is sorted.
    def sort(self):
        return self
        # self.n_best.sort(reverse=True)

    def has_dat(self, dat):
        return any(map(lambda hyp: hyp[1].has_dat(dat), self.n_best))


class DialogueActConfusionNetwork(SLUHypothesis):
    """Dialogue act item confusion network. This is a very simple
    implementation in which all dialogue act items are assumed to be
    independent. Therefore, the network stores only posteriors for dialogue act
    items.

    This can be efficiently stored as a list of DAIs each associated with its
    probability. The alternative for each DAI is that there is no such DAI in
    the DA. This can be represented as the null() dialogue act and its
    probability is 1 - p(DAI).

    If there are more than one null() DA in the output DA, then they are
    collapsed into one null() DA since it means the same.

    Please note that in the confusion network, the null() dialogue acts are not
    explicitly modelled.

    """
    def __init__(self):
        self.cn = []

    def __str__(self):

        s = []
        for prob, dai in self.cn:
            s.append("{prob:.3f} {dai!s}".format(prob=prob, dai=dai))

        return "\n".join(s)

    def __len__(self):
        return len(self.cn)

    def __getitem__(self, i):
        return self.cn[i]

    def __iter__(self):
        for i in self.cn:
            yield i

    def add(self, probability, dai):
        """Append additional dialogue act item into the confusion network."""
        self.cn.append([probability, dai])

    def add_merge(self, probability, dai):
        """Add the probability mass of the passed dialogue act item to an
        existing dialogue act item or adds a new dialogue act item.

        """

        for i in range(len(self.cn)):
            if dai == self.cn[i][1]:
                # I found a matching DAI
                self.cn[i][0] += probability
                return
        # if not found you should add it
        self.add(probability, dai)

    def get_best_da(self):
        """Return the best dialogue act (one with the highest probability)."""
        da = DialogueAct()
        for prob, dai in self.cn:
            if prob > 0.5:
                da.append(dai)

        if len(da) == 0:
            da.append(DialogueActItem('null'))

        return da

    def get_best_nonnull_da(self):
        """Return the best dialogue act (with the highest probability)."""

        res = self.get_best_da()

        if res[0].dat == "null":
            da = DialogueAct()
            for prob, dai in self.cn:
                if dai.name is not None and len(dai.name) > 0:
                    da.append(dai)
                    break

            if len(da) == 0:
                da.append(DialogueActItem('null'))

            res = da

        return res

    def get_best_da_hyp(self, use_log=False, threshold=.5):
        """Return the best dialogue act hypothesis.

        Arguments:
            use_log: whether to express probabilities on the log-scale
                     (otherwise, they vanish easily in a moderately long
                     confnet)
            threshold: threshold on probabilities -- items with probability
                       exceeding the threshold will be present in the output
                       (default: 0.5)

        """
        da = DialogueAct()
        if use_log:
            from math import log
            logprob = 0.
        else:
            prob = 1.0
        for edge_p, dai in self.cn:
            if edge_p > threshold:
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

    def get_prob(self, hyp_index):
        """Return a probability of the given hypothesis."""

        prob = 1.0
        for i, (p, dai) in zip(hyp_index, self.cn):
            if i == 0:
                prob *= p
            else:
                prob *= (1 - p)

        return prob

    def get_next_worse_candidates(self, hyp_index):
        """Returns such hypotheses that will have lower probability. It assumes
        that the confusion network is sorted.

        """
        worse_hyp = []

        for i in range(len(hyp_index)):
            wh = list(hyp_index)
            wh[i] += 1
            if wh[i] >= 2:
                # this generate inadmissible word hypothesis
                # because there are only two alternatives - the DAI and the
                # null() dialogue act
                continue

            worse_hyp.append(tuple(wh))

        return worse_hyp

    def get_hyp_index_dialogue_act(self, hyp_index):
        da = DialogueAct()
        for i, (p, dai) in zip(hyp_index, self.cn):
            if i == 0:
                da.append(dai)

        if len(da) == 0:
            da.append(DialogueActItem('null'))

        return da

    def get_da_nblist_naive(self, n=10, expand_upto_total_prob_mass=0.9):
        """For each CN item creates a NB list item."""

        res = []
        for cn_item in self.cn:
            nda = DialogueAct()
            print type(cn_item)
            print cn_item
            nda.append(cn_item[1])

            res += [(cn_item[0], nda)]

        res.sort(reverse=True)
        return res

    def get_da_nblist(self, n=10, expand_upto_total_prob_mass=0.9):
        """Parses the input dialogue act item confusion network and generates
        N-best hypotheses.

        The result is a list of dialogue act hypotheses each with a with
        assigned probability.  The list also include a dialogue act for not
        having the correct dialogue act in the list - other().

        FIXME: I should stop the expansion when expand_upto_total_prob_mass is
        reached.

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

                for hyp_index in \
                        self.get_next_worse_candidates(current_hyp_index):
                    prob = self.get_prob(hyp_index)
                    open_hyp.append((prob, hyp_index))

                open_hyp.sort(reverse=True)

        nblist = DialogueActNBList()
        for idx in closed_hyp:
            nblist.add(closed_hyp[idx], self.get_hyp_index_dialogue_act(idx))

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

        This method has actually nothing to do. The alternatives for each
        dialog act item (DAI) are just two: it is there, or it isn't. The data
        model captures only the presence of DAI-s, and hence no other
        hypothesis' probabilities need to be added.

        """
        pass

    def prune(self, prune_prob=0.001):
        """Prune all low probability dialogue act items."""
        pruned_cn = []
        for prob, dai in self.cn:
            if prob < prune_prob:
                # prune out
                continue

            pruned_cn.append([prob, dai])

        self.cn = pruned_cn

    def normalise(self):
        """Makes sure that all probabilities add up to one. They should
        implicitly sum to one: p + (1-p) == 1.0

        """

        for p,  dai in self.cn:
            if p >= 1.0:
                raise DialogueActConfusionNetworkException(
                    ("The probability of the {dai!s} dialogue act item is " + \
                     "larger than 1.0, namely {p:0.3f}").format(dai=dai, p=p))

    def sort(self):
        self.cn.sort(reverse=True)


def merge_slu_nblists(multiple_nblists):
    """Merge multiple dialogue act N-best lists."""

    merged_nblists = DialogueActNBList()

    for prob_nblist, nblist in multiple_nblists:
        if not isinstance(nblist, DialogueActNBList):
            raise SLUException(
                "Cannot merge something that is not DialogueActNBList.")
        nblist.merge()
        nblist.normalise()

        for prob, da in nblist:
            merged_nblists.add(prob_nblist * prob, da)

    merged_nblists.merge()
    merged_nblists.normalise()
    merged_nblists.sort()

    return merged_nblists


def merge_slu_confnets(multiple_confnets):
    """Merge multiple dialogue act confusion networks."""

    merged_confnets = DialogueActConfusionNetwork()

    for prob_confnet, confnet in multiple_confnets:
        if not isinstance(confnet, DialogueActConfusionNetwork):
            raise SLUException("Cannot merge something that is not " + \
                               "DialogueActConfusionNetwork.")

        for prob, dai in confnet.cn:
            # it is not clear why I wanted to remove all other() dialogue acts
            # if dai.dat == "other":
            #     continue

            merged_confnets.add_merge(prob_confnet * prob, dai)

    merged_confnets.sort()

    return merged_confnets
