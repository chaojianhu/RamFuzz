#!/usr/bin/env python

# Copyright 2016-17 The RamFuzz contributors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A sample Keras model trainable on the output of ./gencorp.py.  It tries to
predict the test success or failure based on the logged RamFuzz values during
the test run.  It consists of N dense layers in parallel whose outputs are
multiplied.  This is interesting because we know how to translate a fully
trained network like this into a feedback mechanism to the RamFuzz generator --
see ./solver.py.

Unfortunately, this model can currently only reach ~56% accuracy.

Usage: $0 [epochs] [batch_size] [N]
Defaults: epochs=1, batch_size=50, N=50

"""

from keras.constraints import min_max_norm
from keras.layers import BatchNormalization, Dense, Dropout, Embedding, Flatten
from keras.layers import Input
from keras.layers.merge import concatenate, multiply
from keras.metrics import mse
from keras.models import Model
from keras.optimizers import Adam
import glob
import keras.backend as K
import numpy as np
import os.path
import rfutils
import sys


class indexes:
    def __init__(self):
        self.d = dict()
        self.watermark = 1

    def get(self, x):
        if x not in self.d:
            self.d[x] = self.watermark
            self.watermark += 1
        return self.d[x]


def count_locpos(files):
    """Counts distinct positions and locations in a list of files.

    Returns a pair (position count, location indexes object)self.
    """
    posmax = 0
    locidx = indexes()
    for fname in files:
        with open(fname) as f:
            for (pos, (val, loc)) in enumerate(rfutils.logparse(f)):
                locidx.get(loc)
                posmax = max(posmax, pos)
    return posmax + 1, locidx


def read_data(files, poscount, locidx):
    """Builds input data from a files list."""
    locs = []  # One element per file; each is a list of location indexes.
    vals = []  # One element per file; each is a parallel list of values.
    labels = []  # One element per file: true for '.s', false for '.f'.
    for fname in gl:
        flocs = np.zeros(poscount, np.uint64)
        fvals = np.zeros((poscount, 1), np.float64)
        with open(fname) as f:
            for (p, (v, l)) in enumerate(rfutils.logparse(f)):
                flocs[p] = locidx.get(l)
                fvals[p] = v
        locs.append(flocs)
        vals.append(fvals)
        labels.append(fname.endswith('.s'))
    return np.array(locs), np.array(vals), np.array(labels)


gl = glob.glob(os.path.join('train', '*.[sf]'))
poscount, locidx = count_locpos(gl)

embedding_dim = 4
filter_sizes = (3, 8)
num_filters = 1
dropout_prob = (0.01, 0.01)
hidden_dims = 10

K.set_floatx('float64')

in_vals = Input((poscount, 1), name='vals', dtype='float64')
normd = BatchNormalization(
    axis=1, gamma_constraint=min_max_norm(),
    beta_constraint=min_max_norm())(in_vals)
in_locs = Input((poscount, ), name='locs', dtype='uint64')
embed_locs = Embedding(
    locidx.watermark, embedding_dim, input_length=poscount)(in_locs)
merged = concatenate([embed_locs, normd])
dense_count = int(sys.argv[3]) if len(sys.argv) > 3 else 50
dense_list = []
for i in range(dense_count):
    dense_list.append(
        Dropout(0.4)(Dense(1, activation='sigmoid')(Flatten()(merged))))
mult = multiply(dense_list)
ml = Model(inputs=[in_locs, in_vals], outputs=mult)
ml.compile(Adam(lr=0.03), metrics=['acc'], loss=mse)

locs, vals, labels = read_data(gl, poscount, locidx)


def fit(
        eps=int(sys.argv[1]) if len(sys.argv) > 1 else 1,
        # Large batches tend to cause NaNs in batch normalization.
        bsz=int(sys.argv[2]) if len(sys.argv) > 2 else 50):
    ml.fit([locs, vals], labels, batch_size=bsz, epochs=eps)


fit()