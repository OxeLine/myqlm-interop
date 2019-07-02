#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

"""
@brief 

@namespace ...
@authors Reda Drissi <mohamed-reda.drissi@atos.net>
@copyright 2019  Bull S.A.S.  -  All rights reserved.
           This is not Free or Open Source software.
           Please contact Bull SAS for details about its license.
           Bull - Rue Jean Jaurès - B.P. 68 - 78340 Les Clayes-sous-Bois


Description This is a test suite for qiskit circuit converter

Overview
=========


"""
import unittest
from qat.lang.AQASM.gates import *
from qat.core.util import get_syntax
from qat.lang.AQASM.program import Program
from qat.interop.pyquil.converters import to_pyquil_circ, to_qlm_circ
from pyquil import Program as Prg
from pyquil import gates as pg
import numpy as np


pygates_1qb = [X, Y, Z, I, S, T, H, RX(3.14), RY(3.14), RZ(3.14), PH(3.14)]
pygates_2qb = [SWAP, CNOT, H.ctrl(), RZ(3.14).ctrl(), RY(3.14).ctrl()]

quil_1qb = [pg.X, pg.Y, pg.Z, pg.I, pg.S, pg.T, pg.H]
quil_params = [pg.RX, pg.RY, pg.RZ, pg.PHASE]
quil_ctrl = [pg.H]
quil_ctrl_prm = [pg.RZ, pg.RY]

from qat.core.util import get_syntax

def extract_syntax(circuit):
    data = []
    for index, op in enumerate(circuit.ops):
        entry = {}
        try:
            name, params, qubits = get_syntax(circuit, index)
            cbits = op.cbits
        except ValueError:
            name, params, qubits, cbits = get_syntax(circuit, index)
        entry['name'] = name
        entry['params'] = params
        entry['qubits'] = qubits
        entry['cbits'] = cbits
        data.append(entry)
    return data

def print_aq(circuit):
    data = extract_syntax(circuit)
    result = ""
    for entry in data:
        result += "Gate {} with params {} on qubits {} and cbits {}\n".format(
            entry["name"], entry["params"], entry["qubits"], entry['cbits']
        )
        supername = None
    return result


class TestPyquil2QLMConversion(unittest.TestCase):
    """ Tests the function converting pyquil circuit
        to qlm circuit"""

    def test_default_gates(self):
        prog = Program()
        qreg = prog.qalloc(3)

        for op in pygates_1qb:
            prog.apply(op, qreg[0])

        for op in pygates_2qb:
            prog.apply(op, qreg[0], qreg[1])

        prog.apply(CCNOT, qreg[0], qreg[1], qreg[2])

        expected = prog.to_circ()
        #result = to_pyquil_circ(qlm_circuit)
        # print(result)
        result = Prg()
        for op in quil_1qb:
            result += op(0)
        for op in quil_params:
            result += op(3.14, 0)

        result += pg.SWAP(0, 1)
        result += pg.CNOT(0, 1)
        for op in quil_ctrl:
            result += op(1).controlled(0)
        for op in quil_ctrl_prm:
            result += op(3.14, 1).controlled(0)

        result += pg.CCNOT(0, 1, 2)

        qlm_circuit = to_qlm_circ(result)
        exp_str = print_aq(expected)
        res_str = print_aq(qlm_circuit)
        self.assertEqual(exp_str, res_str)

    def test_recursive_ctrl_and_dagger(self):
        prog = Program()
        qreg = prog.qalloc(5)
        prog.apply(
            Y.ctrl().ctrl().ctrl().ctrl().dag().dag().dag(),
            *qreg
        )
        expected = prog.to_circ()
        result = Prg()
        result += (
            pg.Y(4).controlled(0).controlled(1).controlled(2).controlled(3).dagger()
        )
        result = to_qlm_circ(result)
        res_str = print_aq(result)
        exp_str = print_aq(expected)
        self.assertEqual(res_str, exp_str)

    def test_measures(self):
        prog = Program()
        qreg = prog.qalloc(3)
        creg = prog.calloc(3)

        prog.apply(H, qreg[0])
        prog.apply(H, qreg[1])
        prog.apply(H, qreg[2])

        prog.measure(qreg[0], creg[0])
        prog.measure(qreg[1], creg[1])
        prog.measure(qreg[2], creg[2])
        expected = prog.to_circ()

        result = Prg()
        cbs = result.declare("ro", "BIT", 3)
        result += pg.H(0)
        result += pg.H(1)
        result += pg.H(2)
        result += pg.MEASURE(0, cbs[0])
        result += pg.MEASURE(1, cbs[1])
        result += pg.MEASURE(2, cbs[2])

        result = to_qlm_circ(result)
        exp_str = print_aq(expected)
        res_str = print_aq(result)
        self.assertEqual(res_str, exp_str)

    def test_separate_measures(self):
        prog = Program()
        qreg = prog.qalloc(3)
        creg = prog.calloc(3)

        prog.apply(H, qreg[0])
        prog.apply(H, qreg[1])
        prog.apply(H, qreg[2])

        expected = prog.to_circ()

        result = Prg()
        cbs = result.declare("ro", "BIT", 3)
        result += pg.H(0)
        result += pg.H(1)
        result += pg.H(2)
        result += pg.MEASURE(0, cbs[0])
        result += pg.MEASURE(1, cbs[1])
        result += pg.MEASURE(2, cbs[2])

        result, to_measure = to_qlm_circ(result, True)
        exp_str = print_aq(expected)
        res_str = print_aq(result)
        self.assertEqual(res_str, exp_str)
        self.assertEqual(to_measure, [0, 1, 2])

    def _test_qvm_run(self):
        from qat.interop.pyquil.algorithms import QFT3
        from qat.interop.pyquil.providers import PyquilQPU
        from pyquil.api import QVMConnection

        qvm = QVMConnection(endpoint="http://localhost:15011")
        qpu = PyquilQPU(qvm)
        pyquil_prog = QFT3()

        expected = qpu.submit(to_qlm_circ(pyquil_prog).to_job())

        result = qpu.submit(to_qlm_circ(to_pyquil_circ(to_qlm_circ(pyquil_prog))).to_job())
        print(expected)
        print(result)



if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
