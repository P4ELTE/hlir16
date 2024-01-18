#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 Eotvos Lorand University, Budapest, Hungary

# run as: PYTHONPATH=.. python3 load_p4.py -I tnacodes -I tnacodes/simple_switch -o"__TARGET_TOFINO__=1" tnacodes/fastreact/two_by_two.p4

import os
import ujson
import hlir16.hlir
import sys
import argparse

def init_p4c():
    p4c_dir = os.environ.get('P4C')
    if p4c_dir is None or not os.path.isdir(p4c_dir):
        print("Exiting, reason: environment variable $P4C not set")
        sys.exit(1)

    return p4c_dir

def print_we(xs, typetxt):
    if len(xs) == 0:
        return

    print(f'{len(xs)} {typetxt}:')

    for msg in xs:
        msg, msg2 = msg
        print(f'    {msg}: {msg2}')


def print_warnings_errors():
    print_we(hlir.t4p4s.warnings, 'warnings')
    print_we(hlir.t4p4s.errors, 'errors')


def load_hlir(p4_file, json_file=None):
    init_p4c()

    p4v = '16'
    if json_file is None:
        json_file = p4_file.replace('.p4', '.json')

    if not os.path.isfile(json_file):
        json_file = hlir16.hlir.p4_to_json(p4_file, p4_include_dirs=args.include, opts=args.option)

    if not os.path.isfile(json_file):
        print("Exiting, reason: JSON file was not generated")
        sys.exit(1)

    with open(json_file, 'r') as json:
        json_root = ujson.load(json)

    hlir = hlir16.hlir.walk_json_from_top(json_root)
    hlir16.hlir_attrs.set_additional_attrs(hlir, p4_file, p4v)
    return hlir


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-I", "--include", action='append', help="Include files")
    parser.add_argument("-o", "--option", action='append', help="Options")
    parser.add_argument("p4_filename", help="P4 filename")
    args = parser.parse_args()

    hlir = load_hlir(args.p4_filename)

    print(f'File {args.p4_filename} is loaded')
    print_warnings_errors()

    breakpoint()
