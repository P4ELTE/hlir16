# SPDX-License-Identifier: Apache-2.0
# Copyright 2020 Eotvos Lorand University, Budapest, Hungary

from hlir16.p4node import P4Node


def make_node_group(target, new_group_name, nodes, origin = None):
    """Move the selected nodes from a vector node into a new attribute of the target node.
    The grouped nodes are removed from the origin node if it is given."""
    new_node = P4Node(nodes)
    target.set_attr(new_group_name, new_node)
    if origin is not None:
        for node in nodes:
            origin.vec.remove(node)


def align8_16_32(size):
    return 8 if size <= 8 else 16 if size <= 16 else 32


def unique_list(elems):
    return list(set(elems))


def shorten_locvar_names(locvars, last_infix='_'):
    # locs = locvars.filter(lambda loc: 'type_ref' not in loc.type)
    locs = locvars

    locvars_in_order = all(loc.name.endswith(f'{last_infix}{idx}') for idx, loc in enumerate(locs))
    no_dups = len(set(loc.name[:-len(f'{last_infix}{idx}')] for idx, loc in enumerate(locs))) == len(locs)

    can_shorten = locvars_in_order and no_dups

    for idx, loc in enumerate(locs):
        no_postfix = loc.name[:-len(f'{last_infix}{idx}')]
        if not can_shorten:
            loc.short_name = loc.name
        elif no_postfix.startswith('_'):
            loc.short_name = '.'.join(no_postfix.split('_')[1:]) if can_shorten else loc.name
        else:
            loc.short_name = no_postfix if can_shorten else loc.name


# note: Python 3.9 has this as a built-in
def removeprefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def make_canonical_name(node):
    annot = node.annotations.annotations.get('name')
    node.canonical_name = annot.expr[0].value if annot is not None else f'({removeprefix(node.name, "tbl_")})'


def make_short_canonical_names(nodes):
    shorted = set()
    multiple = set()

    infos = [(node, node.canonical_name, node.canonical_name.split('.')[-1], 'is_hidden' in node and node.is_hidden) for node in nodes]

    for node, canname, shortname, hid in infos:
        if hid:
            continue
        shortname = canname.split('.')[-1]
        if shortname in multiple:
            continue
        if shortname in shorted:
            shorted.remove(shortname)
            multiple.add(shortname)
            continue
        shorted.add(shortname)

    for node, canname, shortname, hid in infos:
        if hid:
            node.short_name = canname
        else:
            node.short_name = shortname if shortname in shorted else canname


def dlog(num, base=2):
    """Returns the discrete logarithm of num.
    For the standard base 2, this is the number of bits required to store the range 0..num."""
    return [n for n in range(32) if num < base**n][0]


def unique_everseen(items):
    """Returns only the first occurrence of the items in a list.
    Equivalent to unique_everseen from the package more-itertools."""
    from collections import OrderedDict
    return list(OrderedDict.fromkeys(items))
