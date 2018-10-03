#!/usr/bin/env python3
"""
Embedding layers
================

For embedding discrete inputs (such as words, characters).
"""
from collections import Iterable

import numpy as np
import dynet as dy

from ..data.dictionary import Dictionary
from ..parameter_initialization import NormalInit
from ..operations import unsqueeze
from .base_layers import ParametrizedLayer


class EmbeddingLayer(ParametrizedLayer):
    """Layer for embedding elements of a dictionary

    Example:

    .. code-block:: python

        # Dictionary
        dic = dynn.data.dictionary.Dictionary(symbols=["a", "b"])
        # Parameter collection
        pc = dy.ParameterCollection()
        # Embedding layer of dimension 10
        embed = EmbeddingLayer(pc,dic, 10)
        # Initialize
        dy.renew_cg()
        embed.init()
        # Return a batch of 2 10-dimensional vectors
        vectors = embed([dic.index("b"), dic.index("a")])

    Args:
        pc (:py:class:`dynet.ParameterCollection`): Parameter collection to
            hold the parameters
        dictionary (:py:class:`dynn.data.dictionary.Dictionary`): Mapping
            from symbols to indices
        embed_dim (int): Embedding dimension
        initialization (:py:class:`dynet.PyInitializer`, optional): How
            to initialize the parameters. By default this will initialize
            to :math:`\mathcal N(0, \\frac{`}{\sqrt{\\textt{embed\_dim}}})`
        pad_mask (float, optional): If provided, embeddings of the
            ``dictionary.pad_idx`` index will be masked with this value
    """

    def __init__(
        self,
        pc,
        dictionary,
        embed_dim,
        initialization=None,
        pad_mask=None
    ):
        super(EmbeddingLayer, self).__init__(pc, "embedding")
        # Check input
        if not isinstance(dictionary, Dictionary):
            raise ValueError(
                "dictionary must be a dynn.data.Dictionary object"
            )
        # Dictionary and hyper-parameters
        self.dictionary = dictionary
        self.size = len(self.dictionary)
        self.embed_dim = embed_dim
        self.pad_mask = pad_mask
        # Default init
        default_init = NormalInit(std=1/np.sqrt(self.embed_dim))
        initialization = initialization or default_init
        # Parameter shape for dynet
        if isinstance(embed_dim, (list, tuple, np.ndarray)):
            param_dim = tuple([self.size] + [dim for dim in embed_dim])
        else:
            param_dim = (self.size, embed_dim)
        # Create lookup parameter
        self.params = self.pc.add_lookup_parameters(
            param_dim,
            init=initialization,
            name="params"
        )
        # Default update parameter
        self.update = True

    def init(self, test=False, update=True):
        """Initialize the layer before performing computation

        Args:
            test (bool, optional): If test mode is set to ``True``,
                dropout is not applied (default: ``True``)
            update (bool, optional): Whether to update the parameters
                (default: ``True``)
        """
        self.test = test
        self.update = update

    def __call__(self, idxs):
        """Returns the input's embedding

        If ``idxs`` is a list this returns a batch of embeddings. If it's a
        numpy array of shape ``N x b`` it returns a batch of ``b``
        ``N x embed_dim`` matrices

        Args:
            idxs (list,int): Index or list of indices to embed

        Returns:
            :py:class:`dynet.Expression`: Batch of embeddings
        """
        if not isinstance(idxs, Iterable):
            # Handle int inputs
            idxs = [idxs]
        idxs = np.asarray(idxs, dtype=int)
        if len(idxs.shape) == 1:
            # List of indices
            embeds = dy.lookup_batch(self.params, idxs, update=self.update)
        elif len(idxs.shape) == 2:
            # Matrix of indices
            vecs = [dy.lookup_batch(self.params, idx, update=self.update)
                    for idx in idxs]
            embeds = dy.concatenate([unsqueeze(vec, d=0) for vec in vecs], d=0)
        else:
            raise ValueError(
                "EmbeddingLayer only takes an int , list of ints or matrix of "
                "ints as input"
            )

        # Masking
        if self.pad_mask is not None:
            is_padding = (idxs == self.dictionary.pad_idx).astype(int)
            mask = unsqueeze(dy.inputTensor(is_padding, batched=True), d=-1)
            embeds = dy.cmult(1-mask, embeds) + self.pad_mask * mask

        return embeds
