#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
"""This module contains generic code for working with feature vectors (or, in
general, collections of features).

"""

from collections import defaultdict
import numpy as np


# XXX Is Features.set needed anywhere?  I would suggest removing it as a class
# field.
class Features(object):
    """An abstract class representing features of an object.

    Attributes:
        features: mapping of the features to their values
        set: set of the features

    """
    def __init__(self, *args, **kwargs):
        self.features = defaultdict(float)
        self.set = set()

    def __str__(self):
        return str(self.features)

    def __getitem__(self, feat):
        """Returns the value of `feature' (0.0 if not present)."""
        # We perform the test for presence explicitly, to maintain a consistent
        # notion of len(self).  If we just returned self.features[k], the
        # defaultdict self.features could self.update(k=float()), thus
        # extending self's length by one.
        return self.features[feat] if feat in self.features else 0.

    def __contains__(self, feature):
        """Whether `feature' is among this object's features."""
        return feature in self.features

    def __iter__(self):
        """Iterates this object's features."""
        for feature in self.features:
            yield feature

    def __len__(self):
        """An optional method."""
        return len(self.features)

    def iteritems(self):
        """Iterates tuples of this object's features and their values."""
        for item in self.features.iteritems():
            yield item

    def get_feature_vector(self, feature_idxs):
        """Builds the feature vector based on the provided mapping of features
        onto their indices.

        Arguments:
            feature_idxs: a mapping { feature : feature index }

        """
        feat_vec = np.zeros(len(feature_idxs))
        for feature in self.features:
            if feature in feature_idxs:
                feat_vec[feature_idxs[feature]] = self.features[feature]
        return feat_vec

    def prune(self, to_remove):
        """Discards all features from `to_remove' from self."""
        # Remove the features from `self.set'.
        to_remove_set = (to_remove if isinstance(to_remove, set)
                         else set(to_remove))
        self.set -= to_remove_set
        # Remove the features from `self.features'.
        old_features = self.features
        self.features = defaultdict(float)
        self.features.update(item for item in old_features.iteritems() if
                             item[0] not in to_remove_set)

    @classmethod
    def join(cls, *feature_sets):
        """Joins a number of sets of features, keeping them distinct.

        Returns a new instance of JoinedFeatures.
        """
        return JoinedFeatures(*feature_sets)


class JoinedFeatures(Features):
    """JoinedFeatures are indexed by tuples (feature_sets_index, feature)
    where feature_sets_index selects the required set of features.  Sets of
    features are numbered with the same indices as they had in the list
    used to initialise JoinedFeatures.

    Attributes:
        features: mapping { (feature_set_index, feature) : value of feature }
        set: set of the (feature_set_index, feature) tuples

    """

    def __init__(self, *feature_sets):
        self.features = defaultdict(float)
        for feat_set_idx, feat_set in enumerate(feature_sets):
            self.features.update(((feat_set_idx, item[0]), item[1])
                                 for item in feat_set.iteritems())
        self.set = set(self.features)
        # self.set = set((set_idx, feat) for set_idx in xrange(len(feature_sets))
                       # for feat in feature_sets[set_idx])

    # def __len__(self):
        # return sum(map(len, self.features))

    # def __getitem__(self, feat_tup):
        # if not len(feat_tup) == 2:
            # raise TypeError(
                # "JoinedFeatures are indexed by a tuple of length 2.")
        # try:
            # return self.features[feat_tup[0]][feat_tup[1]]
        # except IndexError:
            # return 0.

    # def __contains__(self, feat_tup):
        # if not len(feat_tup) == 2:
            # raise TypeError(
                # "JoinedFeatures are indexed by a tuple of length 2.")
        # try:
            # return feat_tup[1] in self.features[feat_tup[0]]
        # except IndexError:
            # return False

    # def __iter__(self):
        # for feat_set in self.features:
            # for feat in feat_set:
                # yield feat

    # def get_feature_vector(self, feature_idxs):
        # feat_vec = np.zeros(len(feature_idxs))
        # for feat_set_idx, feat_set in enumerate(self.features):
            # for feat in feat_set:
                # if (feat_set_idx, feat) in feature_idxs:
                    # feat_idx = feature_idxs[(feat_set_idx, feat)]
                    # feat_vec[feat_idx] = self.features[feat_set_idx][feat]
        # return feat_vec
