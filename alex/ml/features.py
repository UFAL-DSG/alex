#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This code is PEP8-compliant. See http://www.python.org/dev/peps/pep-0008.
"""This module contains generic code for working with feature vectors (or, in
general, collections of features).

"""

from collections import defaultdict
import numpy as np

from alex.utils.cache import lru_cache


class Features(object):
    """A mostly abstract class representing features of an object.

    Attributes:
        features: mapping of the features to their values
        set: set of the features

    """
    # __slots__ = ['features', 'set']

    def __init__(self, *args, **kwargs):
        self.features = defaultdict(float)

    def __str__(self):
        return str(self.features)

    def __getitem__(self, feat):
        """Returns the value of `feature' (0.0 if not present)."""
        # We perform the test for presence explicitly, to maintain a consistent
        # notion of len(self).  If we just returned self.features[k], the
        # defaultdict self.features could self.update(k=float()), thus
        # extending self's length by one.
        return self.features[feat] if feat in self.features else 0.

    def __setitem__(self, feat, val):
        self.features[feat] = val

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
        if hasattr(self, 'generic'):
            generics = self.generic
        else:
            generics = dict()
        for feature in self.features:
            key = generics.get(feature, feature)
            if key in feature_idxs:
                feat_vec[feature_idxs[key]] = self.features[feature]
        return feat_vec

    def get_feature_coords_vals(self, feature_idxs):
        """Builds the feature vector based on the provided mapping of features
        onto their indices.  Returns the vector as a two lists, one of
        feature coordinates, one of feature values.

        Arguments:
            feature_idxs: a mapping { feature : feature index }

        """
        coords = list()
        vals = list()
        if hasattr(self, 'generic'):
            generics = self.generic
        else:
            generics = dict()
        for feature in self.features:
            key = generics.get(feature, feature)
            if key in feature_idxs:
                coords.append(feature_idxs[key])
                vals.append(self.features[feature])
        return coords, vals

    def prune(self, to_remove=None, min_val=None):
        """Discards specified features.

        Arguments:
            to_remove -- collection of features to be removed
            min_val -- threshold for feature values in order for them to be
                       retained (those not meeting the threshold are pruned)

        """
        # Determine which features to prune.
        to_remove_set = set()
        if min_val is not None:
            to_remove_set.update(set(feat for (feat, val) in self.features
                                     if val < min_val))
        if to_remove is not None:
            to_remove_set.update(to_remove if isinstance(to_remove, set)
                                 else set(to_remove))
        # Remove the features from `self.features'.
        old_features = self.features
        self.features = defaultdict(float)
        self.features.update(item for item in old_features.iteritems()
                             if item[0] not in to_remove_set)
        # Remove the features from `self.generic'.
        # FIXME This should go into a more specific class, perhaps
        # AbstractedFeatures.
        if hasattr(self, 'generic'):
            self.generic = dict(item for item in self.generic.iteritems()
                                if item[0] not in to_remove_set)

    @classmethod
    def join(cls, feature_sets, distinguish=True):
        """Joins a number of sets of features, keeping them distinct.

        Arguments:
            distinguish -- whether to treat the feature sets as of different
                types (distinguish=True) or just merge features from them by
                adding their values (distinguish=False).  Default is True.

        Returns a new instance of JoinedFeatures.
        """
        if distinguish:
            return JoinedFeatures(feature_sets)
        else:
            feats = Features()
            for feat_set in feature_sets:
                for feat, val in feat_set.features.iteritems():
                    feats.features[feat] += val
            return feats

    def iter_instantiations(self):
        if hasattr(self, 'instantiable'):
            for abstr in self.instantiable:
                for inst in abstr.iter_instantiations():
                    yield inst

    @classmethod
    def iter_abstract(cls, feature):
        last_mbr = feature
        while True:
            # FIXME Devise another way to check this is a subclass of the
            # AbstractedFeature template.
            if isinstance(last_mbr, Abstracted):
                for tup in last_mbr.iter_instantiations():
                    yield tup
                return
            else:
                if not isinstance(last_mbr, tuple):
                    return
                try:
                    last_mbr = last_mbr[-1]
                except:
                    return

    @classmethod
    def do_with_abstract(cls, feature, meth, *args, **kwargs):
        parts = list()
        last_mbr = feature
        while last_mbr:
            # FIXME Devise another way to check this is a subclass of the
            # AbstractedFeature template.
            if isinstance(last_mbr, Abstracted):
                ret = meth(last_mbr, *args, **kwargs)
                for prev_mbrs in reversed(parts):
                    ret = (prev_mbrs + (ret,))
                return ret
            else:
                if not isinstance(last_mbr, tuple):
                    return feature
                try:
                    parts.append(last_mbr[:-1])
                    last_mbr = last_mbr[-1]
                except Exception:
                    return feature
        return feature


# XXX JoinedFeatures are ignorant of features they are composed of.  It would
# be helpful if this class had an `instantiate' method that would call its
# member features' `instantiate' methods provided they are AbstractedFeatures.
class JoinedFeatures(Features):
    """JoinedFeatures are indexed by tuples (feature_sets_index, feature)
    where feature_sets_index selects the required set of features.  Sets of
    features are numbered with the same indices as they had in the list
    used to initialise JoinedFeatures.

    Attributes:
        features: mapping { (feature_set_index, feature) : value of feature }
        set: set of the (feature_set_index, feature) tuples
        generic: mapping { (feature_set_index, abstracted_feature) :
                            generic_feature }
        instantiable: mapping { feature : generic part of feature } for
            features from self.features.keys() that are abstracted

    """
    def __init__(self, feature_sets):
        self.features = defaultdict(float)
        self.generic = dict()
        self.instantiable = dict()
        for feat_set_idx, feat_set in enumerate(feature_sets):
            if hasattr(feat_set, 'generic'):
                assert hasattr(feat_set, 'instantiable')
                generics = feat_set.generic
                insts = feat_set.instantiable
                for feat, val in feat_set.iteritems():
                    my_feat_key = (feat_set_idx, feat)
                    if feat in generics:
                        self.generic[my_feat_key] = (feat_set_idx,
                                                     generics[feat])
                        self.instantiable[my_feat_key] = insts[feat]
                    self.features[my_feat_key] = val
            else:
                self.features.update(((feat_set_idx, item[0]), item[1])
                                      for item in feat_set.iteritems())

    def iter_instantiations(self):
        for feat in self.instantiable:
            for inst in feat.iter_instantiations():
                yield inst


# TODO Extract the InstantiableI.
class Abstracted(object):
    other_val = "[OTHER]"
    splitter = "="

    # TODO Document.
    def __init__(self):
        """It is important for extending classes to call this initialiser."""
        self.instantiable = {self: self}
        self.is_generic = False

    def join_typeval(self, type_, val):
        return self.splitter.join((type_, val))

    def replace_typeval(self, combined, replacement):
        # TODO Document.
        raise NotImplementedError("This is an abstract method.")

    @classmethod
    def make_other(cls, type_):
        return u'{t}-OTHER'.format(t=type_)


    def iter_typeval(self):
        """Iterates the abstracted items in self, yielding combined
        representations of the type and value of each such token.  An abstract
        method of this class.

        """
        raise NotImplementedError('This is an abstract method.')

    def iter_triples(self):
        for combined_el in self.iter_typeval():
            split = combined_el.split(self.splitter, 2)
            try:
                type_, value = split
            except ValueError:
                value = ''
                type_ = split[0] if combined_el else ''
            # XXX Change the order of return values to combined_el, type_,
            # value.
            yield combined_el, value, type_

    # TODO Rename to something like iter_type_value.
    def iter_instantiations(self):
        types = set()
        for comb, value, type_ in self.iter_triples():
            types.add(type_)
            yield type_, value
        # Construct the other-instantiations for each type yet.
        # FIXME: Is this the correct thing to do?
        for type_ in types:
            yield type_, self.other_val

    def insts_for_type(self, type_):
        return [inst for inst in self.iter_instantiations()
                if inst[0] == type_]

    def insts_for_typeval(self, type_, value):
        same_type = [inst for inst in self.iter_instantiations()
                     if inst[0] == type_]
        # If self is not instantiable for type_,
        if not same_type:
            return same_type  # an empty list
        # If self knows the instantiation asked for,
        if (type_, value) in same_type:
            return [(type_, value)]
        # Else, instantiate with <other> as the value for `type_'.
        return [(type_, self.other_val)]

    def get_generic(self):
        new_combined = self
        type_counts = defaultdict(int)
        for combined, value, type_ in set(self.iter_triples()):
            if type_:
                new_combined = new_combined.replace_typeval(
                    combined,
                    self.join_typeval(type_, str(type_counts[type_])))
                type_counts[type_] += 1
                new_combined.is_generic = True
        return new_combined

    def get_concrete(self):
        ret = self
        for comb, value, type_ in self.iter_triples():
            ret = ret.replace_typeval(comb, value)
        return ret

    def instantiate(self, type_, value, do_abstract=False):
        """Example: Let self represent
            da1(a1=T1:v1)&da2(a2=T2:v2)&da3(a3=T1:v3).

        Calling      self.instantiate("T1", "v1")
        results in

            da1(a1=T1)&da2(a2=v2)&da3(a3=v3) ..if do_abstract == False

            da1(a1=T1)&da2(a2=v2)&da3(a3=T1_other) ..if do_abstract == True

        Calling      self.instantiate("T1", "x1")
        results in

            da1(a1=x1)&da2(a2=v2)&da3(a3=v3) ..if do_abstract == False

            da1(a1=T1_other)&da2(a2=v2)&da3(a3=T1_other)
                ..if do_abstract == True.

        """
        ret = self
        for combined, fld_value, fld_type in self.iter_triples():
            if type_ == fld_type:
                if value == fld_value:
                    ret = ret.replace_typeval(combined, type_)
                else:
                    if do_abstract:
                        ret = ret.replace_typeval(combined,
                            self.join_typeval(type_, self.make_other(type_)))
                    else:
                        ret = ret.replace_typeval(combined,
                            self.join_typeval(type_, fld_value))
            elif do_abstract:
                ret = ret.replace_typeval(combined, fld_type)
        return ret

    def all_instantiations(self, do_abstract=False):
        insts = set()
        for type_, value in self.iter_instantiations():
            inst = self.instantiate(type_, value, do_abstract)
            if inst not in insts:
                yield inst
                insts.add(inst)
        if not insts:
            yield self

    # XXX Is this used anywhere?
    def to_other(self):
        ret = self
        for combined, value, type_ in self.iter_triples():
            ret = ret.replace_typeval(combined, self.make_other(type_))
        return ret

Abstracted.__iter__ = Abstracted.iter_triples


def make_abstract(replaceable, iter_meth=None, replace_meth=None, splitter="=",
                  make_other=None):
    if iter_meth is None:
        iter_meth = replaceable.__iter__

    class AbstractedFeature(Abstracted):
        def __init__(self):
            super(AbstractedFeature, self).__init__(
                iter_meth=iter_meth, replace_meth=replace_meth,
                splitter=splitter, make_other=make_other)

    return AbstractedFeature


# DEPRECATED
def make_abstracted_tuple(abstr_idxs):
    """Example usage:

        AbTuple2 = make_abstract_tuple((2,))
        ab_feat = AbTuple2((dai.dat, dai.name,
                            '='.join(dai.name.upper(), dai.value)))
        # ...
        ab_feat.instantiate('food', 'chinese')
        ab_feat.instantiate('food', 'indian')

    """

    class ReplaceableTuple(tuple):
        def __new__(cls, iterable):
            self = tuple.__new__(cls, iterable)
            return self

        def iter_combined(self):
            for idx in abstr_idxs:
                yield self[idx]

        def replace(self, old, new):
            for idx in abstr_idxs:
                if self[idx] == old:
                    break
            else:
                return self
            return ReplaceableTuple(new if mbr == old else mbr for mbr in self)

        # FIXME!!!
        def to_other(self):
            ret = list(self)
            for idx in abstr_idxs:
                ret[idx] += "-OTHER"
            for combined, value_, type_ in self:
                ret = replace_meth(ret, combined, make_other(type_))
            return ret

    class AbstractedTuple(
        make_abstract(ReplaceableTuple,
                      iter_meth=ReplaceableTuple.iter_combined)):

        def __init__(self, iterable):
            self._combined = ReplaceableTuple(iterable)

    return AbstractedTuple


### Something like this might form the basis for a new implementation of DAIs.
### In contrast to the above class template, this is picklable.
class ReplaceableTuple2(tuple):

    def __new__(cls, iterable):
        self = tuple.__new__(cls, iterable)
        return self

    def iter_combined(self):
        yield self[1]

    def replace(self, old, new):
        if self[1] == old:
            return ReplaceableTuple2(
                new if mbr == old else mbr for mbr in self)
        else:
            return self

    # FIXME!!!
    def to_other(self):
        ret = list(self)
        ret[1] += "-OTHER"
        for combined, value_, type_ in self:
            ret = replace_meth(ret, combined, make_other(type_))
        return ret

class AbstractedTuple2(
    make_abstract(ReplaceableTuple2,
                  iter_meth=ReplaceableTuple2.iter_combined)):

    def __new__(cls, iterable):
        self = ReplaceableTuple2.__new__(cls, iterable)
        return self


# class AbstractedFeatures(Features):
#     __slots__ = ['features', 'set', '_concrete_names', '_concrete_types']
#
#     # TODO Document.
#     def __init__(self):
#         super(AbstractedFeatures, self).__init__()
#         self._concrete_names = set()
#
#     @property
#     def concrete_names(self):
#         """set of instatiations of names from which it was abstracted"""
#         return self._concrete_names
#
#     def add(self, feature):
#         """Use this method to add a new AbstractedFeature."""
#         # Register new concrete names, if any are brought in with the new
#         # feature.
#         # XXX Not tested.
#         map_ = feature._comb_name_type
#         if map_ is not None:
#             self._concrete_names.update(name for (comb, name, type_) in map_)
#             self._concrete_types.update(type_ for (comb, name, type_) in map_)
#         else:
#             self._concrete_names.update(
#                 combined.split(feature.splitter, 2)[1] for combined in
#                 feature.iter_typeval(feature._combined))
#             self._concrete_types.update(
#                 combined.split(feature.splitter, 2)[0] for combined in
#                 feature.iter_typeval(feature._combined))
#
#     def instantiate(self, name):
#         if name in self._concrete_names:
#             return self._instantiate_existing(name)
#         else:
#             return self.features
#
#     @lru_cache(10)
#     def _instantiate_existing(self, name):
#         insted = defaultdict(float)
#         insted.update([feat.instantiate(name) for feat in self.features])
#         return insted
