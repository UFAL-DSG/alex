#!/usr/bin/env python
# coding=utf-8
#
# Classes related to Treex documents, bundles and zones
#
from __future__ import unicode_literals
from treex.core.exception import RuntimeException
import treex.core.node

__author__ = "Ondřej Dušek"
__date__ = "2012"


class Document(object):
    """\
    This represents a Treex document, i.e. a sequence of bundles.
    It contains an index of node IDs.
    """

    def __init__(self, filename=None, data=None):
        """\
        Constructor. The data should contain a list of bundles that will be
        passed to the constructor of Bundle.
        """
        data = data or []
        self.__index = {}
        self.__backref = {}
        self.filename = filename
        self.bundles = [Bundle(self, data=bundle_data, b_ord=b_ord)
                        for b_ord, bundle_data in enumerate(data, start=1)]

    def index_node(self, node):
        """\
        Index a node by its id. Also index the node's references in the
        backwards reference index.
        """
        self.__index[node.id] = node
        refs = node.get_referenced_ids()
        for ref_type, value in refs.iteritems():
            self.index_backref(ref_type, node.id, value)

    def remove_node(self, node_id):
        "Remove a node from all indexes."
        # delete from normal index
        del self.__index[node_id]
        # using backward references, remove all references to the node
        for backref_type in self.__backref:
            refs = self.__backref[backref_type].get(node_id)
            if refs:
                for ref in refs:
                    referencing_node = self.get_node_by_id(ref)
                    referencing_node.remove_reference(backref_type, node_id)
                # remove the backward references from the index
                del self.__backref[backref_type][node_id]

    def get_node_by_id(self, node_id):
        return self.__index[node_id]

    def __getitem__(self, key):
        return self.get_node_by_id(key)

    def __setitem__(self, key, value):
        if value.id != key:
            raise ValueError
        return self.index_node(self, value)

    def __delitem__(self, key):
        self.remove_node(key)

    def index_backref(self, attr_name, source_id, target_ids):
        """\
        Keep track of a backward reference (source, target node IDs are in the
        direction of the original reference)
        """
        # create the backward index if it does not exist
        if not self.__backref.get(attr_name):
            self.__backref[attr_name] = {}
        # work always with lists of IDs, but handle also single IDs by
        # putting them into a list
        if not isinstance(target_ids, (list, tuple)):
            target_ids = [target_ids]
        # save the backward references (note the direction target -> source)
        for target_id in target_ids:
            if not self.__backref[attr_name].get(target_id):
                self.__backref[attr_name][target_id] = []
            self.__backref[attr_name][target_id].append(source_id)

    def remove_backref(self, attr_name, source_id, target_ids):
        """\
        Remove references from the backwards index.
        """
        # return if the index does not exist at all
        if not self.__backref.get(attr_name):
            return
        # work always with lists of IDs, but handle also single IDs
        # by putting them into a list
        if not isinstance(target_ids, (list, tuple)):
            target_ids = [target_ids]
        # delete all references
        for target_id in target_ids:
            try:
                self.__backref[attr_name][target_id].remove(source_id)
            except:  # if the reference is not there, we don't care
                pass

    def create_bundle(self, data=None):
        """\
        Append a new bundle and return it.
        """
        self.bundles.append(Bundle(self, data, b_ord=len(self.bundles) + 1))
        return self.bundles[-1]


class Bundle(object):
    """\
    Represents a bundle, i.e. a list of zones pertaining
    to the same sentence (in different variations).
    """

    def __init__(self, document, data=None, b_ord=None):
        """\
        Constructor. The data should contain a list of zones
        that will be passed to the constructor of Zone.
        """
        data = data or []
        self.__document = document
        # if no order is given, default to -1
        self.__ord = b_ord is not None and b_ord or -1
        self.__zones = {}
        # sort zones according to language and selector
        for zone_data in data:
            zone = Zone(data=zone_data, bundle=self)
            self.__zones[(zone.language, zone.selector)] = zone

    def get_all_zones(self):
        """\
        Return all zones contained in this bundle.
        """
        return self.__zones.values()

    def get_zone(self, language, selector):
        """\
        Returns the corresponding zone for a language and selector;
        raises an exception if the zone does not exist.
        """
        return self.__zones[(language, selector)]

    def get_or_create_zone(self, language, selector):
        """\
        Returns the zone for a language and selector; if it does
        not exist, creates an empty zone.
        """
        if self.has_zone(language, selector):
            return self.get_zone(language, selector)
        return self.create_zone(language, selector)

    def has_zone(self, language, selector):
        """\
        Returns True if the bundle has a zone for the
        given language and selector.
        """
        return self.__zones.get((language, selector)) and True or False

    def create_zone(self, language, selector):
        """\
        Creates a zone at the given language and selector.
        Will overwrite any existing zones.
        """
        self.__zones[(language, selector)] = Zone(bundle=self,
                                                  language=language,
                                                  selector=selector)
        return self.__zones[(language, selector)]

    @property
    def document(self):
        "The document this bundle belongs to."
        return self.__document

    @property
    def ord(self):
        "The order of this bundle in the document, as given by constructor"
        return self.__ord


class Zone(object):
    """\
    Represents a zone, i.e. a sentence and corresponding trees.
    """

    def __init__(self, data=None, language=None, selector=None, bundle=None):
        """\
        Constructor. The data should contain a dictionary with
        the following keys:  language, selector, sentence, Xtree (where X
        is one of t, a, n, p).
        """
        data = data or {}
        self.__bundle = bundle
        self.__document = self.bundle and self.bundle.document or None
        self.language = data.get('language') or language
        self.selector = data.get('selector') or selector or ''
        self.sentence = data.get('sentence')
        for layer in ('t', 'a', 'n', 'p'):
            if layer + 'tree' in data:
                self.create_tree(layer, data[layer + 'tree'])

    @property
    def bundle(self):
        "The bundle in which this zone is located"
        return self.__bundle

    @property
    def document(self):
        "The document in which this zone is located"
        return self.__document

    def has_tree(self, layer):
        """\
        Return True if this zone has a tree on the given layer, False
        otherwise.
        """
        return hasattr(self, layer + 'tree')

    def get_tree(self, layer):
        """\
        Return a tree this node has on the given layer or raise an
        exception if the tree does not exist.
        """
        return getattr(self, layer + 'tree')

    def create_tree(self, layer, data=None):
        """\
        Create a tree on the given layer, filling it with the given data
        (if applicable).
        """
        # store data for child nodes for later use
        nodes_data = None
        if data is not None and 'nodes' in data:
            nodes_data = data['nodes']
            del data['nodes']
        if data is None:
            data = {'id': layer + '-node-' + self.language_and_selector +
                    ('-s' + str(self.bundle.ord) if  self.bundle else '') +
                    '-root'}
        # call the appropriate constructor of the corresponding
        # class from treex.core.node (A, T, N, P)
        node_type = getattr(treex.core.node, layer.upper())
        # create the root
        root = node_type(data=data, zone=self)
        setattr(self, layer + 'tree', root)
        # create all the children given in data
        if nodes_data is not None:
            nodes = [(node_data['parent_id'],
                      node_type(data=node_data, parent=root, zone=self))
                     for node_data in nodes_data]
            doc = self.document
            for (parent_id, node) in nodes:
                node.parent = doc.get_node_by_id(parent_id)
        return self.get_tree(layer)

    def has_ttree(self):
        "Return true if this zone has a t-tree."
        return hasattr(self, 'ttree')

    def has_atree(self):
        "Return true if this zone has an a-tree."
        return hasattr(self, 'atree')

    def has_ntree(self):
        "Return true if this zone has an n-tree."
        return hasattr(self, 'ntree')

    def has_ptree(self):
        "Return true if this zone has a p-tree."
        return hasattr(self, 'ptree')

    @property
    def ttree(self):
        """\
        Direct access to t-tree (will raise an exception if the
        tree does not exist).
        """
        return self.__ttree

    @ttree.setter
    def ttree(self, value):
        if self.has_ttree():
            raise RuntimeException('Can\'t create a t-tree: tree exists')
        self.__ttree = value

    @property
    def atree(self):
        """\
        Direct access to a-tree (will raise an exception if the tree
        does not exist).
        """
        return self.__atree

    @atree.setter
    def atree(self, value):
        if self.has_atree():
            raise RuntimeException('Can\'t create an a-tree: tree exists')
        self.__atree = value

    @property
    def ntree(self):
        """\
        Direct access to n-tree (will raise an exception if the tree
        does not exist).
        """
        return self.__ntree

    @ntree.setter
    def ntree(self, value):
        if self.has_ntree():
            raise RuntimeException('Can\'t create an n-tree: tree exists')
        self.__ntree = value

    @property
    def ptree(self):
        """\
        Direct access to p-tree (will raise an exception if the tree
        does not exist).
        """
        return self.__ptree

    @ptree.setter
    def ptree(self, value):
        if self.has_ptree():
            raise RuntimeException('Can\'t create a p-tree: tree exists')
        self.__ptree = value

    def create_ttree(self):
        "Create a tree on the t-layer"
        return self.create_tree('t')

    def create_atree(self):
        "Create a tree on the a-layer"
        return self.create_tree('a')

    def create_ntree(self):
        "Create a tree on the n-layer"
        return self.create_tree('n')

    def create_ptree(self):
        "Create a tree on the p-layer"
        return self.create_tree('p')

    @property
    def language_and_selector(self):
        """\
        Return string concatenation of the zone's language and selector.
        """
        ret = str(self.language)
        if self.selector != '':
            ret += '_' + str(self.selector)
        return ret
