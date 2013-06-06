#!/usr/bin/env python
# -*- coding: utf8 -*-

"""Factor representation for computing with discrete variables."""

import numpy as np
import operator
import abc

from collections import defaultdict
from scipy.misc import logsumexp

ZERO = 0.000000001


def to_log(n, out=None):
    """Convert number to log arithmetic."""
    if np.isscalar(n):
        return np.log(ZERO) if n < ZERO else np.log(n)
    else:
        n[n < ZERO] = ZERO
        return np.log(n, out)


def from_log(n):
    """Convert number from log arithmetic."""
    return np.exp(n)


class Factor(object):

    """Abstract class for factor."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, variables, variable_values, prob_table):
        self.variables = variables
        self.variable_values = variable_values
        self.prob_table = prob_table


class DiscreteFactor(Factor):
    """Discrete factor representation with basic operations."""

    def _factor_table_length(self, cardinalities):
        """Length of the factor table (number of assignments)."""
        return reduce(operator.mul, cardinalities.values())

    def _compute_strides(self, variables, cardinalities, factor_length):
        """Strides for variables of given factor table.

        Compute a stride for each variable. For example there are three
        variables A, B, and C with cardinalities 2, 3, and 4. The length of
        factor is 2 * 3 * 4 = 24. To get from assignment A = 0 to A = 1, we
        have to go over 3 * 4 values: 000, 001, 002, 003, 010, ..., 023, 100.
        As a result, the strides of A, B, and C will be 12, 4, 1.
        """
        strides = {}
        last_stride = factor_length
        for variable in variables:
            last_stride = last_stride / cardinalities[variable]
            strides[variable] = last_stride
        return strides

    def _get_index_from_assignment(self, assignment):
        """Transform variables assignment to index into factor table."""
        index = 0
        for var, assignment_i in zip(self.variables, assignment):
            index += (self.strides[var] *
                      self.translation_table[var][assignment_i])
        return index

    def _get_assignment_from_index(self, index, chosen_vars=None):
        """Get assignment from factor table at given index."""
        if chosen_vars is None:
            chosen_vars = self.variables

        assignment = []
        for var in self.variables:
            if var in chosen_vars:
                assignment.append(self.variable_values[var][index / self.strides[var]])
            index %= self.strides[var]
        return tuple(assignment)

    def _create_translation_table(self):
        """Create translation from string values to numbers.

        Variable values can be anything, but arrays are indexed by
        numbers. Translation table is used for getting an index from an
        assignment.

        For example for a variable X with values ['a', 'b', 'c', 'd'], the
        translation will be: 'a': 0, 'b': 1, 'c': 2, 'd': 3.
        """
        self.translation_table = {}
        for var in self.variables:
            self.translation_table[var] = {}
            for i, value in enumerate(self.variable_values[var]):
                self.translation_table[var][value] = i

    def __init__(self, variables, variable_values, prob_table):
        super(DiscreteFactor, self).__init__(variables,
                                             variable_values,
                                             prob_table)
        # Create translation table from variable values to indexes.
        self._create_translation_table()
        # Compute cardinalities.
        self.cardinalities = {var: len(variable_values[var])
                              for var in self.variables}

        # If prob_table is np.ndarray, than we expect it to be in log form.
        if isinstance(prob_table, np.ndarray):
            self.factor_table = prob_table
            self.factor_length = self.factor_table.size
        elif isinstance(prob_table, dict):
            self.factor_length = self._factor_table_length(self.cardinalities)
            self.factor_table = np.ndarray(self.factor_length, np.float32)

        # Compute strides (how many elements in the prob table we have to skip
        # to get a new assignment of a variable).
        self.strides = self._compute_strides(self.variables,
                                             self.cardinalities,
                                             self.factor_length)

        if isinstance(prob_table, dict):
            # Save values from dictionary.
            for assignment, value in prob_table.iteritems():
                self.factor_table[
                    self._get_index_from_assignment(assignment)] = value
            # Convert values to log form.
            to_log(self.factor_table, self.factor_table)

        # Save the factor table in case we'll modify it with observation.
        self.unobserved_factor_table = self.factor_table

    def __str__(self, width=79):
        ret = ""
        num_columns = len(self.variables) + 1
        column_len = width / num_columns
        format_str = "{:^%d}" % column_len

        ret += width * "-" + "\n"

        for var in self.variables:
            ret += format_str.format(var)
        ret += format_str.format("Value") + "\n"
        ret += width * "-" + "\n"

        for i in range(len(self.factor_table)):
            for assignment in self._get_assignment_from_index(i):
                ret += format_str.format(assignment)
            ret += format_str.format(from_log(self.factor_table[i])) + "\n"

        ret += width * "-" + "\n"
        return ret

    def __iter__(self):
        for i, v in enumerate(self.factor_table):
            yield (self._get_assignment_from_index(i),
                   from_log(v))

    def marginalize(self, variables):
        """Marginalize the factor."""
        # Assignment counter
        assignment = defaultdict(int)
        # New cardinalities and new factor table.
        new_cardinalities = {x: self.cardinalities[x] for x in variables}
        new_factor_length = self._factor_table_length(new_cardinalities)
        new_factor_table = np.empty(new_factor_length, np.float32)
        new_factor_table[:] = np.log(ZERO)
        # Strides for resulting variables in the new factor table.
        new_strides = self._compute_strides(variables,
                                            self.cardinalities,
                                            new_factor_length)
        # Index into the new factor table.
        index = 0

        # Iterate over every element in the old factor table and add them to
        # the correct element in the new factor table.
        for i in range(self.factor_length):
            new_factor_table[index] = np.logaddexp(new_factor_table[index],
                                                   self.factor_table[i])

            # Update the assignment and indexes.
            for var in variables:
                # The assignment of variable var changed, so we must add its
                # stride to the index.
                if (i+1) % self.strides[var] == 0:
                    assignment[var] += 1
                    index += new_strides[var]
                # The assignment of variable var overflowed to 0, we must
                # subtract the cardinality from index.
                if assignment[var] == self.cardinalities[var]:
                    assignment[var] = 0
                    index -= (self.cardinalities[var] *
                              new_strides[var])

        # Return new factor with marginalized variables.
        new_variable_values = {v: self.variable_values[v] for v in variables}
        return DiscreteFactor(variables, new_variable_values, new_factor_table)

    def observed(self, assignment_dict):
        """Set observation."""
        if assignment_dict is not None:
            self.factor_table = np.empty(self.factor_length)
            self.factor_table[:] = np.log(ZERO)
            for assignment, value in assignment_dict.iteritems():
                self.factor_table[
                    self._get_index_from_assignment(assignment)] = to_log(value)
        else:
            self.factor_table = self.unobserved_factor_table

    def __getitem__(self, assignment):
        index = self._get_index_from_assignment(assignment)
        return from_log(self.factor_table[index])

    def __pow__(self, value):
        return DiscreteFactor(self.variables,
                              self.variable_values,
                              self.factor_table * value)

    def multiply_by_converted(self, other_factor, convert):
        new_factor_table = self.factor_table.copy()
        for index, value in enumerate(self.factor_table):
            assignment = self._get_assignment_from_index(index)
            converted_assignment = convert(assignment)
            other_index = other_factor._get_index_from_assignment(converted_assignment)
            new_factor_table[index] += other_factor.factor_table[other_index]
        return DiscreteFactor(self.variables, self.variable_values,
                              new_factor_table)

    def _multiply_same(self, other_factor):
        """Multiply two factors with same variables."""
        return DiscreteFactor(self.variables,
                              self.variable_values,
                              self.factor_table + other_factor.factor_table)

    def _multiply_different(self, other_factor):
        """Multiply two factors with different variables."""
        # The new set of variables will contain variables from both factors.
        new_variables = sorted(
            set(self.variables).union(other_factor.variables))
        # New cardinalities will contain cardinalities of all variables.
        new_cardinalities = dict(self.cardinalities)
        new_cardinalities.update(other_factor.cardinalities)
        # The new factor table will be larger, because it will contain more
        # variables.
        new_factor_length = self._factor_table_length(new_cardinalities)
        # The new factor table.
        new_factor_table = np.empty(new_factor_length, np.float32)

        # Assignment in new factor table.
        assignment = defaultdict(int)
        # Indexes into factor tables.
        index_self = 0
        index_other = 0
        reversed_variables = new_variables[::-1]

        for i in range(new_factor_length):
            # Multiply values from input factors to get new factor.
            new_factor_table[i] = (self.factor_table[index_self] +
                                   other_factor.factor_table[index_other])

            # Update the assignment and indexes.
            for var in reversed_variables:
                # Last variable has stride 1 and always changes it's value.
                assignment[var] += 1
                # The assignment of var overflowed to 0?
                if assignment[var] == new_cardinalities[var]:
                    assignment[var] = 0
                    # Move indexes in tables to correct assignment.
                    index_self -= ((new_cardinalities[var] - 1) *
                                   self.strides.get(var, 0))
                    index_other -= ((new_cardinalities[var] - 1) *
                                    other_factor.strides.get(var, 0))
                else:
                    # var is the last variable that changed.
                    index_self += self.strides.get(var, 0)
                    index_other += other_factor.strides.get(var, 0)
                    break

        new_variable_values = dict(self.variable_values)
        new_variable_values.update(other_factor.variable_values)

        return DiscreteFactor(new_variables,
                              new_variable_values,
                              new_factor_table)

    def __mul__(self, other_factor):
        if self.variables == other_factor.variables:
            return self._multiply_same(other_factor)
        else:
            return self._multiply_different(other_factor)

    def _divide_same(self, other_factor):
        """Divide factor by other factor with same variables."""
        return DiscreteFactor(self.variables,
                              self.variable_values,
                              self.factor_table - other_factor.factor_table)

    def _divide_different(self, other_factor):
        """Divide factor by other factor with less variables."""
        new_factor_table = np.empty_like(self.factor_table)
        assignment = defaultdict(int)
        index_other = 0
        reversed_variables = self.variables[::-1]

        for i in range(self.factor_length):
            new_factor_table[i] = (self.factor_table[i] -
                                   other_factor.factor_table[index_other])

            for var in reversed_variables:
                assignment[var] += 1
                if assignment[var] == self.cardinalities[var]:
                    assignment[var] = 0
                    index_other -= ((self.cardinalities[var] - 1) *
                                    other_factor.strides.get(var, 0))
                else:
                    index_other += other_factor.strides.get(var, 0)
                    break

        return DiscreteFactor(self.variables,
                              self.variable_values,
                              new_factor_table)

    def __div__(self, other_factor):
        if not set(self.variables).issuperset(set(other_factor.variables)):
            raise ValueError(
                "The denominator is not a subset of the numerator.")

        if self.variables == other_factor.variables:
            return self._divide_same(other_factor)
        else:
            return self._divide_different(other_factor)

    def subtract_superset(self, other):
        """Subtract other factor while broadcasting dimenstions of this factor.

        This is a helper function, we want to subtract from this factor, but
        the variables in this factor are a subset of variables in the other
        factor, we need to broadcast the dimensions of this factor first.

        Note: Used only for computing with parameters in dirichlet distribution.

        Example:
        A:
        x0  |   val
        0   |   5
        1   |   3

        B:
        x0  |   x1  |   val
        0   |   0   |   1
        0   |   1   |   2
        1   |   0   |   1
        1   |   1   |   0.5

        A.subtract_from_self_other_larger(B):
        x0  |   x1  |   val
        0   |   0   |   4
        0   |   1   |   3
        1   |   0   |   2
        1   |   1   |   2.5

        Fixme: The subtraction is done naively. It is possible to do it better
        without exponentiating the values first.
        """
        new_factor_table = np.empty_like(other.factor_table)
        for i in range(other.factor_length):
            assignment = other._get_assignment_from_index(i, self.variables)
            index = self._get_index_from_assignment(assignment)
            self_value = self.factor_table[index]
            other_value = other.factor_table[i]
            new_factor_table[i] = to_log(np.exp(self_value) - np.exp(other_value))
        return DiscreteFactor(other.variables, other.variable_values, new_factor_table)

    def normalize(self, parents=None):
        """Normalize factor table."""
        if parents is not None:
            sums = defaultdict(lambda: np.log(ZERO))
            assignments = {}

            for i, value in enumerate(self.factor_table):
                assignments[i] = self._get_assignment_from_index(i, parents)
                sums[assignments[i]] = np.logaddexp(sums[assignments[i]], value)

            for i in range(self.factor_length):
                self.factor_table[i] -= sums[assignments[i]]
        else:
            self.factor_table -= logsumexp(self.factor_table)

    def most_probable(self, n=None):
        indxs = list(reversed(np.argsort(self.factor_table)))[:n]
        return [(self._get_assignment_from_index(i)[0],
                 from_log(self.factor_table[i])) for i in indxs]

    def add(self, n, assignment=None):
        if assignment is not None:
            index = self._get_index_from_assignment(assignment)
            self.factor_table[index] = np.logaddexp(self.factor_table[index], to_log(n))
        else:
            for i in range(self.factor_length):
                self.factor_table[i] = np.logaddexp(self.factor_table[i], to_log(n))