#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: Apache-2.0
# Copyright 2024 Eotvos Lorand University, Budapest, Hungary

def addWarning(hlir, msg, msg2):
    hlir.t4p4s.warnings.append((msg, msg2))

def addError(hlir, msg, msg2):
    hlir.t4p4s.errors.append((msg, msg2))
