#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: Apache-2.0
# Copyright 2017 Eotvos Lorand University, Budapest, Hungary

from hlir16.p4node import P4Node
from hlir16.hlir_utils import unique_list, make_canonical_name, make_short_canonical_names
from hlir16.hlir_model import smem_types_by_model, packets_by_model

def get_ctrlloc_smem_type(loc):
    type = loc.type.baseType if loc.type.node_type == 'Type_Specialized' else loc.type
    return type.path.name


def get_direct_smems(smem_type, tables):
    """Gets counters and meters for tables."""
    return unique_list((t, loc)
        for t in tables
        for loc in t.control.controlLocals['Declaration_Instance']
        if get_ctrlloc_smem_type(loc) == smem_type)


def get_smems(smem_type, tables):
    """Gets counters and meters for tables."""
    return unique_list((None, loc)
        for t in tables
        for loc in t.control.controlLocals['Declaration_Instance']
        if get_ctrlloc_smem_type(loc) == smem_type)


def get_registers(hlir, register_name):
    reg_insts = hlir.decl_instances
    local_regs = hlir.controls.flatmap('controlLocals').filter('node_type', 'Declaration_Instance').filter('type.node_type', 'Type_Specialized')
    return (reg_insts + local_regs).filter('type.baseType.path.name', register_name)


# In v1model, all software memory cells are represented as 32 bit integers
def smem_repr_type(smem):
    tname = "int" if smem.is_signed else "uint"

    for w in [8,16,32,64]:
        if smem.size <= w:
            # note: this should look like the line below, but is used as a postfix of method name apply_direct_smem_* in dataplane.c
            # return f"REGTYPE({tname},{w})"
            return f"register_{tname}{w}_t"

    return "NOT_SUPPORTED"


def smem_components(hlir, smem, table):
    get_smem, reverse_get_smem = smem_types_by_model(hlir)

    make_canonical_name(smem)

    smem.is_direct  = smem.smem_type in ('direct_counter', 'direct_meter')

    smem.size = smem.type.arguments[0].urtype.size if smem.smem_type == 'register' else 32
    smem.is_signed = smem.type.arguments[0].urtype.isSigned if smem.smem_type == 'register' else False
    smem.is_direct = smem.smem_type in ('direct_counter', 'direct_meter')

    smem.amount = 1 if smem.is_direct else smem.arguments['Argument'][0].expression.value

    base_type = smem_repr_type(smem)

    if smem.smem_type == 'register':
        smem.name_parts = P4Node([smem.smem_type, smem.name])
        return [{"type": base_type, "name": smem.name}]


    pobs, reverse_pobs = packets_by_model(hlir)
    smem.packets_or_bytes = reverse_pobs[smem.arguments.map('expression').filter('node_type', 'Member')[0].member]

    smem.smem_for = {
        "packets": smem.packets_or_bytes in ("packets", "packets_and_bytes"),
        "bytes":   smem.packets_or_bytes in (  "bytes", "packets_and_bytes"),
    }

    if smem.is_direct:
        smem.table = table
        pkts_parts  = [smem.smem_type, smem.name, pobs['packets'], table.name]
        bytes_parts = [smem.smem_type, smem.name, pobs['bytes'], table.name]
    else:
        pkts_parts  = [smem.smem_type, smem.name, pobs['packets']]
        bytes_parts = [smem.smem_type, smem.name, pobs['bytes']]

    pkts_name  = '_'.join(pkts_parts)
    bytes_name = '_'.join(bytes_parts)

    pbs = {
        "packets":           P4Node([{"for": "packets", "type": base_type, "name": pkts_name}]),
        "bytes":             P4Node([{"for":   "bytes", "type": base_type, "name": bytes_name}]),

        "packets_and_bytes": P4Node([{"for": "packets", "type": base_type, "name": pkts_name},
                                     {"for":   "bytes", "type": base_type, "name": bytes_name}]),
    }

    flatpbs = {
        "packets":           ['packets'],
        "bytes":             ['bytes'],
        "packets_and_bytes": ['packets', 'bytes'],
    }

    smem.insts = P4Node([])
    for pb in flatpbs[smem.packets_or_bytes]:
        smem_inst = P4Node({'node_type': 'Smem_Instance'})

        smem_inst.smem = smem
        smem_inst.name = smem.name

        smem_inst.packets_or_bytes = pb

        smem_inst.is_direct  = smem.smem_type in ('direct_counter', 'direct_meter')

        smem_inst.size = smem.type.arguments[0].urtype.size if smem.smem_type == 'register' else 32
        smem_inst.is_signed = smem.type.arguments[0].urtype.isSigned if smem.smem_type == 'register' else False
        smem_inst.is_direct = smem.smem_type in ('direct_counter', 'direct_meter')

        smem_inst.amount = 1 if smem.is_direct else smem.arguments['Argument'][0].expression.value

        smem_inst.table = table if smem_inst.is_direct else None

        packet_or_byte = pobs[pb]
        if smem_inst.is_direct:
            smem.name_parts = P4Node([smem.smem_type, smem.name, table.name])
            smem_inst.name_parts = P4Node([smem.smem_type, smem.name, packet_or_byte, table.name])
        else:
            smem.name_parts = P4Node([smem.smem_type, smem.name])
            smem_inst.name_parts = P4Node([smem.smem_type, smem.name, packet_or_byte])

        hlir.smem_insts.append(smem_inst)
        smem.insts.append(smem_inst)
        smem.set_attr(f'smem_{pb}_inst', smem_inst)

    return pbs[smem.packets_or_bytes]


def attrs_stateful_memory(hlir):
    get_smem, reverse_get_smem = smem_types_by_model(hlir)

    # direct counters
    for table in hlir.tables:
        table.direct_meters    = P4Node(unique_list(m for t, m in get_direct_smems(get_smem['direct_meter'], [table])))
        table.direct_counters  = P4Node(unique_list(c for t, c in get_direct_smems(get_smem['direct_counter'], [table])))

    hlir.smem = P4Node({'node_type': 'NodeGroup'})

    # indirect counters
    hlir.smem.meters    = P4Node(unique_list(get_smems(get_smem['meter'], hlir.tables)))
    hlir.smem.counters  = P4Node(unique_list(get_smems(get_smem['counter'], hlir.tables)))
    hlir.smem.registers = P4Node(unique_list(get_registers(hlir, get_smem['register'])))

    dms = [(t, m) for t in hlir.tables for m in t.direct_meters]
    dcs = [(t, c) for t in hlir.tables for c in t.direct_counters]

    for t in hlir.tables:
        for m in t.direct_meters:
            m.table_ref = t
        for c in t.direct_counters:
            c.table_ref = t

    hlir.smem.direct_counters = P4Node(unique_list(dcs))
    hlir.smem.direct_meters = P4Node(unique_list(dms))
    hlir.smem.all_meters   = hlir.smem.meters   + hlir.smem.direct_meters
    hlir.smem.all_counters = hlir.smem.counters + hlir.smem.direct_counters
    hlir.smem.directs      = hlir.smem.direct_meters + hlir.smem.direct_counters
    hlir.smem.indirects    = hlir.smem.meters + hlir.smem.counters
    hlir.smem.all          = hlir.smem.all_meters + hlir.smem.all_counters + hlir.smem.registers.map(lambda reg: (None, reg))

    hlir.smem_insts = P4Node([])

    for table, smem in hlir.smem.all:
        simple_smem_type = smem.type._baseType.path.name

        smem.smem_type  = reverse_get_smem[simple_smem_type]
        smem.components = smem_components(hlir, smem, table)

    make_short_canonical_names([smem for _, smem in hlir.smem.all_meters])
    make_short_canonical_names([smem for _, smem in hlir.smem.all_counters])
    make_short_canonical_names(hlir.smem.registers)


def attrs_ref_stateful_memory(hlir):
    get_smem, reverse_get_smem = smem_types_by_model(hlir)

    for extern in hlir.all_nodes.by_type('Type_Extern'):
        if extern.name in reverse_get_smem:
            extern.extern_type = 'smem'
            extern.smem_type = reverse_get_smem[extern.name]
