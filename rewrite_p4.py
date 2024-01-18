#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: Apache-2.0
# Copyright 2023 Eotvos Lorand University, Budapest, Hungary

# run as: PYTHONPATH=.. python3 rewrite_p4.py

import os
import ujson
import hlir16.hlir
import hlir16.load_p4

p4c_dir = hlir16.load_p4.init_p4c()
p4c_sample_dir = os.path.join(p4c_dir, 'testdata', 'p4_16_samples')

p4_filename = 'basic2-bmv2.p4'
p4_json_filename = p4_filename.replace('.p4', '.json')

p4_file = os.path.join(p4c_sample_dir, p4_filename)
json_file = os.path.join(p4c_sample_dir, p4_json_filename)

hlir = hlir16.load_p4.load_hlir(p4_file, json_file)


import_files = {
    'V1Switch': 'v1model.p4',
    'PSA': 'psa.p4',
}

def type_to_str(node):
    if node.node_type == 'Type_Bits':
        return f'bit<{node.size}>'
    return 'TODO_TYPE'

print(f'#include <{import_files[hlir.news.model]}>')
print()

for hdr in hlir.headers.filter(lambda hdr: hdr.name != 'all_metadatas_t'):
    print(f'header {hdr.name} {{')
    for fld in hdr.fields:
        print(f'    {type_to_str(fld.type)} {fld.name};')
    print(f'}}')
    print()

print(f'struct headers {{')
for hdrinst in hlir.header_instances.filter(lambda hdrinst: hdrinst.name != 'all_metadatas'):
    print(f'    {hdrinst.urtype.name} {hdrinst.name};')
print(f'}}')
print()

print(f'struct metadata {{')
for meta in hlir.header_instances['all_metadatas']:
    print(f'    TODO_META {meta.name};')
print(f'}}')
print()

for parser in hlir.parsers:
    params = ', '.join(f'{param.direction} {param.urtype.name} {param.name}' for param in parser.type.applyParams.parameters)
    # breakpoint()

    print(f'parser {parser.type.name}({params}) {{')
    for state in parser.states:
        if state.name in ('accept', 'reject'):
            continue

        print(f'    state {state.name} {{')
        if state.selectExpression.path.name == 'accept':
            print(f'        transition accept;')
        print(f'    }}')
    print(f'}}')
    print()

def expr_to_string(expr):
    if expr.node_type == 'Constant':
        if expr.base == 10:
            return f'{expr.value}'
        return 'TODO_CONST_EXPR'

    if expr.node_type == 'Member':
        return f'{expr_to_string(expr.expr)}.{expr.member}'

    if expr.node_type == 'MethodCallExpression':
        args = ', '.join(expr_to_string(arg) for arg in expr.arguments)
        if 'path' not in expr.method:
            args = ', '.join(arg for arg in expr.arguments)
            return f'{expr_to_string(expr.method.expr)}.{expr.method.member}({args})'
        return f'{expr.method.path.name}({args})'

    if expr.node_type == 'PathExpression':
        return f'{expr.path.name}'

    if expr.node_type == 'StructExpression':
        args = ', '.join(expr.components.map('expression').map(expr_to_string))
        return f'{{{args}}}'

    if expr.node_type == 'TypeNameExpression':
        return f'{expr.urtype.name}'

    breakpoint()


    return 'TODO_EXPR'

def print_body_component(level, node):
    indent = '    '*level
    mc = node.methodCall
    if node.node_type == 'MethodCallStatement':
        exprs = ', '.join(mc.arguments.map('expression').map(expr_to_string))

        if 'path' not in mc.method:
            name = mc.method.member
            print(f'{indent}{mc.type.name}.{name}({exprs});')
            return
        else:
            name = mc.method.path.name
            print(f'{indent}{name}({exprs});')
            return
    print('TODO_COMP')


for ctl in hlir.controls:
    params = ', '.join(f'{param.direction} {param.urtype.name} {param.name}' for param in ctl.type.applyParams.parameters)

    print(f'control {ctl.type.name}({params}) {{')

    for action in ctl.actions:
        # TODO
        params = ''
        print(f'    action {action.name}({params}) {{')
        for comp in action.body.components:
            print_body_component(2, comp)
        print(f'    }}')

    for table in ctl.tables:
        print(f'    table {table.name} {{')

        print(f'        key = {{')
        for keyelem in table.key.keyElements:
            print(f'            {expr_to_string(keyelem.expression)}: {keyelem.matchType.path.name};')
        print(f'        }}')

        print(f'        actions = {{')
        for name in table.actions.map('expression.method.path.name'):
            print(f'            {name};')
        print(f'        }}')

        if 'size' in table:
            print(f'        size = {expr_to_string(table.size.expression)};')

        if 'default_action' in table:
            print(f'        default_action = {expr_to_string(table.default_action.expression)};')

        print(f'    }}')

    print(f'    apply {{')
    for comp in ctl.body.components:
        print_body_component(2, comp)
    print(f'    }}')

    print(f'}}')
    print()

main = hlir.news.main
main_name = main.urtype.name
main_exprs = ', '.join(hlir.news.main.arguments.map('expression').map('constructedType.path.name').map(lambda e: f'{e}()'))

print(f'{main_name}({main_exprs}) main;')
