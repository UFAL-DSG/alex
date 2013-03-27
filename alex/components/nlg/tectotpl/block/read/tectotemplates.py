#!/usr/bin/env python
# coding=utf-8
#
# Block for reading Treex YAML files
#
from __future__ import absolute_import
from __future__ import unicode_literals

from alex.components.nlg.tectotpl.core.block import Block
from alex.components.nlg.tectotpl.core import Document

from alex.components.nlg.tectotpl.core.exception import LoadingException
from alex.components.nlg.tectotpl.core.util import file_stream
import re

__author__ = "Ondřej Dušek"
__date__ = "2013"


class TectoTemplates(Block):
    """\
    Reader for partial t-tree dialog system templates, where treelets
    can be intermixed with linear text.

    Example template:

    Vlak přijede v [[7|adj:attr] hodina|n:4|gender:fem].

    All linear text is inserted into t-lemmas of atomic nodes, while
    treelets have their formeme and grammateme values filled in.
    """

    def __init__(self, scenario, args):
        """\
        Constructor, checks if language is set and selects encoding according
        to args, defauts to UTF-8.
        """
        Block.__init__(self, scenario, args)
        if self.language is None:
            raise LoadingException('Language must be defined!')
        self.encoding = args.get('encoding', 'UTF-8')

    def process_document(self, filename):
        """\
        Read a Tecto-Template file and return its contents as
        a Document object.
        """
        fh = file_stream(filename, encoding=self.encoding)
        doc = Document(filename)
        for line in fh:
            bundle = doc.create_bundle()
            zone = bundle.create_zone(self.language, self.selector)
            ttree = zone.create_ttree()
            self.parse_line(line, ttree)
        fh.close()
        return doc

    def parse_line(self, text, troot):
        """\
        Parse a template to a t-tree.
        """
        off = 0
        last_tnode = troot
        while off < len(text):
            # search for next treelet
            parse_treelet = True
            pos = text.find('[', off)
            if pos == -1:  # no treelets, everything until the end is linear
                pos = len(text)
                parse_treelet = False
            # create a tree with the linear part up to the next treelet
            tnode = troot.create_child(data={'t_lemma': text[off:pos],
                                             'nodetype': 'atom',
                                             'formeme': 'x'})
            tnode.shift_after_subtree(last_tnode)
            last_tnode = tnode
            # parse the next treelet and move after it
            if parse_treelet:
                tnode = troot.create_child()
                tnode.shift_after_node(last_tnode)
                off = pos + 1 + self.parse_treelet(text[pos + 1:], tnode)
                last_tnode = tnode
            # no more treelets to parse, we just added everything till the end
            else:
                break

    def parse_treelet(self, text, tnode):
        """\
        Parse a treelet in the template, filling the required values.
        Returns the position in the text after the treelet.
        """
        pos = 0
        right = False
        while pos < len(text):
            # skip space
            if text[pos].isspace():
                pos += 1
            # delve deeper
            elif text[pos] == '[':
                tchild = tnode.create_child()
                if not right:
                    tchild.shift_before_node(tnode)
                else:
                    tchild.shift_after_subtree(tnode)
                pos += 1 + self.parse_treelet(text[pos + 1:], tchild)
            # return
            elif text[pos] == ']':
                return pos + 1
            # fill in node attributes
            else:
                # may even contain multiple words
                values = re.match(r'^([^\]\[]+)', text[pos:]).group(1)
                pos += len(values)
                values = values.split('|')
                tnode.t_lemma = values[0]
                # fill in formeme (if applicable, default to x/atom)
                if len(values) >= 2:
                    tnode.formeme = values[1]
                    tnode.nodetype = 'complex'
                else:
                    tnode.formeme = 'x'
                    tnode.nodetype = 'atom'
                # fill in grammatemes
                if len(values) >= 3:
                    gram_dict = {}
                    for gram in values[2].split(','):
                        gram_name, gram_val = gram.split(':')
                        gram_dict[gram_name.strip()] = gram_val.strip()
                right = True
        return len(text)
