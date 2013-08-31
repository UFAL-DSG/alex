#!/usr/bin/env python
# -*- coding: utf8 -*-

"""
This module implements a factor class, which can be used to do computations
with probability distributions.
"""

import numpy as np
import operator

from collections import defaultdict
from scipy.misc import logsumexp

ZERO = 1e-20


def to_log(n, out=None):
    """Convert number to log arithmetic.

    We want to be able to represent zero, therefore every number smaller than
    epsilon is considered a zero.

    :param n: Number to be converted.
    :type n: number or array like
    :param out: Output array.
    :type out: ndarray
    :returns: Number in log arithmetic.
    :rtype: number or array like
    """
    if np.isscalar(n):
        return np.log(ZERO, out) if n < ZERO else np.log(n, out)
    else:
        n[n < ZERO] = ZERO
        return np.log(n, out)


def from_log(n):
    """Convert number from log arithmetic.

    :param n: Number to be converted from log arithmetic.
    :type n: number or array like
    :returns: Number in decimal scale.
    :rtype: number or array like
    """
    return np.exp(n)


@np.vectorize
def logsubexp(a, b):
    """Subtract one number from another in log arithmetic.

    :param a: Minuend.
    :type a: number or array like
    :param b: Subtrahend.
    :type b: number or array like
    :returns: Difference.
    :rtype: number or array like
    """
    if a < b:
        raise Exception("Computing the log of a negative number.")
    elif a == b:
        return np.log(ZERO)
    return a + np.log1p(-np.exp(b - a))


class FactorError(Exception):
    pass


class Factor(object):
    """Basic factor."""

    def __add__(self, other):
        return self._apply_op(other, self._add)

    def __div__(self, other):
        return self._apply_op(other, self._div)

    def __getitem__(self, assignment):
        """Return the value of a given assignment.

        :param assignment: Assignment of variables whose value should be returned.
        :type assignment: tuple
        :returns: Value in table at assignment.
        :rtype: float
        """
        index = self._get_index_from_assignment(assignment)
        return self._decode(self.factor_table[index])

    def __init__(self, variables, variable_values, prob_table, logarithmetic=True):
        """Create a new factor.

        Needs a list of variables, because assignments must be in the same
        order. Variable values are used to compute properties of variables,
        like their cardinalities. Probability table must contain a value for
        each possible assignment of variables. They key must always be a tuple,
        this can be tricky, when there is only one variable.

        Example:

            >>> f = Factor(
            ...     ['A', 'B'],
            ...     {
            ...         'A': ['a1', 'a2'],
            ...         'B': ['b1', 'b2'],
            ...     },
            ...     {
            ...         ('a1', 'b1'): 0.8,
            ...         ('a2', 'b1'): 0.2,
            ...         ('a1', 'b2'): 0.7,
            ...         ('a2', 'b2'): 0.3,
            ...     })

        :param variables: Variables in the domain of this factor.
        :type variables: list
        :param variable_values: Dictionary containing for each variable a list of possible values.
        :type variable_values: dict
        :param prob_table: Probality table, contains a value for each possible assignment.
        """
        self.variables = variables
        self.variable_values = variable_values

        self.logarithmetic = logarithmetic
        if logarithmetic:
            self._add = np.logaddexp
            self._sub = logsubexp
            self._mul = np.add
            self._div = np.subtract
            self._pow = np.multiply
            self._encode = to_log
            self._decode = from_log
            self._zero = np.log(ZERO)
            self._sum = logsumexp
        else:
            self._add = np.add
            self._sub = np.subtract
            self._mul = np.multiply
            self._div = np.divide
            self._pow = np.power
            self._encode = lambda x: x
            self._decode = lambda x: x
            self._zero = ZERO
            self._sum = np.sum

        # Create a translation table from variable values to indexes.
        self._create_translation_table()

        # Compute cardinalities.
        self.cardinalities = {var: len(variable_values[var])
                              for var in self.variables}

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

        # Save the values if the prob_table is a dictionary.
        if isinstance(prob_table, dict):
            for assignment, value in prob_table.iteritems():
                self.factor_table[
                    self._get_index_from_assignment(assignment)] = value

            # Convert values to log form.
            self.factor_table = self._encode(self.factor_table)

        # Save the factor table in case we'll modify it with observation.
        self.unobserved_factor_table = np.array(self.factor_table)

    def __iter__(self):
        """Iterate over assignments and values.

        Each element is a tuple, where the first element is the assignment
        and the second element is the probability of this assignment.

        Example of an element is ``(("a", "b", "c"), 0.8)``.

        :rtype: (tuple, float)
        """
        for i in range(self.factor_length):
            v = self.factor_table[i]
            yield (self._get_assignment_from_index(i),
                   self._decode(v))

    def __mul__(self, other):
        return self._apply_op(other, self._mul)

    def __pow__(self, other):
        return self._apply_op(other, self._pow)

    def __setitem__(self, assignment, value):
        """Set a value.

        :param assignment: Assignment of variables whose value should be changed.
        :type assignment: tuple
        :param value: The new value.
        :type value: number
        """
        index = self._get_index_from_assignment(assignment)
        self.factor_table[index] = self._encode(value)

    def __str__(self):
        """Convert a factor to a string representation."""
        return self.pretty_print()

    def __sub__(self, other):
        return self._apply_op(other, self._sub)

    def _apply_op(self, other, op):
        if np.isscalar(other):
            return self._apply_op_scalar(other, op)

        if self.logarithmetic != other.logarithmetic:
            raise FactorError('Factors must both use log arithmetic.')

        if self.variables == other.variables:
            return self._apply_op_same(other, op)
        else:
            return self._apply_op_different(other, op)

    def _apply_op_different(self, other, op):
        """
        Apply an operation on two factors, which don't have the same sets
        of variables.

        :param other: The other factor.
        :type other: :class:`Factor`
        :param op: Binary function.
        :return: The resulting factor.
        :rtype: :class:`Factor`
        """
        # New factor will have variables which are a union of variables from
        # this and other factor. They will be sorted because otherwise there
        # could exist two factors with same variables, but in different other.
        new_variables = sorted(
            set(self.variables).union(other.variables)
        )

        new_variable_values = dict(self.variable_values)
        new_variable_values.update(other.variable_values)

        # The cardinalities will stay the same, we just have to add
        # cardinalities for variables from both factors.
        new_cardinalities = dict(self.cardinalities)
        new_cardinalities.update(other.cardinalities)

        # Compute the length of new factor table.
        new_factor_length = self._factor_table_length(new_cardinalities)

        # Create a new factor table.
        new_factor_table = np.empty(new_factor_length, np.float32)

        assignment = defaultdict(int)
        index_self = 0
        index_other = 0
        reversed_variables = new_variables[::-1]

        for i in range(new_factor_length):
            # Apply the operator.
            new_factor_table[i] = op(self.factor_table[index_self],
                                     other.factor_table[index_other])

            # Update indexes, start with variable with smallest stride.
            for var in reversed_variables:
                # Move to next value of a variable.
                assignment[var] += 1
                # If we go past the last value of one variable, we need to
                # move onto next variable.
                if assignment[var] == new_cardinalities[var]:
                    assignment[var] = 0
                    index_self -= ((new_cardinalities[var] - 1) *
                                   self.strides.get(var, 0))
                    index_other -= ((new_cardinalities[var] - 1) *
                                    other.strides.get(var, 0))
                # Otherwise we just update this variable and don't have to do
                # anything with other variables.
                else:
                    index_self += self.strides.get(var, 0)
                    index_other += other.strides.get(var, 0)
                    break

        return Factor(new_variables,
                      new_variable_values,
                      new_factor_table,
                      self.logarithmetic)

    def _apply_op_same(self, other, op):
        """
        Apply an operation on two factors, which must have the same sets
        of variables.

        :param other: The other factor.
        :type other: :class:`Factor`
        :param op: Binary function.
        :return: The resulting factor.
        :rtype: :class:`Factor`
        """
        return Factor(self.variables,
                      self.variable_values,
                      op(self.factor_table, other.factor_table),
                      self.logarithmetic)

    def _apply_op_scalar(self, other, op):
        """
        Apply an operation on a factor and a scalar.

        :param other: The other operand.
        :type other: number
        :param op: Binary function.
        :return: The resulting factor.
        :rtype: :class:`Factor`
        """
        if op != self._pow:
            other = self._encode(other)

        return Factor(self.variables,
                      self.variable_values,
                      op(self.factor_table, other),
                      self.logarithmetic)

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

    def _create_translation_table(self):
        """Create a translation from string values to numbers.

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

    def _factor_table_length(self, cardinalities):
        """Length of the factor table (number of assignments)."""
        return reduce(operator.mul, cardinalities.values())

    def _get_assignment_from_index(self, index, chosen_vars=None):
        """Get assignment from a factor table at given index."""
        if chosen_vars is None:
            chosen_vars = self.variables

        assignment = []
        for var in self.variables:
            if var in chosen_vars:
                assignment.append(self.variable_values[var][index / self.strides[var]])
            index %= self.strides[var]
        return tuple(assignment)

    def _get_index_from_assignment(self, assignment):
        """Transform variables assignment to index into factor table."""
        index = 0
        for var, assignment_i in zip(self.variables, assignment):
            index += (self.strides[var] *
                      self.translation_table[var][assignment_i])
        return index

    def marginalize(self, keep):
        """Marginalize all but specified variables.

        Marginalizing means summing out values which are not in `keep`. The
        result is a new factor, which contains only variables from `keep`.

        Example:

            >>> f = Factor(['A', 'B'],
            ...                    {'A': ['a1', 'a2'], 'B': ['b1', 'b2']},
            ...                    {
            ...                         ('a1', 'b1'): 0.8,
            ...                         ('a2', 'b1'): 0.2,
            ...                         ('a1', 'b2'): 0.3,
            ...                         ('a2', 'b2'): 0.7
            ...                    })
            >>> result = f.marginalize(['A'])
            >>> print result.pretty_print(width=30)
            ------------------------------
                   A            Value
            ------------------------------
                  a1             1.1
                  a2             0.9
            ------------------------------

        :param keep: Variables which should be left in marginalized factor.
        :type keep: list of str
        :returns: Marginalized factor.
        :rtype: :class:`Factor`

        """
        # Assignment counter
        assignment = defaultdict(int)
        # New cardinalities and new factor table.
        new_cardinalities = {x: self.cardinalities[x] for x in keep}
        new_factor_length = self._factor_table_length(new_cardinalities)
        new_factor_table = np.empty(new_factor_length, np.float32)
        new_factor_table[:] = self._zero
        # Strides for resulting variables in the new factor table.
        new_strides = self._compute_strides(keep,
                                            self.cardinalities,
                                            new_factor_length)
        # Index into the new factor table.
        index = 0

        # Iterate over every element in the old factor table and add them to
        # the correct element in the new factor table.
        for i in range(self.factor_length):
            new_factor_table[index] = self._add(new_factor_table[index],
                                                self.factor_table[i])

            # Update the assignment and indexes.
            for var in keep:
                # The assignment of variable var changed, so we must add its
                # stride to the index.
                if (i + 1) % self.strides[var] == 0:
                    assignment[var] += 1
                    index += new_strides[var]
                # The assignment of variable var overflowed to 0, we must
                # subtract the cardinality from index.
                if assignment[var] == self.cardinalities[var]:
                    assignment[var] = 0
                    index -= (self.cardinalities[var] *
                              new_strides[var])

        # Return new factor with marginalized variables.
        new_variable_values = {v: self.variable_values[v] for v in keep}
        return Factor(keep, new_variable_values, new_factor_table, self.logarithmetic)

    def most_probable(self, n=None):
        """Return a list of most probable assignments from the table.

        Returns a sorted list of assignment and their values according to
        their probability. The size of the list can be changed by specifying
        n.

        :param n: The number of most probable elements, which should be returned.
        :type n: int
        :returns: A list of tuples (assignment, value) in descending order.
        :rtype: list of (tuple, float)
        """
        indxs = list(reversed(np.argsort(self.factor_table)))[:n]
        return [(self._get_assignment_from_index(i)[0],
                 self._decode(self.factor_table[i])) for i in indxs]

    def normalize(self, parents=None):
        """Normalize a factor table.

        The table is normalized so all elements sum to one.
        The parents argument is a list of names of parents. If it is
        specified, then only those rows in table, which share the same
        parents, are normalized.

        Example:

            >>> f = Factor(['A', 'B'],
            ...                    {'A': ['a1', 'a2'], 'B': ['b1', 'b2']},
            ...                    {
            ...                         ('a1', 'b1'): 3,
            ...                         ('a1', 'b2'): 1,
            ...                         ('a2', 'b1'): 1,
            ...                         ('a2', 'b2'): 1,
            ...                    })
            >>> f.normalize(parents=['B'])
            >>> print f.pretty_print(width=30)
            ------------------------------
                A         B       Value
            ------------------------------
                a1        b1       0.75
                a1        b2       0.5
                a2        b1       0.25
                a2        b2       0.5
            ------------------------------

        :param parents: Parents of the factor.
        :type parents: list
        """
        if parents is not None:
            sums = defaultdict(lambda: self._zero)
            assignments = {}

            for i in range(self.factor_length):
                value = self.factor_table[i]
                assignments[i] = self._get_assignment_from_index(i, parents)
                sums[assignments[i]] = self._add(sums[assignments[i]], value)

            for i in range(self.factor_length):
                self.factor_table[i] = self._div(self.factor_table[i], sums[assignments[i]])
        else:
            self.factor_table = self._div(self.factor_table, self._sum(self.factor_table))

    def observed(self, assignment_dict):
        """Set observation.

        Example:

            >>> f = Factor(
            ...     ['X'],
            ...     {
            ...         'X': ['x0', 'x1'],
            ...     },
            ...     {
            ...         ('x0',): 0.5,
            ...         ('x1',): 0.5,
            ...     })
            >>> print f.pretty_print(width=30, precision=3)
            ------------------------------
                   X            Value
            ------------------------------
                  x0             0.5
                  x1             0.5
            ------------------------------
            >>> f.observed({('x0',): 0.8, ('x1',): 0.2})
            >>> print f.pretty_print(width=30, precision=3)
            ------------------------------
                   X            Value
            ------------------------------
                  x0             0.8
                  x1             0.2
            ------------------------------

        :param assignment_dict: Observed values for different assignments of values or None.
        :type assignment_dict: dict or None
        """
        if assignment_dict is not None:
            # Clear the factor table.
            self.factor_table[:] = self._zero
            for assignment, value in assignment_dict.iteritems():
                self.factor_table[
                    self._get_index_from_assignment(assignment)] = self._encode(value)
        else:
            self.factor_table[:] = self.unobserved_factor_table

    def pretty_print(self, width=79, precision=10):
        """Create a readable representation of the factor.

        Creates a table with a column for each variable and value. Every row
        represents one assignemnt and its corresponding value. The default
        width of the table is 79 chars, to fit to terminal window.

        :param width: Width of the table.
        :type width: int
        :param precision: Precision of values.
        :type precision: int
        :returns: Pretty printed factor table.
        :rtype: str
        """
        ret = ""
        num_columns = len(self.variables) + 1
        column_len = width / num_columns
        format_str = "{:^%d}" % column_len
        value_str = "{:^%d.%d}" % (column_len, precision)

        ret += width * "-" + "\n"

        for var in self.variables:
            ret += format_str.format(var)
        ret += format_str.format("Value") + "\n"
        ret += width * "-" + "\n"

        for i in range(self.factor_length):
            for assignment in self._get_assignment_from_index(i):
                ret += format_str.format(assignment)
            ret += value_str.format(self._decode(self.factor_table[i])) + "\n"

        ret += width * "-" + "\n"
        return ret

    def rename_variables(self, mapping):
        for i in range(len(self.variables)):
            if self.variables[i] in mapping:
                old_variable = self.variables[i]
                new_variable = mapping[old_variable]
                self.variables[i] = new_variable

                self.variable_values[new_variable] = self.variable_values[old_variable]
                del self.variable_values[old_variable]

                self.strides[new_variable] = self.strides[old_variable]
                del self.strides[old_variable]

                self.cardinalities[new_variable] = self.cardinalities[old_variable]
                del self.cardinalities[old_variable]

                self.translation_table[new_variable] = self.translation_table[old_variable]
                del self.translation_table[old_variable]

    def sum_other(self):
        factor_sum = self._sum(self.factor_table)
        new_factor_table = self._sub(factor_sum, self.factor_table)
        return Factor(self.variables,
                      self.variable_values,
                      new_factor_table,
                      self.logarithmetic)