#!/usr/bin/env python
# coding=utf-8

"""
Data set representation with ARFF input possibility.
"""

from __future__ import unicode_literals
import re
import numpy as np
import scipy.sparse as sp
import copy
from sklearn.datasets.base import Bunch
import math
from alex.components.nlg.tectotpl.core.util import file_stream

__author__ = "Ondřej Dušek"
__date__ = "2012"


class Attribute(object):
    """
    This represents an attribute of the data set.
    """

    def __init__(self, name, type_spec):
        """
        Initialize an attribute, given its ARFF specification.
        Sets the attribute type, list of labels and list of possible values.
        """
        self.name = name
        # numeric attributes
        if type_spec.lower() in ['numeric', 'real', 'integer']:
            self.type = 'numeric'
            self.labels = None
            self.values = None
        # string attributes
        elif type_spec.lower() == 'string':
            self.type = 'string'
            self.labels = []
            self.values = {}
        # nominal attributes
        elif type_spec.startswith('{'):
            # strip '{', '}', append comma to match last value
            type_spec = type_spec[1:-1] + ','
            self.type = 'nominal'
            self.values = {}
            self.labels = []
            for match in re.finditer(DataSet.DENSE_FIELD, type_spec):
                val = match.group(1)
                # quoted value
                if re.match(r'^[\'"].*[\'"]$', val):
                    val = val[1:-1]
                    val = re.sub(r'\\([\n\r\'"\\\t%])', '\1', val)
                # plain value
                else:
                    val = val.strip()
                self.values[val] = float(len(self.labels))
                self.labels.append(val)
        # other attribute types are not supported
        else:
            raise TypeError('Unsupported attribute type: ' + type_spec)

    def numeric_value(self, value):
        """
        Return a numeric representation of the given value.
        Raise a ValueError if the given value does not conform to the
        attribute type.
        """
        # parse number for numeric values
        if self.type == 'numeric':
            try:
                return float(value)
            except ValueError:
                raise ValueError('Invalid numeric value "' + value + '" ' +
                                 'of attribute ' + self.name)
        # return value numbers for nominal values
        elif self.type == 'nominal':
            if not value in self.values:
                raise ValueError('Invalid nominal value "' + value + '" ' +
                                 'of attribute ' + self.name)
            return self.values[value]
        # return values for string attributes, adding new ones is possible
        else:
            if not value in self.values:
                self.values[value] = float(len(self.labels))
                self.labels.append(value)
            return self.values[value]

    def soft_numeric_value(self, value, add_values):
        """
        Same as numeric_value(), but will not raise exceptions for unknown
        numeric/string values. Will either add the value to the list or
        return a NaN (depending on the add_values setting).
        """
        # None = NaN
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return float('NaN')
        # return directly or convert for numeric values
        if self.type == 'numeric':
            if isinstance(value, float):
                return value
            try:
                return float(value)
            except ValueError:
                raise ValueError('Invalid numeric value "' + value + '" ' +
                                 'of attribute ' + self.name)
        # return value numbers for nominal/string values,
        # add unseen values to list if add_values == True.
        else:
            if not value in self.values:
                if add_values:
                    self.values[value] = float(len(self.labels))
                    self.labels.append(value)
                else:
                    return float('NaN')
            return self.values[value]

    def value(self, numeric_val):
        """
        Given a numeric (int/float) value, returns the corresponding string
        value for string or nominal attributes, or the identical value for
        numeric attributes.
        Returns None for missing nominal/string values, NaN for missing numeric
        values.
        """
        if self.type == 'numeric':
            return numeric_val
        if math.isnan(numeric_val):
            return None
        return self.labels[int(numeric_val)]

    def get_arff_type(self):
        """
        Return the ARFF type of the given attribute (numeric, string or
        list of values for nominal attributes).
        """
        if self.type == 'nominal':
            return "{'" + "','".join([re.sub('(' + DataSet.SPEC_CHARS + ')',
                                             r'\\\1', label)
                                      for label in self.labels]) + "'}"
        else:
            return self.type

    def values_set(self):
        """
        Return a set of all possible values for this attribute.
        """
        return set(self.labels)

    @property
    def num_values(self):
        """
        Return the number of distinct values found in this attribute.
        Returns -1 for numeric attributes where the number of values is
        not known.
        """
        if self.type == 'numeric':
            return -1
        else:
            return len(self.labels)

    def __repr__(self):
        """
        This is the same as __str__.
        """
        return self.__str__()

    def __str__(self):
        """
        String representation returns the attribute name and type.
        """
        return self.__class__.__name__ + ': ' + \
                self.name + ' (' + self.type + ')'


class DataSet(object):
    """
    ARFF relation data representation.
    """

    # Regex matching an ARFF sparse instance field
    SPARSE_FIELD = r'([0-9]+)\s+' + \
                   r'([^"\'\s][^,]*|' + \
                   r'\'[^\']*(\\\'[^\']*)*\'|' + \
                   r'"[^"]*(\\"[^"]*)*"),'
    # Regex matching an ARFF dense instance field
    DENSE_FIELD = r'([^"\'][^,]*|' + \
                  r'\'[^\']*(\\\'[^\']*)*(?<!\\)\'|' + \
                  r'"[^"]*(\\"[^"]*)*(?<!\\)"),'
    # ARFF special characters for regexps
    SPEC_CHARS = r'[\n\r\'"\\\t%]'

    def __init__(self):
        """
        Just initialize the internal data structures (as empty).
        """
        self.relation_name = ''
        self.data = []
        self.inst_weights = []
        self.attribs = []
        self.attribs_by_name = {}
        self.is_sparse = False

    @property
    def is_empty(self):
        """
        Return true if the data structures are empty.
        """
        return not self.relation_name and not self.data and not self.attribs

    def as_dict(self, mask_attrib=[], select_attrib=[]):
        """
        Return the data as a list of dictionaries, which is useful
        as an input to DictVectorizer.

        Attributes (numbers or indexes) listed in mask_attrib are not
        added to the dictionary. Missing values are also not added to the
        dictionary.
        If mask_attrib is not set but select_attrib is set, only attributes
        listed in select_attrib are added to the dictionary.
        """
        ret = []
        mask_set = self.__get_mask_set(select_attrib, mask_attrib)
        for inst in self.data:
            # find relevant data (different for sparse and dense)
            if self.is_sparse:
                num_vals = zip(inst.rows[0], inst.data[0])
            else:
                num_vals = enumerate(inst)
            # add the data to a dictionary which is appended to the list
            ret.append({self.attribs[attr_num].name:
                        self.attribs[attr_num].value(val)
                        for attr_num, val in num_vals
                        if attr_num not in mask_set and not math.isnan(val)})
        # return the list of all collected dictionaries
        return ret

    def as_bunch(self, target, mask_attrib=[], select_attrib=[]):
        """
        Return the data as a scikit-learn Bunch object. The target parameter
        specifies the class attribute.
        """
        mask_set = self.__get_mask_set(select_attrib, mask_attrib + [target])
        # prepare the data matrixes
        X = np.empty(shape=(len(self.attribs) - len(mask_set), 0))
        y = np.empty(shape=(1, 0))
        # identify the target attribute
        target = self.attrib_index(target)
        # divide and convert the data to X, y
        if self.data:
            # dense matrix
            if not self.is_sparse:
                y = np.array([inst[target] for inst in self.data])
                X = np.matrix([[val for idx, val in enumerate(inst)
                                if idx not in mask_set]
                               for inst in self.data])
            # sparse matrix
            else:
                y = np.array([inst[0, target] for inst in self.data])
                data_buf = []
                for inst in self.data:
                    filt_inst = sp.csr_matrix([val for idx, val
                                               in enumerate(inst.toarray()[0])
                                               if idx not in mask_set])
                    data_buf.append(filt_inst)
                X = sp.vstack(tuple(data_buf), 'csr')
        # return as Bunch
        return Bunch(data=X,
                     DESCR=self.relation_name,
                     target=y,
                     target_names=self.attribs[target].labels)

    def load_from_arff(self, filename, encoding='UTF-8'):
        """
        Load an ARFF file/stream, filling the data structures.
        """
        # initialize
        if not self.is_empty:
            raise IOError('Cannot store second data set into the same object.')
        status = 'header'  # we first assume to read the header
        line_num = 1  # line counter
        instances = []
        weights = []
        # open the file
        fh = file_stream(filename, encoding=encoding)
        # parse the file
        for line in fh:
            line = line.strip()
            # skip comments
            if line.startswith('%'):
                continue
            # relation name
            elif line.lower().startswith('@relation'):
                self.relation_name = line.split(None, 1)[1]
            # attribute definition
            elif line.lower().startswith('@attribute'):
                attr_name, attr_type = line.split(None, 2)[1:]
                self.attribs.append(Attribute(attr_name, attr_type))
            # data section start
            elif line.lower().startswith('@data'):
                status = 'data'
            # data lines
            elif status == 'data' and line != '':
                inst, weight = self.__parse_line(line, line_num)
                instances.append(inst)
                weights.append(weight)
            line_num += 1
        fh.close()
        # store the resulting matrix
        self.data = instances
        self.inst_weights = weights
        # remember attribute names
        self.attribs_by_name = {attr.name: idx
                                for idx, attr in enumerate(self.attribs)}

    def save_to_arff(self, filename, encoding='UTF-8'):
        """
        Save the data set to an ARFF file
        """
        # open the file
        fh = file_stream(filename, 'w', encoding)
        # print the relation name
        print >> fh, '@relation ' + (self.relation_name
                                     if self.relation_name is not None
                                     else '<noname>')
        # print the list of attributes
        for attrib in self.attribs:
            print >> fh, '@attribute ' + attrib.name + ' ' + \
                    attrib.get_arff_type()
        # print instances
        print >> fh, '@data'
        for inst, weight in zip(self.data, self.inst_weights):
            print >> fh, self.__get_arff_line(inst, weight)

    def load_from_matrix(self, attr_list, matrix):
        """
        Fill in values from a matrix.
        """
        # initialize
        if not self.is_empty:
            raise IOError('Cannot store second data set into the same object.')
        if len(attr_list) != matrix.shape[1]:
            raise ValueError('Number of attributes must' +
                             'correspond to matrix width.')
        # store attribute lists
        self.attribs = copy.deepcopy(attr_list)
        self.attribs_by_name = {attr.name: idx
                                for idx, attr in enumerate(self.attribs)}
        self.is_sparse = sp.issparse(matrix)
        # store data
        if self.is_sparse:
            self.data = [matrix[line, :].tolil()
                         for line in xrange(matrix.shape[0])]
        else:
            self.data = [matrix[line] for line in xrange(matrix.shape[0])]

    def load_from_vect(self, attrib, vect):
        """
        Fill in values from a vector of values and an attribute (allow adding
        values for nominal attributes).
        """
        # store attribute information
        attrib = copy.deepcopy(attrib)
        self.attribs = [attrib]
        self.attribs_by_name = {attrib.name: 0}
        self.is_sparse = False
        # store the data
        self.data = [[attrib.soft_numeric_value(val, True)] for val in vect]

    def load_from_dict(self, data, attrib_types={}):
        """
        Fill in values from a list of dictionaries (=instances).
        Attributes are assumed to be of string type unless specified
        otherwise in the attrib_types variable.
        Currently only capable of creating dense data sets.
        """
        if not self.is_empty:
            raise IOError('Cannot store second data set into the same object.')
        self.attribs = []
        self.attribs_by_name = {}
        buf = []
        # prepare 'instances' with stringy values, prepare attributes
        for dict_inst in data:
            inst = [None] * len(self.attribs)
            for attr_name, val in dict_inst.iteritems():
                try:
                    attr = self.get_attrib(attr_name)
                # attribute does not exist, create it
                except:
                    attr = Attribute(attr_name,
                                     attrib_types.get(attr_name, 'string'))
                    self.attribs_by_name[attr_name] = len(self.attribs)
                    self.attribs.append(attr)
                    inst.append(None)
                # add the stringy value to the instance
                idx = self.attrib_index(attr_name)
                inst[idx] = val
            buf.append(inst)
        # convert instances to numeric representation and add to my list
        for str_inst in buf:
            if len(str_inst) < len(self.attribs):
                str_inst += [None] * (len(self.attribs) - len(str_inst))
            inst = [self.get_attrib(idx).soft_numeric_value(val, True)
                    for idx, val in enumerate(str_inst)]
            self.data.append(inst)

    def attrib_index(self, attrib_name):
        """
        Given an attribute name, return its number. Given a number, return
        precisely that number. Return -1 on failure.
        """
        if isinstance(attrib_name, int):
            return attrib_name
        return self.attribs_by_name.get(attrib_name, -1)

    def get_attrib(self, attrib):
        """
        Given an attribute name or index, return the Attribute object.
        """
        if isinstance(attrib, basestring):
            attrib = self.attribs_by_name[attrib]
        return self.attribs[attrib]

    def get_headers(self):
        """
        Return a copy of the headers of this data set (just attributes list,
        relation name and sparse/dense setting)
        """
        ret = DataSet()
        ret.attribs = copy.deepcopy(self.attribs)
        ret.attribs_by_name = copy.deepcopy(self.attribs_by_name)
        ret.data = []
        ret.is_sparse = copy.deepcopy(self.is_sparse)
        ret.relation_name = copy.deepcopy(self.relation_name)
        return ret

    def attrib_as_vect(self, attrib, dtype=None):
        """
        Return the specified attribute (by index or name) as a list
        of values.
        If the data type parameter is left as default, the type of the returned
        values depends on the attribute type (strings for nominal or string
        attributes, floats for numeric ones). Set the data type parameter to
        int or float to override the data type.
        """
        # convert attribute name to index
        if isinstance(attrib, basestring):
            attrib = self.attrib_index(attrib)
        # default data type: according to the attribute type
        if dtype is None:
            dtype = lambda x: self.attribs[attrib].value(x)
        elif dtype == int:
            dtype = lambda x: int(x) if not math.isnan(x) else None
        # return the values
        if self.is_sparse:
            return [dtype(line[0, attrib]) for line in self.data]
        else:
            return [dtype(line[attrib]) for line in self.data]

    def rename_attrib(self, old_name, new_name):
        """
        Rename an attribute of this data set (find it by original name or
        by index).
        """
        attr = self.get_attrib(old_name)
        attr.name = new_name

    def separate_attrib(self, attribs):
        """
        Given a list of attributes, delete them from the data set
        and return them as a new separate data set.
        Accepts a list of names or indexes, or one name, or one index.
        """
        attribs, attribs_set = self.__get_attrib_list(attribs)
        # initialize the second data set
        separ = DataSet()
        separ.is_sparse = self.is_sparse
        separ.relation_name = self.relation_name + \
                 '-sep-' + ",".join([str(attrib) for attrib in attribs])
        separ.inst_weights = copy.deepcopy(self.inst_weights)
        # separate columns in sparse matrixes
        if self.is_sparse:
            # cache column shifting (i.e. number of deleted to the left)
            # and new indexes for the separated data
            shifts = {idx: len([a for a in attribs if a < idx])
                      for idx in xrange(len(self.attribs))}
            for sep_idx, old_idx in enumerate(attribs):
                shifts[old_idx] = old_idx - sep_idx
            # separate data in individual instances
            for inst in self.data:
                # find sparse indexes to split-out
                sep_inst = sp.lil_matrix((1, len(attribs)))
                sep_cols = [col in attribs_set for col in inst.rows[0]]
                # shift sparse column indexes
                lshift = np.array([shifts[col] for col in inst.rows[0]])
                inst.rows[0] -= lshift
                # split out the desired columns
                sep_inst.rows[0] = [col for col, sep
                                    in zip(inst.rows[0], sep_cols) if sep]
                inst.rows[0] = [col for col, sep
                                in zip(inst.rows[0], sep_cols) if not sep]
                sep_inst.data[0] = [val for val, sep
                                    in zip(inst.data[0], sep_cols) if sep]
                inst.data[0] = [val for val, sep
                                in zip(inst.data[0], sep_cols) if not sep]
                # update the original instance shape
                inst._shape = (1, len(self.attribs) - len(attribs))
                # add the separated data to the other data set
                separ.data.append(sep_inst)
        # separate columns in dense matrixes
        else:
            for idx, inst in enumerate(self.data):
                self.data[idx] = [val for col, val in enumerate(inst)
                                  if col not in attribs_set]
                sep_inst = [val for col, val in enumerate(inst)
                            if col in attribs_set]
                separ.data.append(sep_inst)
        # separate metadata
        separ.attribs = [attr for idx, attr in enumerate(self.attribs)
                         if idx in attribs_set]
        self.attribs = [attr for idx, attr in enumerate(self.attribs)
                        if not idx in attribs_set]
        separ.attribs_by_name = {attr.name: idx
                                 for idx, attr in enumerate(separ.attribs)}
        self.attribs_by_name = {attr.name: idx
                                for idx, attr in enumerate(self.attribs)}
        return separ

    def delete_attrib(self, attribs):
        """
        Given a list of attributes, delete them from the data set.
        Accepts a list of names or indexes, or one name, or one index.
        """
        attribs, attribs_set = self.__get_attrib_list(attribs)
        # delete columns in sparse matrixes
        if self.is_sparse:
            # cache column shifting (i.e. number of deleted to the left)
            lshifts = {idx: len([a for a in attribs if a < idx])
                       for idx in xrange(len(self.attribs))}
            for inst in self.data:
                # find sparse indexes to remove
                rem = [idx for idx, col in enumerate(inst.rows[0])
                       if col in attribs_set]
                # shift sparse column indexes
                lshift = np.array([lshifts[col] for col in inst.rows[0]])
                inst.rows[0] -= lshift
                # remove the desired columns and update the shape
                inst.rows[0] = np.delete(inst.rows[0], rem)
                inst.data[0] = np.delete(inst.data[0], rem)
                inst._shape = (1, len(self.attribs) - len(attribs))
        # delete columns in dense matrixes
        else:
            self.data = [np.delete(inst, attribs) for inst in self.data]
        # delete the attributes from metadata
        self.attribs = [attr for idx, attr in enumerate(self.attribs)
                        if not idx in attribs_set]
        self.attribs_by_name = {attr.name: idx
                                for idx, attr in enumerate(self.attribs)}

    def merge(self, other):
        """
        Merge two DataSet objects. The list of attributes will be concatenated.
        The two data sets must have the same number of instances and
        be either both sparse or both non-sparse.

        Instance weights are left unchanged (from this data set).
        """
        # check compatibility
        if self.is_sparse != other.is_sparse or \
                len(self) != len(other):
            raise ValueError('Data sets are not compatible!')
        # merge instances
        if self.is_sparse:
            for my_inst, other_inst in zip(self.data, other.data):
                my_inst.rows[0].extend([col + len(self.attribs)
                                        for col in other_inst.rows[0]])
                my_inst.data[0].extend(other_inst.data[0])
                my_inst._shape = (1, len(self.attribs) + len(other.attribs))
        else:
            for my_inst, other_inst in zip(self.data, other.data):
                my_inst.extend(other_inst)
        # merge meta data
        self.attribs.extend(other.attribs)
        self.attribs_by_name = {attr.name: idx
                                for idx, attr in enumerate(self.attribs)}
        self.relation_name += '_' + other.relation_name

    def append(self, other):
        """
        Append instances from one data set to another. Their attributes must
        be compatible (of the same types).
        """
        # sanity checks
        self.__check_headers(other)
        # append the instances
        # update possible values for string and nominal using loose_nominal
        for inst in other.data:
            self.data.append(other.__convert_to_headers(inst, self, True))
            self.inst_weights.extend(copy.deepcopy(other.inst_weights))

    def add_attrib(self, attrib, values=None):
        """
        Add a new attribute to the data set, with pre-filled values
        (or missing, if not set).
        """
        # create a vector of missing values, if none are given
        if values is None:
            values = [None] * len(self)
        # if values are given, check vector size
        elif len(values) != len(self):
            raise ValueError('The size of the attribute vector must match!')
        # create a temporary data set and merge
        temp = DataSet()
        temp.load_from_vect(attrib, values)
        self.merge(temp)

    def match_headers(self, other, add_values=False):
        """
        Force this data set to have equal headers as the other data set.
        This cares for different values of nominal/numeric attributes --
        (numeric values will be the same, values unknown in the other data
        set will be set to NaNs).
        In other cases, such as a different number or type of attributes,
        an exception is thrown.
        """
        # sanity checks
        self.__check_headers(other)
        # go through nominal and string attribute values
        for idx, inst in enumerate(self.data):
            self.data[idx] = self.__convert_to_headers(inst, other, add_values)
        # copy the headers from other
        self.attribs = [copy.deepcopy(attr) for attr in other.attribs]

    def value(self, instance, attr_idx):
        """
        Return the value of the given instance and attribute.
        """
        if isinstance(attr_idx, basestring):
            attr_idx = self.attrib_index(attr_idx)
        attr = self.attribs[attr_idx]
        if self.is_sparse:
            return attr.value(self.data[instance][0, attr_idx])
        return attr.value(self.data[instance][attr_idx])

    def instance(self, index, dtype='dict', do_copy=True):
        """
        Return the given instance as a dictionary (or a list, if specified).

        If do_copy is set to False, do not create a copy of the list for
        dense instances (other types must be copied anyway).
        """
        inst = self.data[index]
        if dtype == 'list':
            if self.is_sparse:
                return inst.toarray()[0].tolist()
            return copy.deepcopy(inst) if do_copy else inst
        elif dtype == 'dict':
            if self.is_sparse:
                return {self.attribs[attr].name: self.attribs[attr].value(val)
                        for attr, val in zip(inst.rows[0], inst.data[0])}
            return {self.attribs[attr].name: self.attribs[attr].value(val)
                    for attr, val in enumerate(inst)}
        raise ValueError('Unsupported data type')

    def subset(self, *args, **kwargs):
        """
        Return a data set representing a subset of this data set's values.

        Args can be a slice or [start, ] stop [, stride] to create a slice.
        No arguments result in a complete copy of the original.

        Kwargs may contain just one value -- if copy is set to false,
        the sliced values are removed from the original data set.
        """
        # obtain the real arguments
        if len(args) > 3:
            raise TypeError('Too many arguments')
        elif len(args) == 0:
            indexes = slice(len(self))
        elif len(args) == 1 and isinstance(args[0], slice):
            indexes = args[0]
        else:
            indexes = slice(*args)
        if kwargs.keys() not in [[], ['copy']]:
            raise TypeError('Unsupported keyword arguments')
        keep_copy = kwargs.get('copy', True)
        # copy metadata
        subset = self.__metadata_copy('_slice_' + str(indexes.start) +
                                      '-' + str(indexes.stop) +
                                      '-' + str(indexes.step))
        # copy/move instances
        if keep_copy:
            subset.data = [copy.deepcopy(self.data[idx])
                           for idx in xrange(*indexes.indices(len(self)))]
            subset.inst_weights = [self.inst_weights[idx] for idx
                                   in xrange(*indexes.indices(len(self)))]
        else:
            idxs = range(*indexes.indices(len(self)))
            subset.data = [self.data[idx] for idx in idxs]
            subset.inst_weights = [self.inst_weights[idx] for idx in idxs]
            idxs_set = set(idxs)
            self.data = [self.data[idx] for idx in xrange(len(self))
                         if not idx in idxs_set]
            self.inst_weights = [self.inst_weights[idx] for idx
                                 in xrange(len(self)) if not idx in idxs_set]
        return subset

    def filter(self, filter_func, keep_copy=True):
        """
        Filter the data set using a filtering function and return a
        filtered data set.

        The filtering function must take two arguments - current instance
        index and the instance itself in an attribute-value dictionary
        form - and return a boolean.

        If keep_copy is set to False, filtered instances will be removed from
        the original data set.
        """
        filtered = self.__metadata_copy('_filtered')
        filt_res = [filter_func(idx, self.instance(idx))
                    for idx in xrange(len(self))]
        true_idxs = [idx for idx, res in enumerate(filt_res) if res]
        if keep_copy:
            filtered.data = [copy.deepcopy(self.data[idx])
                             for idx in true_idxs]
            filtered.inst_weights = [self.inst_weights[idx]
                                     for idx in true_idxs]
        else:
            false_idxs = [idx for idx, res in enumerate(filt_res) if not res]
            data_true = [self.data[idx] for idx in true_idxs]
            weights_true = [self.inst_weights[idx] for idx in true_idxs]
            data_false = [self.data[idx] for idx in false_idxs]
            weights_false = [self.inst_weights[idx] for idx in false_idxs]
            self.data = data_false
            self.inst_weights = weights_false
            filtered.data = data_true
            filtered.inst_weights = weights_true
        return filtered

    def split(self, split_func, keep_copy=True):
        """
        Split the data set using a splitting function and return a dictionary
        where keys are different return values of the splitting function and
        values are data sets containing instances which yield the respective
        splitting function return values.

        The splitting function takes two arguments - the current instance index
        and the instance itself as an attribute-value dictionary. Its return
        value determines the split.

        If keep_copy is set to False, ALL instances will be removed from
        the original data set.
        """
        ret = {}
        for idx in xrange(len(self)):
            key = split_func(idx, self.instance(idx))
            if not key in ret:
                ret[key] = self.__metadata_copy('_split_' + key)
            if keep_copy:
                ret[key].data.append(self.data[idx])
            else:
                ret[key].data.append(copy.deepcopy(self.data[idx]))
        if not keep_copy:
            self.data = []
        return ret

    def __parse_line(self, line, line_num):
        """"
        Parse one ARFF data line (dense or sparse, return appropriate
        array).
        """
        # check weight, if needed
        weight = 1.0
        match_weight = re.search(r',\s*\{([0-9]+(\.[0-9]*)?|\.[0-9]+)\}$',
                                 line)
        if match_weight:
            weight = float(match_weight.group(1))
            line = re.sub(r',\s*\{[^\{\}]+\}$', '', line)
        # sparse instance
        if line.startswith('{'):
            self.is_sparse = True  # trigger sparseness
            line = line.strip('{}') + ','  # append comma to match last value
            values = np.zeros(len(self.attribs))
            # capture all fields
            for match in re.finditer(self.SPARSE_FIELD, line):
                # extract index and value
                idx, val = match.group(1, 2)
                idx = int(idx)
                # undefined value
                if val == '?':
                    values[idx] = float('NaN')
                # quoted value
                elif re.match(r'^[\'"].*[\'"]$', val):
                    val = val[1:-1]
                    val = re.sub(r'\\(' + self.SPEC_CHARS + ')', r'\1', val)
                    values[idx] = self.__get_numeric_value(idx, val, line_num)
                # plain value
                else:
                    val = val.strip()
                    values[idx] = self.__get_numeric_value(idx, val, line_num)
            # return in sparse format
            return sp.lil_matrix(values), weight
        # dense instance
        else:
            values = []
            line += ','  # append comma to match last value
            for match in re.finditer(self.DENSE_FIELD, line):
                val = match.group(1)
                # undefined value
                if val == '?':
                    values.append(float('NaN'))
                # quoted value
                elif re.match(r'^[\'"].*[\'"]$', val):
                    val = val[1:-1]
                    val = re.sub(r'\\(' + self.SPEC_CHARS + ')', r'\1', val)
                    values.append(self.__get_numeric_value(len(values),
                                                           val, line_num))
                # plain value
                else:
                    val = val.strip()
                    values.append(self.__get_numeric_value(len(values),
                                                           val, line_num))
            return values, weight

    def __get_attrib_list(self, attribs):
        """
        Convert the given list of names or indexes, or one name, or one index
        to a list and a set of indexes.
        """
        if isinstance(attribs, list):
            attribs = [self.attrib_index(a) if isinstance(a, basestring) else a
                       for a in attribs]
        elif isinstance(attribs, basestring):
            attribs = [self.attrib_index(attribs)]
        elif isinstance(attribs, int):
            attribs = [attribs]
        # cache set of attributes to be deleted
        attribs_set = set(attribs)
        return attribs, attribs_set

    def __check_headers(self, other):
        """
        Sanity check for appending / headers matching. Checks if the data sets
        have the same number of attributes and if the attributes are of the
        same type. Same values for numeric/string attributes are not required.
        """
        if len(self.attribs) != len(other.attribs):
            raise ValueError('Data sets have different numbers of attributes!')
        for my_attr, other_attr in zip(self.attribs, other.attribs):
            if my_attr.type != other_attr.type:
                raise ValueError('Attributes ' + my_attr + ' and ' +
                                 other_attr + ' must be of the same type!')

    def __convert_to_headers(self, inst, other, add_values):
        """
        Convert numeric values for an instance to match the string/nominal
        headers of the given data set. Returns a new instance (dense or
        sparse).
        """
        if other.is_sparse:
            # convert through dense as 0 may have a different meaning
            vals = [self.attribs[col].value(val)
                    for col, val in enumerate(inst.toarray()[0])]
            vals = [other.attribs[col].soft_numeric_value(val, add_values)
                    for col, val in enumerate(vals)]
            new_inst = sp.lil_matrix((1, len(other.attribs)))
            new_inst.rows[0] = [col for col, val in enumerate(vals)
                                if val != 0]
            new_inst.data[0] = [val for col, val in enumerate(vals)
                                if val != 0]
            return new_inst
        # dense data sets
        else:
            vals = [self.attribs[col].value(val)
                    for col, val in enumerate(inst)]
            return [other.attribs[col].soft_numeric_value(val, add_values)
                              for col, val in enumerate(vals)]

    def __get_numeric_value(self, attr_num, value, line_num):
        """
        Return the attribute value as a float,
        i.e. convert the string value to number for numeric attributes,
        look up the value number for nominal ones and keep track of possible
        values for string attributes.
        """
        if attr_num >= len(self.attribs):
            raise TypeError('Attribute number ' + str(attr_num) +
                            ' out of range on line ' + str(line_num))
        attr = self.attribs[attr_num]
        try:
            return attr.numeric_value(value)
        except ValueError as e:
            raise ValueError(e.message + ' on line ' + str(line_num))

    def __get_arff_line(self, inst, weight=1.0):
        """
        Return a sparse or a dense ARFF data line
        """
        if self.is_sparse:
            ret = "{" + ",".join([str(int(idx)) + ' ' +
                                  self.__get_arff_val(idx, attr)
                                  for idx, attr in zip(inst.rows[0],
                                                       inst.data[0])]) + '}'
        else:
            ret = ",".join([self.__get_arff_val(idx, attr)
                            for idx, attr in enumerate(inst)])
        if weight != 1.0:
            ret += ', {' + str(weight) + '}'
        return ret

    def __get_arff_val(self, attr_num, value):
        """
        Return an ARFF-output safe value.
        """
        # missing values
        if math.isnan(value):
            return '?'
        # numeric values
        if self.attribs[attr_num].type == 'numeric':
            return str(value)
        # stringy values
        else:
            value = self.attribs[attr_num].value(value)
            # decide if it needs to be quoted
            quote = False
            if value == '' or \
                    re.search('(' + self.SPEC_CHARS + '|[{}?, ])', value):
                quote = True
            # backslash for special chars
            value = re.sub('(' + self.SPEC_CHARS + ')', r'\\\1', value)
            # return the result (quoted or not)
            return value if not quote else "'" + value + "'"

    def __metadata_copy(self, add_to_name=''):
        """
        Returns a copy of this data set with no instances.
        Adds the specified string to the name if required.
        """
        my_copy = DataSet()
        my_copy.is_sparse = self.is_sparse
        my_copy.attribs = copy.deepcopy(self.attribs)
        my_copy.attribs_by_name = copy.deepcopy(self.attribs_by_name)
        my_copy.relation_name = self.relation_name + add_to_name
        my_copy.data = []
        return my_copy

    def __get_mask_set(self, select_attrib, mask_attrib):
        """
        Given a list of specifically selected or specifically masked
        attributes, this returns the set of attributes to avoid.
        """
        deselect_set = set()
        mask_set = set()
        if select_attrib:
            select_attrib, select_set = self.__get_attrib_list(select_attrib)
            deselect_set = set(range(len(self.attribs))) - select_set
        if mask_attrib:
            mask_attrib, mask_set = self.__get_attrib_list(mask_attrib)
        return mask_set | deselect_set

    def __len__(self):
        """
        Return the number of instances in this data set.
        """
        return len(self.data)

    def __getitem__(self, key):
        """
        This supports access to individual instances by index (will
        be returned as a dict), to individual attributes (returned as
        vector of values) or slicing and filtering (see subset() and
        filter()).
        """
        # tuple: return the value given by the coordinates
        if isinstance(key, tuple) and len(key) == 2 and \
                isinstance(key[0], int) and (isinstance(key[1], int) or
                                             isinstance(key[1], basestring)):
            return self.value(*key)
        # one number: return one element
        elif isinstance(key, int):
            return self.instance(key)
        # string: return attribute as vector
        elif isinstance(key, basestring):
            return self.attrib_as_vect(key)
        # slicing
        elif isinstance(key, slice):
            return self.subset(key)
        # filtering
        elif hasattr(key, '__call__'):
            return self.filter(key)
        raise ValueError('Unsupported index type!')

    def __repr__(self):
        """
        This is the same as __str__.
        """
        return self.__str__()

    def __str__(self):
        """
        String representation returns the relation name, number of
        attributes and instances.
        """
        ret = self.__class__.__name__ + ': '
        if self.is_empty:
            return ret + 'empty'
        ret += 'relation ' + (self.relation_name
                              if self.relation_name is not None
                              else '<noname>') + ': '
        ret += ('sparse' if self.is_sparse else 'dense') + ', ' + \
                str(len(self.attribs)) + ' attributes, ' + \
                str(len(self)) + ' instances.'
        return ret

    def __iter__(self):
        """
        Return an iterator over instances.
        """
        return DataSetIterator(self)


class DataSetIterator(object):
    """
    An iterator over the instances of a data set.
    """

    def __init__(self, dataset):
        """
        Initialize pointing at the beginning.
        """
        self.dataset = dataset
        self.pos = 0

    def __iter__(self):
        return self

    def next(self):
        """
        Move to the next instance.
        """
        try:
            res = self.dataset.instance(self.pos)
            self.pos += 1
            return res
        except IndexError:
            raise StopIteration
