#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is mostly PEP8-compliant. See
# http://www.python.org/dev/peps/pep-0008.

from collections import defaultdict
import cPickle as pickle
from math import isnan
import numpy as np
import random

from sklearn import tree
from sklearn.linear_model import LogisticRegression

from alex.components.asr.utterance import UtteranceFeatures, \
    UtteranceNBListFeatures, UtteranceHyp
from alex.components.slu import SLUInterface
from alex.components.slu.da import DialogueActItem, \
    DialogueActConfusionNetwork, DialogueActFeatures, merge_slu_confnets
from alex.ml.features import Features
from alex.utils.exception import DAILRException, SLUException


class DAILogRegClassifier(SLUInterface):
    """Implements learning of and decoding with dialogue act item classifiers
    based on logistic regression.

    When used for parsing an utterance, each classifier decides whether its
    respective dialogue act item is present.  Then, the output dialogue act is
    constructed by joining all detected dialogue act items.

    Dialogue act is defined as a composition of dialogue act items. E.g.

    confirm(drinks="wine")&inform(name="kings shilling")
        <=> 'does kings serve wine'

    where confirm(drinks="wine") and inform(name="kings shilling") are two
    dialogue act items.

    This parser uses logistic regression as the classifier of the dialogue
    act items.


    Attributes:
        category_labels: mapping { utterance ID:
                                    { category label: original string } }
        cls_threshold: threshold for classifying as positive
        clser_type: a string indicating type of the classifier used
                    currently supported choices: 'logistic', 'tree'
        dai_counts: mapping { DAI: number of occurrences in data }
        das: mapping { utterance ID: DA } for DAs corresponding to training
             utterances
        feat_counts: mapping { feature: number of occurrences }
        feature_idxs: mapping { feature: feature index }; feature indices span
                      range(0, number_of_features)
        features_size: size (order) of features, i.e., length of the n-grams
        features_type: type of features
        input_matrix: observation matrix, a numpy array with rows corresponding
                      to utterances and columns corresponding to features
                      This is a read-only attribute.
        output_matrix: mapping { DAI: [ utterance index:
                                        ?DAI present in utterance ] }
                       where the list is a numpy array, and the values are
                       either 0.0 or 1.0
                       This is a read-only attribute.
        preprocessing: an SLUPreprocessing object to be used for preprocessing
                       of utterances and DAs
        trained_classifiers: mapping { DAI: classifier for this DAI }
        utt_ids: IDs of training utterances / utterance hypotheses (n-best
                 lists)
        utterance_features: mapping { utterance ID: utterance features } where
                            the features is an UtteranceFeatures object
        utterances: mapping { utterance ID: utterance } for training utterances

    Type of features:
        By default, 'ngram' is used, meaning n-grams up to order 4 plus all
        skip n-grams of maximally that order are extracted.

        Value of the argument specifying the type of features is tested for
        inclusion of specific feature types.  If it contains (may it be as
        a substring, or a member of a tuple, for example) any of the following
        keywords, the corresponding type of features is extracted.

            'ngram': n-grams (as described above)
            'prev_da': features of the DA preceding to the one to be classified

    """
    # TODO Document attributes from the original DAILogRegClassifier class
    # (from the load_model method on).

    # TODO Document.
    def __init__(self,
                 preprocessing=None,
                 clser_type='logistic',
                 features_type='ngram',
                 features_size=4):
        # FIXME: maybe the SLU components should use the Config class to
        # initialise themselves.  As a result it would create their category
        # label database and pre-processing classes.
        random.seed()

        # Save the arguments.
        self.preprocessing = preprocessing
        self.clser_type = clser_type
        self.features_type = features_type
        self.features_size = features_size

        # Additional bookkeeping.
        # Setting protected fields to None is interpreted as that they have to
        # be computed yet.
        self.cls_threshold = 0.5
        self._dai_counts = None
        self._input_matrix = None
        self._output_matrix = None
        self._default_min_feat_count = 1

    def _get_feature_extractor(self,
                               prev_das=None,
                               utt_nblists=None,
                               by_utt_id=False):
        ft = self.features_type
        fs = self.features_size

        def extract_feats(utterance=None, prev_da=None, utt_nblist=None):
            # Collect all types of features.
            feat_sets = list()
            if 'ngram' in ft:
                feat_sets.append(UtteranceFeatures('ngram', fs, utterance))
            if 'prev_da' in ft and prev_da is not None:
                feat_sets.append(DialogueActFeatures(prev_da))
            if 'utt_nbl' in ft and utt_nblist is not None:
                feat_sets.append(
                    UtteranceNBListFeatures(size=fs, utt_nblist=utt_nblist))

            # Based on the number of distinct feature types, either join them
            # or take the single feature type.
            if len(feat_sets) > 1:
                feats = Features.join(*feat_sets)
            elif len(feat_sets) == 1:
                feats = feat_sets[0]
            else:
                # XXX This exception can actually be raised even if we know how
                # to handle that type of features ('prev_da') but don't have
                # the argument specifying the necessary input (prev_das).
                raise DAILRException(
                    'Cannot handle this type of features: "{ft}".'
                    .format(ft=ft))
            return feats

        if by_utt_id:
            return (lambda utt_id:
                    extract_feats(utterance=(self.utterances[utt_id]
                                             if self.utterances is not None
                                             else None),
                                  prev_da=(prev_das[utt_id]
                                           if prev_das is not None
                                           else None),
                                  utt_nblist=(utt_nblists[utt_id]
                                              if utt_nblists is not None
                                              else None)))
        else:
            return extract_feats

    # FIXME: Move the `das' argument to the first place (after self) and make
    # it obligatory also formally.  This will require refactoring code that
    # uses this class, calling this method with positional arguments.
    def extract_features(self, utterances=None, das=None, prev_das=None,
                         utt_nblists=None, verbose=False):
        """Extracts features from given utterances, making use of their
        corresponding DAs.  This is a pre-requisite to pruning features,
        classifiers, and running training with this learner.

        Arguments:
            utterances: mapping { utterance ID: utterance }, the utterance
                 being an instance of the Utterance class (default: None)
            das: mapping { utterance ID: DA }, the DA being an instance of the
                 DialogueAct class
                 NOTE this argument has a default value, yet it is obligatory.
            prev_das: mapping { utterance ID: DA }, the DA, an instance of
                 the DialogueAct class, describing the DA immediately preceding
                 to the one in question (default: None)
            utt_nblists: mapping { utterance ID: utterance n-best list }, with
                 the utterance n-best list reflecting the ASR output
                 (default: None)
            verbose: print debugging output?  More output is printed if
                 verbose > 1.

        The dictionary arguments are expected to all have the same set of keys.

        """
        self.utterances = utterances
        self.utt_nblists = utt_nblists
        self.das = das
        if utterances:
            self.utt_ids = utterances.keys()
        elif utt_nblists:
            self.utt_ids = utt_nblists.keys()
        else:
            raise DAILRException('Cannot learn a classifier without '
                                 'utterances and without ASR hypotheses.')

        # Normalise the text and substitute category labels.
        self.category_labels = {}
        if self.preprocessing:
            # Learning from transcriptions...
            if utterances:
                for utt_id in self.utt_ids:
                    # Normalise the text.
                    self.utterances[utt_id] = self.preprocessing\
                        .text_normalisation(self.utterances[utt_id])
                    # Substitute category labes.
                    (self.utterances[utt_id],
                     self.das[utt_id],
                     self.category_labels[utt_id]) = \
                        self.preprocessing.values2category_labels_in_da(
                            self.utterances[utt_id], self.das[utt_id])
            # ...or, learning from utterance hypotheses.
            else:
                assert bool(utt_nblists)
                for utt_id in self.utt_nblists.iterkeys():
                    nblist = self.utt_nblists[utt_id]
                    if nblist is None:
                        # FIXME This should rather be discarded right away.
                        continue
                    # Normalise the text.
                    for utt_idx, hyp in enumerate(nblist):
                        utt = hyp[1]
                        nblist[utt_idx][1] = (self.preprocessing
                                              .text_normalisation(utt))
                    # Substitute category labes.
                    (self.utt_nblists[utt_id],
                     self.das[utt_id],
                     self.category_labels[utt_id]) = \
                        self.preprocessing.values2category_labels_in_da(
                            nblist, self.das[utt_id])

        # Generate utterance features.
        extract_feats = self._get_feature_extractor(by_utt_id=True,
                                                    prev_das=prev_das,
                                                    utt_nblists=utt_nblists)
        self.utterance_features = {utt_id: extract_feats(utt_id)
                                   for utt_id in self.utt_ids}
        if verbose >= 2:
            print "Random few extracted features:"
            for utt_id in self.utt_ids[:41]:
                print str(self.utterance_features[utt_id])
            print

    def prune_features(self, min_feature_count=None, verbose=False):
        """Prunes features that occur few times.

        Arguments:
            min_feature_count: minimum number of a feature occurring for it not
                               to be pruned (default: 5)
            verbose:           whether to print diagnostic messages to stdout;
                               when set to a larger value (i.e., 2), causes
                               even higher verbosity
                               (default: False)

        """
        # Remember the threshold used, and use it as a default later.
        if min_feature_count is None:
            min_feature_count = 5
        else:
            self._default_min_feat_count = min_feature_count
        # Count number of occurrences of features.
        self.feat_counts = dict()
        for utt_id in self.utt_ids:
            for feature in self.utterance_features[utt_id]:
                self.feat_counts[feature] = \
                    self.feat_counts.get(feature, 0) + 1

        if verbose:
            print "Number of features: ", len(self.feat_counts)

        # Collect those with too few occurrences.
        low_count_features = set(filter(
            lambda feature: self.feat_counts[feature] < min_feature_count,
            self.feat_counts.iterkeys()))

        # Discard the low-count features.
        for utt_id in self.utt_ids:
            self.utterance_features[utt_id].prune(low_count_features)
        old_feat_counts = self.feat_counts
        self.feat_counts = {key: old_feat_counts[key]
                            for key in old_feat_counts
                            if key not in low_count_features}

        if verbose:
            print ("Number of features occurring less than {occs} times: {cnt}"
                   .format(occs=min_feature_count,
                           cnt=len(low_count_features)))

        # Build the mapping from features to their indices.
        self.feature_idxs = {}
        for idx, feature in enumerate(self.feat_counts.iterkeys()):
            self.feature_idxs[feature] = idx

        if verbose:
            print "Number of features after pruning: ", len(self.feat_counts)
            if verbose > 1:
                print "The features:"
                print "---features---"
                import pprint
                pprint.pprint([str(feat) for feat in self.feature_idxs])
                print "---features---"

    @property
    def dai_counts(self):
        """a mapping { DAI : number of occurrences in training DAs }"""
        # If `_dai_counts' have not been evaluated yet,
        if self._dai_counts is None:
            # Count occurrences of all DAIs in the DAs bound to this learner.
            _dai_counts = self._dai_counts = dict()
            for utt_id in self.utt_ids:
                for dai in self.das[utt_id].dais:
                    _dai_counts[dai] = _dai_counts.get(dai, 0) + 1
        return self._dai_counts

    def print_dais(self):
        """Prints what `extract_classifiers(verbose=True)' would output in
        earlier versions.

        """
        for utt_id in self.utt_ids:
            for dai in self.das[utt_id].dais:
                # XXX What again does ('-' not in dai.value) check? Presence of
                # a category label? This seems to be the case yet it is very
                # cryptic.
                if dai.value and '-' not in dai.value:
                    print '#' * 60
                    print self.das[utt_id]
                    print self.utterances[utt_id]
                    print self.category_labels[utt_id]

    def prune_classifiers(self, min_dai_count=5, accept_dai=None):
        """Prunes classifiers for DAIs that cannot be reliably classified with
        these training data.

        Arguments:
            min_dai_count: minimum number of occurrences of a DAI for it
                to have its own classifier (this affects only non-atomic DAIs
                without abstracted category labels)
            accept_dai: custom fuction that takes a string representation of
                a DAI and returns True if that DAI should have its classifier,
                else False;

                The function gets called with the following tuple
                of arguments: (self, dai), where `self' is this
                DAILogRegClassifierLearning object, and `dai' the DAI in
                question

        """
        # Define pruning criteria.
        if accept_dai is not None:
            _accept_dai = lambda dai: accept_dai(self, dai)
        else:
            def _accept_dai(dai):
                # Discard a DAI that is reasonably complex and yet has too few
                # occurrences.
                if (dai.name is not None
                        and dai.value is not None
                        and not dai.has_category_label()
                        and self._dai_counts[dai] < min_dai_count):
                    return False
                # Discard a DAI in the form '(slotname="dontcare")'.
                if dai.name is not None and dai.value == "dontcare":
                    return False
                # Discard a 'null()'. This classifier can be ignored since the
                # null dialogue act is a complement to all other dialogue acts.
                return not dai.is_null()

        # Do the pruning.
        old_dai_counts = self.dai_counts  # NOTE the side effect from the
                                          # getter
        self._dai_counts = {dai: old_dai_counts[dai]
                            for dai in old_dai_counts
                            if _accept_dai(dai)}

    def print_classifiers(self):
        print "Classifiers detected in the training data"
        print "-" * 60
        print "Number of classifiers: ", len(self.dai_counts)
        print "-" * 60

        for dai in sorted(self.dai_counts.iterkeys()):
            print '{dai:>40} = {cnt}'.format(dai=dai,
                                             cnt=self._dai_counts[dai])
        print "-" * 60
        print

    @property
    def output_matrix(self):
        """the output matrix of DAIs for training utterances

        Note that the output matrix has unusual indexing: first associative
        index to columns, then integral index to rows.

        Beware, this getter will fail if `extract_features' was not called
        before.

        """
        if self._output_matrix is None:
            self.gen_output_matrix()
        return self._output_matrix

    def gen_output_matrix(self):
        """Generates the output matrix from training data.

        Beware, this method will fail if `extract_features' was not called
        before.

        """
        das = self.das
        uts = self.utt_ids
        # NOTE that the output matrix has unusual indexing: first associative
        # index to columns, then integral index to rows.
        self._output_matrix = \
            {dai.extension(): np.array([2 * (dai in das[utt_id]) - 1.
                                        for utt_id in uts])
             for dai in self._dai_counts}

    @property
    def input_matrix(self):
        """the input matrix of features for training utterances

        Beware, this getter will fail if `extract_features' was not called
        before.

        """
        if self._input_matrix is None:
            self.gen_input_matrix()
        return self._input_matrix

    def gen_input_matrix(self):
        """Generates the observation matrix from training data.

        Beware, this method will fail if `extract_features' was not called
        before.

        """
        self._input_matrix = np.zeros((len(self.utt_ids),
                                       len(self.feat_counts)))
        for utt_idx, utt_id in enumerate(self.utt_ids):
            self._input_matrix[utt_idx] = (
                self.utterance_features[utt_id]
                .get_feature_vector(self.feature_idxs))

    @classmethod
    def balance_data(cls, inputs, outputs):
        outputs_idxs = defaultdict(list)
        for output_idx, output in enumerate(outputs):
            outputs_idxs[output].append(output_idx)
        max_count = max(map(len, outputs_idxs.values()))
        new_inputs = list()
        new_outputs = list()
        for output, output_idxs in outputs_idxs.iteritems():
            n_remains = max_count - len(output_idxs)
            new_inputs.extend(inputs[random.choice(output_idxs)]
                              for _ in xrange(n_remains))
            new_outputs.extend([output] * n_remains)
        # (The following check is to avoid ValueError from numpy.concatenate of
        # an empty list.)
        # If any balancing was done,
        if new_outputs:
            # Return a new, balanced set.
            return (np.concatenate((inputs, new_inputs)),
                    np.concatenate((outputs, new_outputs)))
        else:
            # Return the original inputs and outputs.
            return inputs, outputs

    def train(self, sparsification=1.0, min_feature_count=None,
              calibrate=False, verbose=True):
        if min_feature_count is None:
            min_feature_count = self._default_min_feat_count

        # Make sure the input and output matrices have been generated.
        if self._output_matrix is None:
            self.gen_output_matrix()
        if self._input_matrix is None:
            self.gen_input_matrix()

        # Train classifiers for every DAI less those that have been pruned.
        self.trained_classifiers = {}
        if verbose:
            coefs_abs_sum = np.zeros(shape=(1, len(self.feat_counts)))
        for dai in sorted(self._dai_counts):
            # before message
            if verbose:
                print "Training classifier: ", dai

            # (TODO) We might want to skip this based on whether NaNs were
            # considered in the beginning.  That might be specified in an
            # argument to the initialiser.

            # Select from the training data only those with non-NaN values.
            outputs = self._output_matrix[dai]
            valid_row_idxs = set(
                [row_idx for row_idx in xrange(len(self._input_matrix))
                 if not isnan(outputs[row_idx])])
            if len(valid_row_idxs) == len(outputs):
                inputs = self._input_matrix
            else:
                inputs = np.array(
                    [row for row_idx, row in enumerate(self._input_matrix)
                     if row_idx in valid_row_idxs])
                outputs = np.array(
                    [output for row_idx, output in enumerate(outputs)
                     if row_idx in valid_row_idxs])
            if verbose:
                print "Support for training: {sup} (pos: {pos}, neg: {neg})"\
                    .format(sup=len(valid_row_idxs),
                            pos=len(filter(lambda out: out == 1., outputs)),
                            neg=len(filter(lambda out: out == 0., outputs)))

            # Prune features based on the selection of DAIs.
            if len(valid_row_idxs) != len(self._input_matrix):
                inputs = inputs.transpose()
                n_feats_used = len(inputs)
                for feat_idx, feat_vec in enumerate(inputs):
                    n_occs = len(
                        filter(lambda feat_val: not (isnan(feat_val)
                                                     or feat_val == 0),
                               feat_vec))
                    if n_occs < min_feature_count:
                        inputs[feat_idx] *= 0
                        n_feats_used -= 1
                inputs = inputs.transpose()
                if verbose:
                    print ("Adaptively pruned features to {cnt}."
                           .format(cnt=n_feats_used))

            # Train and store the classifier for `dai'.
            if self.clser_type == 'logistic':
                clser = LogisticRegression('l1', C=sparsification, tol=1e-6,
                                           class_weight='auto')
                # clser.fit(inputs, outputs)
                # XXX Balancing the data cannot be canceled by passing an
                # argument now.
                clser.fit(*self.balance_data(inputs, outputs))
            else:
                assert self.clser_type == 'tree'
                # TODO Make the parameters tunable.
                clser = tree.DecisionTreeClassifier(min_samples_split=5,
                                                    max_depth=4)
                clser.fit(*self.balance_data(inputs, outputs))
            self.trained_classifiers[dai] = clser

            # after message
            if verbose:
                if self.clser_type == 'logistic':
                    coefs_abs_sum += map(abs, clser.coef_)
                else:
                    coefs_abs_sum += clser.tree_.node_count
                accuracy = clser.score(inputs, outputs)
                predictions = [clser.predict(obs)[0] for obs in inputs]
                true_pos = sum(predictions[idx] == outputs[idx] == 1
                               for idx in xrange(len(outputs)))
                false_pos = sum(predictions[idx] == 1 and outputs[idx] == 0
                                for idx in xrange(len(outputs)))
                false_neg = sum(predictions[idx] == 0 and outputs[idx] == 1
                                for idx in xrange(len(outputs)))
                if true_pos + false_pos > 0.:
                    precision = true_pos / float(true_pos + false_pos)
                else:
                    precision = 0.
                if true_pos + false_neg > 0.:
                    recall = true_pos / float(true_pos + false_neg)
                else:
                    recall = 0.
                if precision * recall == 0.:
                    f_score = 0.
                else:
                    f_score = 2 * precision * recall / (precision + recall)
                if self.clser_type == 'logistic':
                    n_nonzero = np.count_nonzero(clser.coef_)
                else:
                    n_nonzero = clser.tree_.node_count
                msg = ("Accuracy for training data: {acc:6.2f} %\n"
                       "P/R/F: {p:.3f}/{r:.3f}/{f:.3f}\n"
                       # "Size of the params: {parsize}\n"
                       "Number of non-zero params: {nonzero}").format(
                           acc=(100 * accuracy),
                           p=precision,
                           r=recall,
                           f=f_score,
                           # parsize=clser.coef_.shape,
                           nonzero=n_nonzero)
                print msg
                # TODO Print the non-zero features learned.
                if self.clser_type == 'logistic':
                    nonzero_idxs = clser.coef_.nonzero()[1]
                    # [0] is intercept, perhaps
                    if len(nonzero_idxs):
                        print "Non-zero features:"
                        for feat_idx in nonzero_idxs:
                            print "  {}".format(
                                self.feat_counts.keys()[feat_idx])
                print

        if verbose:
            print "Total number of non-zero params:", \
                  np.count_nonzero(coefs_abs_sum)

        # Calibrate the prior.
        if calibrate:
            if verbose:
                print
                print "Calibrating the prior..."
            self.calibrate_prior(verbose=verbose)

    def calibrate_prior(self, exp_unknown=0.05, verbose=False):
        """Calibrates the prior on classification (its bias).  Requires that
        the model be already trained.

        Arguments:
            exp_unknown: expected answer for DAIs that are not labeled in
                         training data.  This needs to be a float between 0.
                         and 1., expressing how likely it is for such DAIs to
                         be actually correct.
            verbose: Be verbose; if `verbose' > 1, produces a lot of output.
                     For debugging purposes.

        """
        def fscore():
            precision = true_pos / (true_pos + false_pos)
            recall = true_pos / (true_pos + false_neg)
            if precision + recall > 0.:
                return 2 * precision * recall / (precision + recall)
            return 0.
        # Collect a new type of training data: predicted value -> true value.
        # In cases where we don't know the true label of a classification
        # problem (of a DAI in its utterance), we use `exp_unknown' instead of
        # the label.
        # FIXME: Exclude DAIs that are never labeled.
        calib_data = np.empty(
            (len(self.utt_ids) * len(self.trained_classifiers), 2))
        # sanity check
        if not len(calib_data):
            return
        dais_labeled = set()
        datum_idx = 0
        for utt_idx, utt_id in enumerate(self.utt_ids):
            dais_labeled.update(self.das[utt_id].dais)
            # FIXME: The check for the 'correct' attribute is not very
            # thought-out.
            dais_corr = [dai for dai in dais_labeled
                         if not (hasattr(dai, 'correct') and not dai.correct)]
            for dai, clser in self.trained_classifiers.iteritems():
                predicted = clser.predict_proba(
                    self._input_matrix[utt_idx])[0][1]
                if dai in dais_labeled:
                    # Note we cannot use just `dai.correct', as `dai' is
                    # actually a different object than "`dais_corr[dai]'".
                    true = float(dai in dais_corr)
                else:
                    true = exp_unknown
                calib_data[datum_idx] = (predicted, true)
                datum_idx += 1
            dais_labeled.clear()

        # Find the optimal decision boundary.
        # Here we use the absolute error, not squared error.  This should be
        # more efficient and have little impact on the result.
        true_pos = np.sum(calib_data, axis=0)[1]
        false_pos = np.sum(1. - calib_data, axis=0)[1]
        false_neg = 0.
        error = 1. - fscore()
        calib_data = np.array(sorted(calib_data, key=lambda row: row[0]))
        split_idx = 0
        best_error = error
        if verbose:
            print "Total error: {err}".format(err=error)
        datum_idx = 0
        while True:
            if verbose > 1:
                start_idx = datum_idx
            try:
                predicted, true = calib_data[datum_idx]
            except IndexError:
                break
            # Collect all the classifications for the same predicted value.
            point_cnt = 1
            point_cls_sum = true
            while True:
                try:
                    next_is_same = (calib_data[datum_idx + 1][0] == predicted)
                except IndexError:
                    break
                if next_is_same:
                    datum_idx += 1
                    point_cnt += 1
                    point_cls_sum += calib_data[datum_idx][1]
                else:
                    break
            # Compute the difference in total error.
            true_pos -= point_cls_sum
            false_pos -= point_cnt - point_cls_sum
            false_neg += point_cls_sum
            error = 1. - fscore()
            if error < best_error:
                best_error = error
                split_idx = datum_idx
            datum_idx += 1
            if verbose > 1:
                print "Split [{start}, {end}): pred={pred}, err={err}".format(
                    start=start_idx, end=datum_idx, pred=predicted, err=error)

        try:
            self.cls_threshold = .5 * (calib_data[split_idx][0]
                                       + calib_data[split_idx + 1][0])
        except IndexError:
            self.cls_threshold = calib_data[split_idx][0]

        if verbose:
            print
            print "Best error: {err}".format(err=best_error)
            print "Threshold: {thresh}".format(thresh=self.cls_threshold)

    @classmethod
    def resave_model(self, infname, outfname):
        """This helper method serves to convert from the original format of SLU
        models to the current one.

        """
        with open(infname, 'rb') as infile:
            data = pickle.load(infile)
        new_clsers = {DialogueActItem(dai): clser for dai, clser in
                      data[2].iteritems()}

        #import ipdb; ipdb.set_trace()
        with open(outfname, 'wb+') as outfile:
            pickle.dump((data[0], data[1], new_clsers, data[3], data[4]),
                        outfile)

    def save_model(self, file_name):
        version = '2'
        data = (self.feat_counts.keys(),
                self.feature_idxs,
                self.clser_type,
                {dai.extension(): clser for dai, clser in
                 self.trained_classifiers.iteritems()},
                self.features_type,
                self.features_size,
                self.cls_threshold)
        with open(file_name, 'w+') as outfile:
            pickle.dump((version, data), outfile)

    ###############################################################
    ### From here on, the methods come from what used to be the ###
    ### DAILogRegClassifier class.                              ###
    ###############################################################

    def load_model(self, file_name):
        with open(file_name, 'r') as infile:
            data = pickle.load(infile)
            if isinstance(data[0], basestring):
                version = data[0]
                data = data[1]
            else:
                version = '0'

        if version == '0':
            (self.features_list, self.feature_idxs, self.trained_classifiers,
                self.features_type, self.features_size) = data
        elif version == '1':
            (self.features_list, self.feature_idxs,
             self.trained_classifiers, self.features_type,
             self.features_size, self.cls_threshold) = data
        elif version == '2':
            (self.features_list, self.feature_idxs,
             self.clser_type, self.trained_classifiers, self.features_type,
             self.features_size, self.cls_threshold) = data
        else:
            raise SLUException('Unknown version of the SLU model file: '
                               '{v}.'.format(v=version))

    def get_size(self):
        """Returns the number of features in use."""
        return len(self.features_list)

    def parse_1_best(self,
                     utterance,
                     prev_da=None,
                     utt_nblist=None,
                     ret_cl_map=False,
                     verbose=False):
        """Parses `utterance' and generates the best interpretation in the form
        of a confusion network of dialogue acts.

        Arguments:
            utterance: an instance of Utterance or UtteranceHyp to be parsed
            prev_da: the immediately preceding DA if applicable; this is used
                     only if the model was trained using this information
                     (default: None)
            utt_nblist: mapping { utterance ID: utterance n-best list }, with
                 the utterance n-best list reflecting the ASR output
                 (default: None)
            ret_cl_map: whether the tuple (da_confnet, cl2vals_forms) should be
                        returned instead of just da_confnet.  The second member
                        of the tuple will be a mapping from category labels
                        identified in the utterance to the pair (slot value,
                        surface form).  (The slot name can be parsed from the
                        category label itself.)
            verbose: print debugging output?  More output is printed if
                     verbose > 1.


        """
        if isinstance(utterance, UtteranceHyp):
            # Parse just the utterance and ignore the confidence score.
            utterance = utterance.utterance

        if verbose:
            print 'Parsing utterance "{utt}".'.format(utt=utterance)

        if self.preprocessing:
            utterance = self.preprocessing.text_normalisation(utterance)
            utterance, category_labels = \
                self.preprocessing.values2category_labels_in_utterance(
                    utterance)
            if verbose:
                print 'After preprocessing: "{utt}".'.format(utt=utterance)
                print category_labels
        else:
            category_labels = dict()

        # Generate utterance features.
        extract_feats = self._get_feature_extractor()
        utterance_features = extract_feats(utterance=utterance,
                                           prev_da=prev_da,
                                           utt_nblist=utt_nblist)

        if verbose >= 2:
            print 'Features: ', utterance_features

        feat_vec = np.array(
            [utterance_features.get_feature_vector(self.feature_idxs)])

        da_confnet = DialogueActConfusionNetwork()

        for dai in self.trained_classifiers:
            if verbose:
                print "Using classifier: ", dai

            try:
                dai_prob = (self.trained_classifiers[dai]
                            .predict_proba(feat_vec))
            except Exception as ex:
                print '(EE) Parsing exception: ', ex
                continue

            if verbose:
                print "Classification result: ", dai_prob

            da_confnet.add(dai_prob[0][1], dai)

        if verbose:
            print "DA: ", da_confnet

        if self.preprocessing is not None:
            confnet = self.preprocessing.category_labels2values_in_confnet(
                da_confnet, category_labels)
            confnet.sort()
        else:
            confnet = da_confnet

        if ret_cl_map:
            return confnet, category_labels
        return confnet

    def parse_nblist(self, utterance_list):
        """Parse N-best list by parsing each item in the list and then merging
        the results."""

        if len(utterance_list) == 0:
            raise DAILRException("Empty utterance N-best list.")

        confnets = []
        for prob, utt in utterance_list:
            if "__other__" == utt:
                confnet = DialogueActConfusionNetwork()
                confnet.add(1.0, DialogueActItem("other"))
            else:
                confnet = self.parse_1_best(utt)

            confnets.append((prob, confnet))

            # print prob, utt
            # confnet.prune()
            # confnet.sort()
            # print confnet

        confnet = merge_slu_confnets(confnets)
        confnet.prune()
        confnet.sort()

        return confnet

    def parse_confnet(self, confnet, verbose=False):
        """Parse the confusion network by generating an N-best list and parsing
        this N-best list."""

        #TODO: We should implement a parser which uses features directly from
        # confusion networks.

        # print "Confnet"
        # print confnet
        # print

        nblist = confnet.get_utterance_nblist(n=40)

        # print "NBList"
        # print nblist
        # print

        sem = self.parse_nblist(nblist)

        # print "Semantics"
        # print sem
        # print

        return sem


# TODO Delete this class.
class DAILogRegClassifierLearning(DAILogRegClassifier):
    """Merged into DAILogRegClassifier, retained for compatibility."""
    pass
