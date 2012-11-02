#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import defaultdict

from SDS.utils.string import split_by
from SDS.utils.exception import DialogueActItemException
from SDS.utils.exception import DialogueActNBListException
from SDS.utils.exception import DialogueActException


def load_das(file_name, limit=None):
    f = open(file_name)

    semantics = defaultdict(list)
    c = 0
    for l in f:
        c += 1
        if limit and c > limit:
            break

        l = l.strip()
        if not l:
            continue

        l = l.split("=>")

        key = l[0].strip()
        sem = l[1].strip()

        semantics[key] = DialogueAct(sem)
    f.close()

    return semantics


def save_das(file_name, das):
    f = open(file_name, 'w+')

    for u in sorted(das):
        f.write(u)
        f.write(" => ")
        f.write(str(das[u]) + '\n')

    f.close()


class DialogueActItem:
    """Represents dialogue act item which is a component of a dialogue act. Each dialogue act item is composed of

    1) dialogue act type - e.g. inform, confirm, request, select, hello, ...
    2) slot and value pair - e.g. area, pricerange, food and respectively centre, cheap, Italian


    """
    def __init__(self, dialogue_act_type=None, name=None, value=None):
        """Initialise the dialogue act item. Assigns the default values to dialogue act type (dat), slot name (name),
        and slot value (value).

        """

        self.dat = dialogue_act_type
        self.name = name
        self.value = value

    def __str__(self):
        r = self.dat + '('

        if self.name:
            r += self.name

        if self.value:
            r += '="' + self.value + '"'

        r += ')'
        return r

    def __eq__(self, dai):
        if dai.dat:
            if dai.dat != self.dat:
                return False

        if dai.name:
            if dai.name != self.name:
                return False

        if dai.value:
            if dai.value != self.value:
                return False

        return True

    def parse(self, dai):
        """Parse the dialogue act item in text format into a structured form.
        """
        try:
            i = dai.index('(')
        except ValueError:
            raise DialogueActItemException(
                "Parsing error in: %s. Missing opening parenthesis." % dai)

        self.dat = dai[:i]

        # remove the parentheses
        dai_sv = dai[i + 1:len(dai) - 1]
        if not dai_sv:
            # there is no slot name or value
            return

        r = split_by(dai_sv, '=', '', '', '"')
        if len(r) == 1:
            # there is only slot name
            self.name = r[0]
        elif len(r) == 2:
            # there is slot name and value
            self.name = r[0]
            self.value = r[1][1:-1]
        else:
            raise DialogueActItemException(
                "Parsing error in: %s: %s" % (dai, str(r)))


class DialogueAct:
    def __init__(self, da=None):
        self.dais = []

        if da:
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
            l = [str(dai) for dai in self.dais]
            return dai in l

    def __lt__(self, other):
        return self.dais < other.dais

    def __le__(self, other):
        return self.dais <= other.dais

    def __eq__(self, other):
        if isinstance(other, DialogueAct):
            return self.dais == other.dais
        elif isinstance(other, str):
            o = DialogueAct(other)
            return self.dais == o.dais
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
        """Checks whether any of the dialogue act items has a specific dialogue act type."""

        for dai in self.dais:
            if dat == dai.dat:
                return True

        return False

    def has_only_dat(self, dat):
        """Checks whether all the dialogue act items has a specific dialogue act type."""

        for dai in self.dais:
            if dat != dai.dat:
                return False

        return True

    def parse(self, da):
        """Parse the dialogue act in text format into the structured form.
        """
        dais = sorted(split_by(da, '&', '(', ')', '"'))

        for dai in dais:
            dai_parsed = DialogueActItem()
            dai_parsed.parse(dai)
            self.dais.append(dai_parsed)

    def append(self, dai):
        """Append a dialogue act item to the current dialogue act."""
        if isinstance(dai, DialogueActItem):
            self.dais.append(dai)
        else:
            raise DialogueActException(
                "Only DialogueActItems can be appended.")


class DialogueActNBList:
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

    def parse_dai_confusion_network(self, dai_cn, n=10, expand_upto_total_prob_mass=0.9):
        """Parses the input dialogue act item confusion network and generates N-best hypotheses.

        The result is a list of dialogue act hypotheses each with a with assigned probability.
        The list also include a dialogue act for not having the correct dialogue act in the list, e.g. null()
        """
        self.n_best = []

        #FIXME: expand the DAI confusion network

        self.merge()
        self.normalise()
        self.sort()

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
                        new_n_best[j][1][0] += self.n_best[i][0]
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
        """The N-best list is extended to include a "null()" dialogue act to represent that semantic hypotheses
        which are not included in the N-best list.
        """
        sum = 0.0
        null_da = -1
        for i in range(len(self.n_best)):
            sum += self.n_best[i][0]

            if self.n_best[i][1] == 'null()':
                if null_da != -1:
                    raise DialogueActNBListException('Dialogue act list include multiple null() dialogue acts: %s' % str(self.n_best))
                null_da = i

        if null_da == -1:
            if sum > 1.0:
                raise DialogueActNBListException('Sum of probabilities in dialogue act list > 1.0: %8.6f' % sum)
            prob_null = 1.0 - sum
            self.n_best.append([prob_null, DialogueAct('null()')])

        else:
            for i in range(len(self.n_best)):
                # null act is already there, therefore just normalise
                self.n_best[i][0] /= sum

    def sort(self):
        self.n_best.sort(reverse=True)


class DialogueActConfusionNetwork:
    def __init__(self):
        pass

    def normalise(self):
        pass
