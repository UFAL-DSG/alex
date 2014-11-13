#!/usr/bin/env python
# coding=utf-8
#
# Classes related to Treex trees & nodes
#

from __future__ import unicode_literals
from alex.components.nlg.tectotpl.core.exception import RuntimeException
from alex.components.nlg.tectotpl.core.log import log_warn
from collections import deque
import types
import re
import sys
import inspect
from alex.components.nlg.tectotpl.core.util import as_list


__author__ = "Ondřej Dušek"
__date__ = "2012"


class Node(object):
    "Representing a node in a tree (recursively)"

    __lastId = 0
    # this holds attributes used for all nodes
    # (overridden in derived classes and used from get_attr_list)
    attrib = [('alignment', types.ListType), ('wild', types.DictType)]
    # this similarly holds a list of attributes that contain references
    # (to be overridden by derived classes)
    ref_attrib = []

    def __init__(self, data=None, parent=None, zone=None):
        "Constructor, can create a tree recursively"
        # create a dummy data dictionary if None is passed
        data = data or {}
        # upper level links
        self.__zone = zone or (parent and parent.zone) or None
        self.__document = self.zone and self.zone.document or None
        self.__parent = None
        self.parent = parent
        # set all attributes belonging to the current node class
        # (replace '.' with '_')
        for attr_type, safe_attr in zip(self.get_attr_list(include_types=True),
                                        self.get_attr_list(safe=True)):
            attr, att_type = attr_type
            # initialize lists and dicts, perform simple type coercion on other
            if att_type == types.DictType:
                setattr(self, safe_attr,
                        data.get(attr) is not None and dict(data[attr]) or {})
            elif att_type == types.ListType:
                setattr(self, safe_attr,
                        data.get(attr) is not None and list(data[attr]) or [])
            elif att_type == types.BooleanType:
                # booleans need to be prepared for values such as '1' and '0'
                setattr(self, safe_attr,
                        data.get(attr) is not None and
                            bool(int(data[attr])) or False)
            else:
                # other types (int,str): be prepared for values that evaluate
                # to false -- cannot use the and-or trick
                if data.get(attr) is not None:
                    val = att_type(data[attr])
                else:
                    val = None
                setattr(self, safe_attr, val)
        # set or generate id (will be indexed automatically; must be called
        # after attributes have been set due to references)
        self.id = data.get('id') or self.__generate_id()
        # create children (will add themselves to the list automatically)
        self.__children = []
        if ('children' in data):
            # call the right constructor for each child from data
            [self.create_child(data=child_data)
             for child_data in data['children']]

    def  __generate_id(self):
        "Generate successive IDs for all nodes"
        Node.__lastId += 1
        ret = re.sub(r'^.*\.', '', self.__class__.__name__.lower()) + '-node-'
        if self.zone:
            ret += self.zone.language_and_selector + '-'
            if self.zone.bundle:
                ret += 's' + str(self.zone.bundle.ord) + '-'
        ret += 'n' + str(Node.__lastId)
        return ret

    @staticmethod
    def __safe_name(attr):
        """Return a safe version of an attribute's name
        (mangle referencing attributes)."""
        if attr.endswith('.rf'):
            return '__' + re.sub(r'\.', '_', attr)
        return attr

    def __track_backref(self, name, value):
        """Track reverse references if the given attribute contains
        references (used by set_attr)"""
        # handle alignment as a special case
        if name == 'alignment':
            old_alignment = self.get_attr('alignment')
            if old_alignment:
                for reference in old_alignment:
                    self.document.remove_backref('alignment', self.id,
                                                 reference['counterpart.rf'])
            if value:
                for reference in value:
                    self.document.index_backref('alignment', self.id,
                                                reference['counterpart.rf'])
            return
        # test if the attribute contains references
        reference = self.get_ref_attr_list(split_nested=True).get(name)
        if not reference:
            return
        # normal case: value itself is a reference
        ref_keys = [name]
        ref_values = [value]
        # special case: value is a dict containing references
        if isinstance(reference, dict):
            ref_keys = [name + '/' + key for key in value if key in reference]
            ref_values = [value[key] for key in value if key in reference]
        # track all the references
        for ref_name, ref_value in zip(ref_keys, ref_values):
            old_value = self.get_attr(ref_name)
            self.document.remove_backref(ref_name, self.id, old_value)
            self.document.index_backref(ref_name, self.id, ref_value)

    def get_attr_list(self, include_types=False, safe=False):
        """Get attributes of the current class
        (gathering all attributes of base classes)"""
        # Caching for classes
        # (since the output is always the same for the same class)
        myclass = self.__class__
        if not hasattr(myclass, '__attr_list_cache'):
            myclass.__attr_list_cache = {}
        # Not in cache -- must compute
        if not (include_types, safe) in myclass.__attr_list_cache:
            mybases = inspect.getmro(myclass)
            attrs = [attr for cls in mybases if hasattr(cls, 'attrib') for attr in cls.attrib]
            if safe:
                attrs = [(Node.__safe_name(attr), atype)
                         for attr, atype in attrs]
            if not include_types:
                attrs = [attr for attr, atype in attrs]
            myclass.__attr_list_cache[(include_types, safe)] = attrs
        # Return the result from cache
        return myclass.__attr_list_cache[(include_types, safe)]

    def get_ref_attr_list(self, split_nested=False):
        """Return a list of the attributes of the current class that
        contain references (splitting nested ones, if needed)"""
        # Caching for classes
        # (since the output is always the same for the same class)
        myclass = self.__class__
        if not hasattr(myclass, '__ref_attr_cache'):
            myclass.__ref_attr_cache = {}
        # Not in cache -- must compute
        if not split_nested in self.__class__.__ref_attr_cache:
            mybases = inspect.getmro(myclass)
            attrs = [attr for cls in mybases if hasattr(cls, 'ref_attrib') for attr in cls.ref_attrib]
            if not split_nested:
                myclass.__ref_attr_cache[split_nested] = attrs
            else:
                # unwind the attributes to a dictionary
                attr_dict = {}
                for attr in attrs:
                    # always put True value for the whole path
                    attr_dict[attr] = True
                    # for nested values, put a nested dictionary in addition
                    if '/' in attr:
                        key, val = attr.split('/', 1)
                        if not isinstance(attr_dict.get(key), dict):
                            attr_dict[key] = {}
                        attr_dict[key][val] = True
                myclass.__ref_attr_cache[split_nested] = attr_dict
        # Return the result from cache
        return myclass.__ref_attr_cache[split_nested]

    def get_attr(self, name):
        """Return the value of the given attribute.
        Allows for dictionary nesting, e.g. 'morphcat/gender'"""
        if '/' in name:
            attr, path = name.split('/', 1)
            path = path.split('/')
            obj = getattr(self, Node.__safe_name(attr))
            for step in path:
                if type(obj) != dict:
                    return None
                obj = obj.get(step)
            return obj
        else:
            return getattr(self, Node.__safe_name(name))

    def set_attr(self, name, value):
        """Set the value of the given attribute.
        Allows for dictionary nesting, e.g. 'morphcat/gender'"""
        # handle referring attributes (keep track of backwards references)
        self.__track_backref(name, value)
        # any nested attributes
        if '/' in name:
            #prepare the attribute as a dict
            attr, path = name.split('/', 1)
            path = path.split('/')
            obj = getattr(self, Node.__safe_name(attr))
            if type(obj) != dict:
                obj = {}
                setattr(self, Node.__safe_name(attr), obj)
            # build dict path up to the last level
            for step in path[:-1]:
                if not step in obj:
                    obj[step] = {}
                obj = obj[step]
            #set the value
            obj[path[-1]] = value
        # plain attributes
        else:
            setattr(self, Node.__safe_name(name), value)

    def set_deref_attr(self, name, value):
        """This assumes the value is a node/list of nodes and
        sets its id/their ids as the value of the given attribute."""
        if type(value) == list:
            self.set_attr(name, [node.id for node in value])
        else:
            self.set_attr(name, value.id)

    def get_deref_attr(self, name):
        """This assumes the given attribute holds node id(s) and
        returns the corresponding node(s)"""
        value = self.get_attr(name)
        if type(value) == list:
            return [self.document.get_node_by_id(node_id) for node_id in value]
        elif value is not None:
            return self.document.get_node_by_id(value)
        return None

    def get_referenced_ids(self):
        """Return all ids referenced by this node, keyed under
        their reference types in a hash."""
        ret = {'alignment': []}
        for align in self.alignment:
            ret['alignment'].add(align['counterpart.rf'])
        for attr in self.get_ref_attr_list():
            value = self.get_attr(attr)
            if not value:
                continue
            ret[attr] = as_list(value)
        return ret

    def remove_reference(self, ref_type, refd_id):
        "Remove the reference of the given type to the given node."
        # handle alignment separately
        if ref_type == 'alignment':
            refs = self.get_attr('alignment')
            self.set_attr('alignment', [ref for ref in refs if
                                        ref['counterpart.rf'] != refd_id])
        # handle plain attributes and lists
        refs = self.get_attr(ref_type)
        if isinstance(refs, list):
            self.set_attr(ref_type, [ref for ref in refs if ref != refd_id])
        else:
            self.set_attr(ref_type, None)

    def get_descendants(self, add_self=False, ordered=False,
                        preceding_only=False, following_only=False):
        "Return all topological descendants of this node."
        return self._process_switches([desc for child in self.__children
                                       for desc in
                                       child.__descs_and_self_unsorted()],
                                       add_self, ordered, preceding_only,
                                       following_only)

    def get_children(self, add_self=False, ordered=False,
                     preceding_only=False, following_only=False):
        "Return all children of the node"
        return self._process_switches(list(self.__children), add_self, ordered,
                                      preceding_only, following_only)

    def __descs_and_self_unsorted(self):
        "Recursive function to return all descendants + self, in any order."
        return [self] + [desc for child in self.__children
                         for desc in child.__descs_and_self_unsorted()]

    def _process_switches(self, nodes, add_self, ordered,
                          preceding_only, following_only):
        """Process all variants on a node list:
        add self, order, filter out only preceding or only following ones."""
        if preceding_only and following_only:
            raise RuntimeException('Cannot return preceding_only ' +
                                   'and following_only nodes')
        if preceding_only or following_only:
            ordered = True
        if add_self:
            nodes.append(self)
        # filtering
        if preceding_only:
            nodes = filter(lambda node: node < self, nodes)
        elif following_only:
            nodes = filter(lambda node: node > self, nodes)
        # sorting
        if ordered:
            nodes.sort()
        return nodes

    def create_child(self, id=None, data=None):
        "Create a child of the current node"
        if id:
            data = data and data or {}
            data['id'] = id
        return getattr(sys.modules[__name__],
                       self.__class__.__name__)(data=data, parent=self)

    def remove(self):
        "Remove the node from the tree."
        if self.get_children():
            raise RuntimeException('Cannot remove a node with children:' +
                                   self.id)
        self.parent = None
        self.document.remove_node(self.id)

    @property
    def root(self):
        "The root of the tree this node is in."
        return self.__root

    @property
    def document(self):
        "The document this node is a member of."
        return self.__document

    @property
    def parent(self):
        "The parent of the current node. None for roots."
        return self.__parent

    @parent.setter
    def parent(self, value):
        "Change the parent of the current node."
        # TODO possibly implement moving across documents
        # (would require new ID indexing)
        if value is not None and self.__document != value.__document:
            raise RuntimeException('Cannot move nodes across documents.')
        # filter original parent's children
        if self.__parent:
            self.__parent.__children = [child for child
                                        in self.__parent.__children
                                        if child != self]
        # set new parent and update its children, set new root
        self.__parent = value
        if self.__parent:
            self.__parent.__children.append(self)
            self.__root = self.__parent.__root
        else:
            self.__root = self

    def get_depth(self):
        "Return the depth, i.e. the distance to the root."
        node = self
        depth = 0
        while node:
            node = node.parent
            depth += 1
        return depth

    @property
    def id(self):
        "The unique id of the node within the document."
        return self.__id

    @id.setter
    def id(self, value):
        self.__id = value
        if self.__document:
            self.__document.index_node(self)

    @property
    def zone(self):
        "The zone this node belongs to."
        return self.__zone

    @property
    def is_root(self):
        """Return true if this node is a root"""
        return self.parent is None

    def __eq__(self, other):
        "Node comparison by id"
        return self.id == other.id

    def __ne__(self, other):
        "Node comparison by id"
        return self.id != other.id

    def __lt__(self, other):
        "Node ordering is only implemented in Ordered"
        if not isinstance(self, Ordered) or not isinstance(other, Ordered):
            return NotImplemented
        return Ordered.__lt__(self, other)

    def __gt__(self, other):
        "Node ordering is only implemented in Ordered"
        if not isinstance(self, Ordered) or not isinstance(other, Ordered):
            return NotImplemented
        return Ordered.__gt__(self, other)

    def __le__(self, other):
        "Node ordering is only implemented in Ordered"
        if not isinstance(self, Ordered) or not isinstance(other, Ordered):
            return NotImplemented
        return Ordered.__le__(self, other)

    def __ge__(self, other):
        "Node ordering is only implemented in Ordered"
        if not isinstance(self, Ordered) or not isinstance(other, Ordered):
            return NotImplemented
        return Ordered.__ge__(self, other)


class Ordered(object):
    """\
    Representing an ordered node (has an attribute called ord),
    defines sorting.
    """

    attrib = [('ord', types.IntType)]
    ref_attrib = []

    def __lt__(self, other):
        return self.ord < other.ord

    def __gt__(self, other):
        return self.ord > other.ord

    def __le__(self, other):
        return self.ord <= other.ord

    def __ge__(self, other):
        return self.ord >= other.ord

    def shift_after_node(self, other, without_children=False):
        "Shift one node after another in the ordering."
        self.__shift_to_node(other, after=True)

    def shift_before_node(self, other, without_children=False):
        "Shift one node before another in the ordering."
        self.__shift_to_node(other, after=False)

    def shift_before_subtree(self, other, without_children=False):
        """\
        Shift one node before the whole subtree of another node
        in the ordering.
        """
        subtree = other.get_descendants(ordered=True, add_self=True)
        if len(subtree) <= 1 and self == other:
            return  # no point if self==other and there are no children
        self.__shift_to_node(subtree[0] == self and subtree[1] or subtree[0],
                             after=False)

    def shift_after_subtree(self, other, without_children=False):
        """\
        Shift one node after the whole subtree of another node in the ordering.
        """
        subtree = other.get_descendants(ordered=True, add_self=True)
        if len(subtree) <= 1 and self == other:
            return   # no point if self==other and there are no children
        self.__shift_to_node(subtree[-1] == self
                             and subtree[-2] or subtree[-1], after=True)

    def __shift_to_node(self, other, after, without_children=False):
        "Shift a node before or after another node in the ordering"
        all_nodes = self.root.get_descendants(ordered=True, add_self=True)
        # determine what's being moved
        to_move = [self] if without_children else self.get_descendants(ordered=True, add_self=True)
        moving = set(to_move)
        # do the moving
        cur_ord = 0
        for node in all_nodes:
            # skip nodes moved, handle them when we're at the reference node
            if node in moving:
                continue
            if after:
                node.ord = cur_ord
                cur_ord += 1
            # we're at the target node, move all needed
            if node == other:
                for moving_node in to_move:
                    moving_node.ord = cur_ord
                    cur_ord += 1
            if not after:
                node.ord = cur_ord
                cur_ord += 1

    def get_next_node(self):
        "Get the following node in the ordering."
        my_ord = self.ord
        next_ord, next_node = (None, None)
        for node in self.root.get_descendants():
            cur_ord = node.ord
            if cur_ord <= my_ord:
                continue
            if next_ord is not None and cur_ord > next_ord:
                continue
            next_ord, next_node = (cur_ord, node)
        return next_node

    def get_prev_node(self):
        "Get the preceding node in the ordering."
        my_ord = self.ord
        prev_ord, prev_node = (None, None)
        for node in self.root.get_descendants():
            cur_ord = node.ord
            if cur_ord >= my_ord:
                continue
            if prev_ord is not None and cur_ord < prev_ord:
                continue
            prev_ord, prev_node = (cur_ord, node)
        return prev_node

    def is_first_node(self):
        """\
        Return True if this node is the first node in the tree,
        i.e. has no previous nodes.
        """
        prev_node = self.get_prev_node()
        return prev_node is None

    def is_last_node(self):
        """\
        Return True if this node is the last node in the tree,
        i.e. has no following nodes.
        """
        next_node = self.get_next_node()
        return next_node is None

    @property
    def is_right_child(self):
        """Return True if this node has a greater ord than its parent. Returns None for a root."""
        if self.parent is None:
            return None
        return self.parent.ord < self.ord


class EffectiveRelations(object):
    "Representing a node with effective relations"

    attrib = [('is_member', types.BooleanType)]
    ref_attrib = []

    def is_coap_root(self):
        """\
        Testing whether the node is a coordination/apposition root.
        Must be implemented in descendants.
        """
        raise NotImplementedError

    # TODO: dive ~ subroutine / auxcp
    def get_echildren(self, or_topological=False,
                      add_self=False, ordered=False,
                      preceding_only=False, following_only=False):
        "Return the effective children of the current node."
        # test if we can get e-children
        if not self.__can_apply_eff(or_topological):
            return self.get_children(add_self, ordered,
                                     preceding_only, following_only)
        # my own effective children
        # (I am their only parent) & shared effective children
        echildren = self.__get_my_own_echildren() + \
                    self.__get_shared_echildren()
        # final filtering
        return self._process_switches(echildren, add_self, ordered,
                                      preceding_only, following_only)

    def __can_apply_eff(self, or_topological):
        """Return true if the given node is OK for effective relations
        to be applied, false otherwise."""
        if self.is_coap_root():
            caller_name = inspect.stack()[1][3]
            message = caller_name + ' called on coap_root (' + self.id + ').'
            if or_topological:
                return False
            else:
                # this should not happen, so warn about it
                log_warn(message + ' Fallback to topological.')
                return False
        return True

    def __get_my_own_echildren(self):
        "Return the e-children of which this node is the only parent."
        echildren = []
        for node in self.get_children():
            if node.is_coap_root():
                echildren.extend(node.get_coap_members())
            else:
                echildren.append(node)
        return echildren

    def __get_shared_echildren(self):
        "Return e-children this node shares with other node(s)"
        coap_root = self.__get_direct_coap_root()
        if not coap_root:
            return []
        echildren = []
        while coap_root:
            # add all shared children and go upwards
            echildren += [coap_member for node in coap_root.get_children()
                          if not node.is_member
                          for coap_member in node.get_coap_members()]
            coap_root = coap_root.__get_direct_coap_root()
        return echildren

    def __get_direct_coap_root(self):
        "Return the direct coap root."
        if self.is_member:
            return self.parent
        return None

    def get_coap_members(self):
        """Return the members of the coordination, if the node is a coap root.
        Otherwise return the node itself."""
        if not self.is_coap_root():
            return [self]
        queue = deque(filter(lambda node: node.is_member, self.get_children()))
        members = []
        while queue:
            node = queue.popleft()
            if node.is_coap_root():
                queue.extend(filter(lambda node: node.is_member,
                                    node.get_children()))
            else:
                members.append(node)
        return members

    def get_eparents(self, or_topological=False,
                     add_self=False, ordered=False,
                     preceding_only=False, following_only=False):
        "Return the effective parents of the current node."
        # test if we can get e-parents
        if not self.__can_apply_eff(or_topological):
            return [self.parent]
        return self._process_switches(self.__get_eparents(), add_self,
                                      ordered, preceding_only, following_only)

    def __get_eparents(self):
        if not self.parent:
            log_warn("Cannot find parents, using the root: " + self.id)
            return [self.root]
        # try getting coap root, if applicable
        node = self.__get_transitive_coap_root() or self
        # continue to parent
        node = node.parent
        if not node:
            return [self.__fallback_parent()]
        # if we are not in coap, return just the one node
        if not node.is_coap_root:
            return [node]
        # we are in a coap -> return members
        eff = node.get_coap_members()
        if eff:
            return eff
        return [self.__fallback_parent()]

    def __get_transitive_coap_root(self):
        "Climb up a nested coap structure and return its root."
        root = self.__get_direct_coap_root()
        if not root:
            return None
        while root.is_member:
            root = root.__get_direct_coap_root()
            if not root:
                return None
        return root

    def __fallback_parent(self):
        "Issue a warning and return the topological parent."
        log_warn("No effective parent, using topological: " + self.id)
        return self.parent


class InClause(object):
    "Represents nodes that are organized in clauses"

    attrib = [('clause_number', types.IntType),
              ('is_clause_head', types.BooleanType)]
    ref_attrib = []

    def get_clause_root(self):
        "Return the root of the clause the current node resides in."
        # default to self if clause number is not defined
        if self.clause_number is None:
            log_warn('Clause number undefined in: ' + self.id)
            return self
        highest = self
        parent = self.parent
        # move as high as possible within the clause
        while parent and parent.clause_number == self.clause_number:
            highest = parent
            parent = parent.parent
        # handle coordinations - shared attributes
        if parent and parent.is_coap_root() and not highest.is_member:
            try:
                eff_parent = next(child for child in parent.get_children()
                                  if child.is_member and
                                  child.clause_number == self.clause_number)
                return eff_parent
            except StopIteration:  # no eff_parent found
                pass
        return highest


class T(Node, Ordered, EffectiveRelations, InClause):
    "Representing a t-node"

    attrib = [('functor', types.UnicodeType), ('formeme', types.UnicodeType),
              ('t_lemma', types.UnicodeType), ('nodetype', types.UnicodeType),
              ('subfunctor', types.UnicodeType), ('tfa', types.UnicodeType),
              ('is_dsp_root', types.BooleanType), ('gram', types.DictType),
              ('a', types.DictType), ('compl.rf', types.ListType),
              ('coref_gram.rf', types.ListType),
              ('coref_text.rf', types.ListType),
              ('sentmod', types.UnicodeType),
              ('is_parenthesis', types.BooleanType),
              ('is_passive', types.BooleanType),
              ('is_generated', types.BooleanType),
              ('is_relclause_head', types.BooleanType),
              ('is_name_of_person', types.BooleanType),
              ('voice', types.UnicodeType), ('mlayer_pos', types.UnicodeType),
              ('t_lemma_origin', types.UnicodeType),
              ('formeme_origin', types.UnicodeType),
              ('is_infin', types.BooleanType),
              ('is_reflexive', types.BooleanType)]
    ref_attrib = ['a/lex.rf', 'a/aux.rf', 'compl.rf', 'coref_gram.rf',
                  'coref_text.rf']

    def __init__(self, data=None, parent=None, zone=None):
        "Constructor"
        Node.__init__(self, data, parent, zone)

    def is_coap_root(self):
        functor = self.functor or None
        return functor in ['CONJ', 'CONFR', 'DISJ', 'GRAD', 'ADVS', 'CSQ',
                           'REAS', 'CONTRA', 'APPS', 'OPER']

    @property
    def lex_anode(self):
        return self.get_deref_attr('a/lex.rf')

    @lex_anode.setter
    def lex_anode(self, value):
        self.set_deref_attr('a/lex.rf', value)

    @property
    # TODO think of a better way (make node.aux_anodes.append(node2) possible?)
    def aux_anodes(self):
        return self.get_deref_attr('a/aux.rf')

    @aux_anodes.setter
    def aux_anodes(self, value):
        self.set_deref_attr('a/aux.rf', value)

    @property
    def anodes(self):
        "Return all anodes of a t-node"
        return (self.lex_anode and [self.lex_anode] or []) + \
               (self.aux_anodes or [])

    def add_aux_anodes(self, new_anodes):
        "Add an auxiliary a-node/a-nodes to the list."
        # get the original anodes and set the union
        if self.aux_anodes:
            self.aux_anodes = self.aux_anodes + as_list(new_anodes)
        else:
            self.aux_anodes = as_list(new_anodes)

    def remove_aux_anodes(self, to_remove):
        "Remove an auxiliary a-node from the list"
        self.aux_anodes = [anode for anode in self.aux_anodes
                           if not anode in to_remove]
        if not self.aux_anodes:
            self.aux_anodes = None

    @property
    def coref_gram_nodes(self):
        return self.get_deref_attr('coref_gram.rf')

    @coref_gram_nodes.setter
    def coref_gram_nodes(self, new_coref):
        self.set_deref_attr('coref_gram.rf', new_coref)

    @property
    def coref_text_nodes(self):
        return self.get_deref_attr('coref_text.rf')

    @coref_text_nodes.setter
    def coref_text_nodes(self, new_coref):
        self.set_deref_attr('coref_text.rf', new_coref)

    @property
    def compl_nodes(self):
        return self.get_deref_attr('compl.rf')

    @compl_nodes.setter
    def compl_nodes(self, new_coref):
        self.set_deref_attr('compl.rf', new_coref)

    @property
    def gram_number(self):
        return self.get_attr('gram/number')

    @gram_number.setter
    def gram_number(self, value):
        self.set_attr('gram/number', value)

    @property
    def gram_gender(self):
        return self.get_attr('gram/gender')

    @gram_gender.setter
    def gram_gender(self, value):
        self.set_attr('gram/gender', value)

    @property
    def gram_tense(self):
        return self.get_attr('gram/tense')

    @gram_tense.setter
    def gram_tense(self, value):
        self.set_attr('gram/tense', value)

    @property
    def gram_negation(self):
        return self.get_attr('gram/negation')

    @gram_negation.setter
    def gram_negation(self, value):
        self.set_attr('gram/negation', value)

    @property
    def gram_aspect(self):
        return self.get_attr('gram/aspect')

    @gram_aspect.setter
    def gram_aspect(self, value):
        self.set_attr('gram/aspect', value)

    @property
    def gram_degcmp(self):
        return self.get_attr('gram/degcmp')

    @gram_degcmp.setter
    def gram_degcmp(self, value):
        self.set_attr('gram/degcmp', value)

    @property
    def gram_deontmod(self):
        return self.get_attr('gram/deontmod')

    @gram_deontmod.setter
    def gram_deontmod(self, value):
        self.set_attr('gram/deontmod', value)

    @property
    def gram_dispmod(self):
        return self.get_attr('gram/dispmod')

    @gram_dispmod.setter
    def gram_dispmod(self, value):
        self.set_attr('gram/dispmod', value)

    @property
    def gram_indeftype(self):
        return self.get_attr('gram/indeftype')

    @gram_indeftype.setter
    def gram_indeftype(self, value):
        self.set_attr('gram/indeftype', value)

    @property
    def gram_iterativeness(self):
        return self.get_attr('gram/iterativeness')

    @gram_iterativeness.setter
    def gram_iterativeness(self, value):
        self.set_attr('gram/iterativeness', value)

    @property
    def gram_numertype(self):
        return self.get_attr('gram/numertype')

    @gram_numertype.setter
    def gram_numertype(self, value):
        self.set_attr('gram/numertype', value)

    @property
    def gram_person(self):
        return self.get_attr('gram/person')

    @gram_person.setter
    def gram_person(self, value):
        self.set_attr('gram/person', value)

    @property
    def gram_politeness(self):
        return self.get_attr('gram/politeness')

    @gram_politeness.setter
    def gram_politeness(self, value):
        self.set_attr('gram/politeness', value)

    @property
    def gram_resultative(self):
        return self.get_attr('gram/resultative')

    @gram_resultative.setter
    def gram_resultative(self, value):
        self.set_attr('gram/resultative', value)

    @property
    def gram_verbmod(self):
        return self.get_attr('gram/verbmod')

    @gram_verbmod.setter
    def gram_verbmod(self, value):
        self.set_attr('gram/verbmod', value)

    @property
    def gram_sempos(self):
        return self.get_attr('gram/sempos')

    @gram_sempos.setter
    def gram_sempos(self, value):
        self.set_attr('gram/sempos', value)

    @property
    def gram_diathesis(self):
        return self.get_attr('gram/diathesis')

    @gram_diathesis.setter
    def gram_diathesis(self, value):
        self.set_attr('gram/diathesis', value)

    def __eq__(self, other):
        """Equality based on memory reference, IDs, and finally hashes.
        TODO evaluate thoroughly"""
        if self is other:  # same object (address)
            return True
        if self.id and other.id and self.id == other.id:  # same IDs
            return True
        return hash(self) == hash(other)  # same tree under different/no ID

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        """Return hash of the tree that is composed of t-lemmas, formemes,
        and parent orders of all nodes in the tree (ordered)."""
        return hash(unicode(self))

    def __unicode__(self):
        desc = self.get_descendants(add_self=1, ordered=1)
        return ' '.join(['%d|%d|%s|%s' % (n.ord if n.ord is not None else -1,
                                          n.parent.ord if n.parent else -1,
                                          n.t_lemma,
                                          n.formeme)
                         for n in desc])

    def __str__(self):
        return unicode(self).encode('UTF-8', 'replace')


class A(Node, Ordered, EffectiveRelations, InClause):
    "Representing an a-node"

    attrib = [('form', types.UnicodeType), ('lemma', types.UnicodeType),
              ('tag', types.UnicodeType), ('afun', types.UnicodeType),
              ('no_space_after', types.BooleanType),
              ('morphcat', types.DictType),
              ('is_parenthesis_root', types.BooleanType),
              ('edge_to_collapse', types.BooleanType),
              ('is_auxiliary', types.BooleanType),
              ('p_terminal.rf', types.UnicodeType), ]
    ref_attrib = ['p_terminal.rf']

    morphcat_members = ['pos', 'subpos', 'gender', 'number', 'case', 'person',
                        'tense', 'negation', 'voice', 'grade', 'mood',
                        'possnumber', 'possgender']

    def __init__(self, data=None, parent=None, zone=None):
        "Constructor"
        Node.__init__(self, data, parent, zone)

    def is_coap_root(self):
        afun = self.afun or None
        return afun in ['Coord', 'Apos']

    def reset_morphcat(self):
        "Reset the morphcat structure members to '.'"
        for category in A.morphcat_members:
            self.set_attr('morphcat/' + category, '.')

    @property
    def morphcat_pos(self):
        return self.get_attr('morphcat/pos')

    @morphcat_pos.setter
    def morphcat_pos(self, value):
        self.set_attr('morphcat/pos', value)

    @property
    def morphcat_subpos(self):
        return self.get_attr('morphcat/subpos')

    @morphcat_subpos.setter
    def morphcat_subpos(self, value):
        self.set_attr('morphcat/subpos', value)

    @property
    def morphcat_gender(self):
        return self.get_attr('morphcat/gender')

    @morphcat_gender.setter
    def morphcat_gender(self, value):
        self.set_attr('morphcat/gender', value)

    @property
    def morphcat_number(self):
        return self.get_attr('morphcat/number')

    @morphcat_number.setter
    def morphcat_number(self, value):
        self.set_attr('morphcat/number', value)

    @property
    def morphcat_case(self):
        return self.get_attr('morphcat/case')

    @morphcat_case.setter
    def morphcat_case(self, value):
        self.set_attr('morphcat/case', value)

    @property
    def morphcat_person(self):
        return self.get_attr('morphcat/person')

    @morphcat_person.setter
    def morphcat_person(self, value):
        self.set_attr('morphcat/person', value)

    @property
    def morphcat_tense(self):
        return self.get_attr('morphcat/tense')

    @morphcat_tense.setter
    def morphcat_tense(self, value):
        self.set_attr('morphcat/tense', value)

    @property
    def morphcat_negation(self):
        return self.get_attr('morphcat/negation')

    @morphcat_negation.setter
    def morphcat_negation(self, value):
        self.set_attr('morphcat/negation', value)

    @property
    def morphcat_voice(self):
        return self.get_attr('morphcat/voice')

    @morphcat_voice.setter
    def morphcat_voice(self, value):
        self.set_attr('morphcat/voice', value)

    @property
    def morphcat_grade(self):
        return self.get_attr('morphcat/grade')

    @morphcat_grade.setter
    def morphcat_grade(self, value):
        self.set_attr('morphcat/grade', value)

    @property
    def morphcat_mood(self):
        return self.get_attr('morphcat/mood')

    @morphcat_mood.setter
    def morphcat_mood(self, value):
        self.set_attr('morphcat/mood', value)

    @property
    def morphcat_possnumber(self):
        return self.get_attr('morphcat/possnumber')

    @morphcat_possnumber.setter
    def morphcat_possnumber(self, value):
        self.set_attr('morphcat/possnumber', value)

    @property
    def morphcat_possgender(self):
        return self.get_attr('morphcat/possgender')

    @morphcat_possgender.setter
    def morphcat_possgender(self, value):
        self.set_attr('morphcat/possgender', value)


class N(Node):
    "Representing an n-node"

    attrib = [('ne_type', types.UnicodeType),
              ('normalized_name', types.UnicodeType),
              ('a.rf', types.ListType), ]
    ref_attrib = ['a.rf']

    def __init__(self, data=None, parent=None, zone=None):
        "Constructor"
        Node.__init__(self, data, parent, zone)


class P(Node):
    "Representing a p-node"

    attrib = [('is_head', types.BooleanType), ('index', types.UnicodeType),
              ('coindex', types.UnicodeType), ('edgelabel', types.UnicodeType),
              ('form', types.UnicodeType), ('lemma', types.UnicodeType),
              ('tag', types.UnicodeType), ('phrase', types.UnicodeType),
              ('functions', types.UnicodeType), ]
    ref_attrib = []

    def __init__(self, data=None, parent=None, zone=None):
        "Constructor"
        Node.__init__(self, data, parent, zone)
