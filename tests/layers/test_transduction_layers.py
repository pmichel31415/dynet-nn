#!/usr/bin/env python3
from itertools import product
import unittest
from unittest import TestCase

import numpy as np
import dynet as dy

from dynn.layers import dense_layers, recurrent_layers, transduction_layers


class TestFeedForwardTransductionLayer(TestCase):

    def setUp(self):
        self.pc = dy.ParameterCollection()
        self.do = 10
        self.di = 20
        self.bz = 6

    def test_feedforward_layer_transduction(self):
        # Simple dense layer
        dense = dense_layers.DenseLayer(self.pc, self.di, self.do)
        # Create transduction layer
        tranductor = transduction_layers.FeedForwardTransductionLayer(dense)
        # Initialize computation graph
        dy.renew_cg()
        # Create inputs
        seq = [dy.random_uniform(self.di, 0, i, self.bz) for i in range(10)]
        # Initialize tranductor
        tranductor.init(test=False, update=True)
        # Run tranductor
        outputs = tranductor(seq)
        # Try forward/backward
        z = dy.mean_batches(dy.sum_elems(dy.esum(outputs)))
        z.forward()
        z.backward()


def _test_recurrent_layer_unidirectional_transduction(
    layer,
    dummy_input,
    lengths,
    backward,
    left_padded,


):
    # Create transduction layer
    tranductor = transduction_layers.UnidirectionalLayer(layer)
    # Initialize computation graph
    dy.renew_cg()
    # Create inputs
    seq = [
        dy.inputTensor(dummy_input, batched=True) + i for i in range(10)
    ]
    # Initialize tranductor
    tranductor.init(test=False, update=True)
    # Run tranductor
    states = tranductor(
        seq, lengths=lengths, backward=backward, left_padded=left_padded
    )
    # Try forward/backward
    z = dy.mean_batches(dy.esum([dy.sum_elems(state[0]) for state in states]))
    z.forward()
    z.backward()


class TestUnidirectionalLayer(TestCase):

    def setUp(self):
        self.pc = dy.ParameterCollection()
        self.dh = 10
        self.di = 20
        self.bz = 6
        self.dropout = 0.1
        self.parameters_matrix = product(
            [None, [1, 2, 3, 4, 5, 6], [4, 5, 6, 6, 1, 2]],  # lengths
            [False, True],  # backward
            [True, False],  # left_padded
        )

    def test_elman_rnn(self):
        # Create lstm layer
        lstm = recurrent_layers.ElmanRNN(
            self.pc, self.di, self.dh, dropout=self.dropout
        )
        for lengths, backward, left_padded in self.parameters_matrix:
            print(f"Testing with:")
            print(f"- lengths=: {lengths}")
            print(f"- backward=: {backward}")
            print(f"- left_padded=: {left_padded}")
            _test_recurrent_layer_unidirectional_transduction(
                lstm,
                np.random.rand(self.di, self.bz),
                lengths,
                backward,
                left_padded
            )

    def test_lstm(self):
        # Create lstm layer
        lstm = recurrent_layers.LSTM(
            self.pc,
            self.di,
            self.dh,
            dropout_x=self.dropout,
            dropout_h=self.dropout,
        )
        for lengths, backward, left_padded in self.parameters_matrix:
            print(f"Testing with:")
            print(f"- lengths=: {lengths}")
            print(f"- backward=: {backward}")
            print(f"- left_padded=: {left_padded}")
            _test_recurrent_layer_unidirectional_transduction(
                lstm,
                np.random.rand(self.di, self.bz),
                lengths,
                backward,
                left_padded
            )


def _test_recurrent_layer_bidirectional_transduction(
    fwd_layer,
    bwd_layer,
    dummy_input,
    lengths,
    left_padded,
):
    # Create transduction layer
    tranductor = transduction_layers.BidirectionalLayer(fwd_layer, bwd_layer)
    # Initialize computation graph
    dy.renew_cg()
    # Create inputs
    seq = [
        dy.inputTensor(dummy_input, batched=True) + i for i in range(10)
    ]
    # Initialize tranductor
    tranductor.init(test=False, update=True)
    # Run tranductor
    fwd_states, bwd_states = tranductor(
        seq, lengths=lengths, left_padded=left_padded
    )
    # Try forward/backward
    fwd_z = dy.mean_batches(
        dy.esum([dy.sum_elems(state[0]) for state in fwd_states])
    )
    bwd_z = dy.mean_batches(
        dy.esum([dy.sum_elems(state[0]) for state in bwd_states])
    )
    z = fwd_z + bwd_z
    z.forward()
    z.backward()


class TestBidirectionalLayer(TestCase):

    def setUp(self):
        self.pc = dy.ParameterCollection()
        self.dh = 10
        self.di = 20
        self.bz = 6
        self.dropout = 0.1
        self.parameters_matrix = product(
            [None, [1, 2, 3, 4, 5, 6], [4, 5, 6, 6, 1, 2]],  # lengths
            [True, False],  # left_padded
        )

    def test_bi_elman_rnn(self):
        # Create rnn layers
        fwd_rnn = recurrent_layers.ElmanRNN(
            self.pc, self.di, self.dh, dropout=self.dropout
        )
        bwd_rnn = recurrent_layers.ElmanRNN(
            self.pc, self.di, self.dh, dropout=self.dropout
        )
        for lengths, left_padded in self.parameters_matrix:
            print(f"Testing with:")
            print(f"- lengths=: {lengths}")
            print(f"- left_padded=: {left_padded}")
            _test_recurrent_layer_bidirectional_transduction(
                fwd_rnn,
                bwd_rnn,
                np.random.rand(self.di, self.bz),
                lengths,
                left_padded
            )

    def test_bi_lstm(self):
        # Create lstm layers
        fwd_lstm = recurrent_layers.LSTM(
            self.pc,
            self.di,
            self.dh,
            dropout_x=self.dropout,
            dropout_h=self.dropout,
        )
        bwd_lstm = recurrent_layers.LSTM(
            self.pc,
            self.di,
            self.dh,
            dropout_x=self.dropout,
            dropout_h=self.dropout,
        )

        for lengths, left_padded in self.parameters_matrix:
            print(f"Testing with:")
            print(f"- lengths=: {lengths}")
            print(f"- left_padded=: {left_padded}")
            _test_recurrent_layer_bidirectional_transduction(
                fwd_lstm,
                bwd_lstm,
                np.random.rand(self.di, self.bz),
                lengths,
                left_padded
            )

    def test_rnn_lstm(self):
        # Create rnn/lstm layers
        fwd_lstm = recurrent_layers.LSTM(
            self.pc,
            self.di,
            self.dh,
            dropout_x=self.dropout,
            dropout_h=self.dropout,
        )
        bwd_rnn = recurrent_layers.ElmanRNN(
            self.pc, self.di, self.dh, dropout=self.dropout
        )
        for lengths, left_padded in self.parameters_matrix:
            print(f"Testing with:")
            print(f"- lengths=: {lengths}")
            print(f"- left_padded=: {left_padded}")
            _test_recurrent_layer_bidirectional_transduction(
                fwd_lstm,
                bwd_rnn,
                np.random.rand(self.di, self.bz),
                lengths,
                left_padded
            )


if __name__ == '__main__':
    unittest.main()