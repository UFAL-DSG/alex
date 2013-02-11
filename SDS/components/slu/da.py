#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008/.

from collections import defaultdict

from SDS.utils.text import split_by
from SDS.utils.exception import SLUException, DialogueActException, \
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

        1) dialogue act type - e.g. inform, confirm, request, select, hello,
           ...
        2) slot and value pair - e.g. area, pricerange, food and
           respectively centre, cheap, Italian

    """
    def __init__(self, dialogue_act_type=None, name=None, value=None,
                 dai=None):
        """Initialise the dialogue act item. Assigns the default values to
        dialogue act type (dat), slot name (name), and slot value (value).

        """

        self.dat = dialogue_act_type
        self.name = name
        self.value = value

        if dai:
            self.parse(dai)

    def __str__(self):
        r = self.dat + '('

        if self.name:
            r += self.name

        if self.value:
            r += '="' + self.value + '"'

        r += ')'
        return r

    def __eq__(self, other):
        if other.dat:
            if other.dat != self.dat:
                return False

        if other.name:
            if other.name != self.name:
                return False

        if other.value:
            if other.value != self.value:
                return False

        return True

    def __lt__(self, other):
        return str(self) < str(other)

    def parse(self, dai):
        """Parse the dialogue act item in text format into a structured form.
        """
        dai = dai.strip()

        try:
            first_par_idx = dai.index('(')
        except ValueError:
            raise DialogueActItemException(
                "Parsing error in: %s. Missing opening parenthesis." % dai)

        self.dat = dai[:first_par_idx]

        # Remove the parentheses.
        dai_sv = dai[first_par_idx + 1:len(dai) - 1]
        if len(dai_sv) == 0:
            # There is no slot name or value.
            return self

        attr_val = split_by(dai_sv, splitter='=', quotes='"')
        if len(attr_val) == 1:
            # There is only a slot name.
            self.name = attr_val[0]
        elif len(attr_val) == 2:
            # There is a slot name and a value.
            self.name = attr_val[0]
            self.value = attr_val[1]
            if self.value[0] in ["'", '"']:
                self.value = self.value[1:-1]
        else:
            raise DialogueActItemException(
                "Parsing error in: {dai}: {atval}".format(
                    dai=dai, atval=attr_val))

        return self


class DialogueAct(object):
    def __init__(self, da=None):
        self.dais = []

        if da is not None:
            self.parse(da)

    def __str__(self):
        dais = []

        for dai in self.dais:
            dais.append(str(dai))

        return '&'.join(dais)

    def __contains__(self, dai):
        if isinstance(dai, DialogueActItem):
            return dai in self.dais
        elif isinstance(dai, str):
            l = [str(d) for d in self.dais]
            return dai in l

    def __lt__(self, other):
        return self.dais < other.dais

    def __le__(self, other):
        return self.dais <= other.dais

    def __eq__(self, other):
        if isinstance(other, DialogueAct):
            return self.dais == other.dais
        elif isinstance(other, str):
            return str(self) == other
        else:
            DialogueActException("Unsupported comparison type.")

    def __ne__(self, other):
        return self.dais != other.dais

    def __gt__(self, other):
        return self.dais > other.dais

    def __ge__(self, other):
        return self.dais >= other.dais

    def __len__(self):
        return len(self.dais)

    def __getitem__(self, i):
        return self.dais[i]

    def __iter__(self):
        for i in self.dais:
            yield i

    def has_dat(self, dat):
        """Checks whether any of the dialogue act items has a specific dialogue
        act type.

        """

        for dai in self.dais:
            if dat == dai.dat:
                return True

        return False

    def has_only_dat(self, dat):
        """Checks whether all the dialogue act items has a specific dialogue
        act type.

        """

        for dai in self.dais:
            if dat != dai.dat:
                return False

        return True

    def parse(self, da):
        """Parse the dialogue act in text format into the structured form."""
        dais = sorted(split_by(da, splitter='&', opening_parentheses='(',
                               closing_parentheses=')', quotes='"'))

        self.dais.extend(DialogueActItem(dai=dai) for dai in dais)

    def append(self, dai):
        """Append a dialogue act item to the current dialogue act."""
        if isinstance(dai, DialogueActItem):
            self.dais.append(dai)
        else:
            raise DialogueActException(
                "Only DialogueActItems can be appended.")

    def get_slots_and_values(self):
        """Returns all values and corresponding slot names in the dialogue
        act.

        """
        sv = []
        for dai in self.dais:
            if dai.value:
                sv.append([dai.name, dai.value])

        return sv

    def sort(self):
       # print "S1", self
        self.dais.sort()
       # print "S2", self

    def merge(self, da):
        for dai in da:
            self.append(dai)


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
    2. merge
    3. normalise
    4. sort

    """

    def __init__(self):
        self.n_best = []

    def __str__(self):
        s = []
        for h in self.n_best:
            s.append("%.3f %s" % (h[0], h[1]))

        return '\n'.join(s)

    def __len__(self):
        return len(self.n_best)

    def __getitem__(self, i):
        return self.n_best[i]

    def __iter__(self):
        for i in self.n_best:
            yield i

    def get_best_da(self):
        """Returns the most probable dialogue act."""
        return self.n_best[0][1]

    def add(self, probability, da):
        self.n_best.append([probability, da])

    def merge(self):
        """Adds up probabilities for the same hypotheses.
        """
        new_n_best = []

        if len(self.n_best) <= 1:
            return
        else:
            new_n_best.append(self.n_best[0])

            for i in range(1, len(self.n_best)):
                for j in range(len(new_n_best)):
                    if new_n_best[j][1] == self.n_best[i][1]:
                        # merge, add the probabilities
                        new_n_best[j][0] += self.n_best[i][0]
                        break
                else:
                    new_n_best.append(self.n_best[i])

        self.n_best = new_n_best

    def scale(self):
        """The N-best list will be scaled to sum to one."""

        s = sum([p for p, da in self.n_best])

        for i in range(len(self.n_best)):
            # null act is already there, therefore just normalise
            self.n_best[i][0] /= s

    def normalise(self):
        """The N-best list is extended to include a "other()" dialogue act to
        represent that semantic hypotheses which are not included in the N-best
        list.

        """
        sum = 0.0
        other_da = -1
        for i in range(len(self.n_best)):
            sum += self.n_best[i][0]

            if self.n_best[i][1] == 'other()':
                if other_da != -1:
                    raise DialogueActNBListException(
                        'Dialogue act list include multiple null() ' + \
                        'dialogue acts: {nb!s}'.format(nb=self.n_best))
                other_da = i

        if other_da == -1:
            if sum > 1.0:
                raise DialogueActNBListException(
                    'Sum of probabilities in dialogue act list > 1.0: ' + \
                    '{s:8.6f}'.format(s=sum))
            prob_other = 1.0 - sum
            self.n_best.append([prob_other, DialogueAct('other()')])

        else:
            for i in range(len(self.n_best)):
                # null act is already there, therefore just normalise
                self.n_best[i][0] /= sum

    def sort(self):
        self.n_best.sort(reverse=True)

    def has_dat(self, dat):
        for prob, da in self:
            if da.has_dat(dat):
                return True
        return False


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
        """Return the best dialogue act (with the highest probability)."""
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

    def get_best_da_hyp(self):
        """Return the best dialogue act hypothesis."""
        da = DialogueAct()
        prob = 1.0
        for p, dai in self.cn:
            if p > 0.5:
                da.append(dai)
                # multiply with probability of presence of a dialogue act
                prob *= p
            else:
                # multiply with probability of exclusion of the dialogue act
                prob *= (1 - p)

        if len(da) == 0:
            da.append(DialogueActItem('null'))

        return DialogueActHyp(prob, da)

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
