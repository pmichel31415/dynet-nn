#!/usr/bin/env python3
"""
Convolution layers
==================
"""
import dynet as dy

from ..parameter_initialization import ZeroInit
from ..activations import identity
from .. import util, operations
from .base_layers import ParametrizedLayer


class Conv1D(ParametrizedLayer):
    """1D convolution along the first dimension

    Args:
        pc (:py:class:`dynet.ParameterCollection`): Parameter collection to
            hold the parameters
        input_dim (int): Input dimension
        num_kernels (int): Number of kernels (essentially the output dimension)
        kernel_width (int): Width of the kernels
        activation (function, optional): activation function
            (default: ``identity``)
        dropout (float, optional):  Dropout rate (default 0)
        nobias (bool, optional): Omit the bias (default ``False``)
        zero_padded (bool, optional): Default padding behaviour. Pad
            the input with zeros so that the output has the same length
            (default ``True``)
        stride (list, optional): Default stride along the length
            (defaults to ``1``).
    """

    def __init__(
        self,
        pc,
        input_dim,
        num_kernels,
        kernel_width,
        activation=identity,
        dropout_rate=0.0,
        nobias=False,
        zero_padded=True,
        stride=1,
        K=None,
        b=None,
    ):
        super(Conv1D, self).__init__(pc, "conv1d")
        # Hyper-parameters
        self.input_dim = input_dim
        self.num_kernels = num_kernels
        self.kernel_width = kernel_width
        self.activation = activation
        self.dropout_rate = dropout_rate
        self.nobias = nobias
        self.zero_padded = zero_padded
        self.stride = stride
        # Parameters
        # Filters have shape:
        #   kernel_width x 1 x input_dim x num_filters
        self.add_parameters(
            "K",
            (self.kernel_width, 1, self.input_dim, self.num_kernels),
            param=K,
        )
        if not self.nobias:
            self.add_parameters(
                "b",
                self.num_kernels,
                param=b,
                init=ZeroInit(),
            )

    def __call__(self, x, stride=None, zero_padded=None):
        """Forward pass

        Args:
            x (:py:class:`dynet.Expression`): Input expression with the shape
                (length, input_dim)
            stride (int, optional): Stride along the temporal dimension
            zero_padded (bool, optional): Pad the image with zeros so that the
                output has the same length (default ``True``)

        Returns:
            :py:class:`dynet.Expression`: Convolved sequence.
        """
        # Dropout
        x = util.conditional_dropout(x, self.dropout_rate, not self.test)
        # Reshape the ``length x input_dim`` matrix to an
        # "image" of shape ``length x 1 x input_dim`` to use dynet's conv2d
        img = operations.unsqueeze(x, 1)
        # Retrieve convolution arguments
        is_valid = not (
            self.zero_padded if zero_padded is None else zero_padded
        )
        stride = [stride or self.stride or 1, 1]
        if self.nobias:
            output_img = dy.conv2d(
                img, self.K, stride=stride, is_valid=is_valid
            )
        else:
            output_img = dy.conv2d_bias(
                img, self.K, self.b, stride=stride, is_valid=is_valid
            )
        # Reshape back to a  ``length x output_dim`` matrix
        output = operations.squeeze(output_img, 1)
        # Activation
        output = self.activation(output)
        # Final output
        return output


class Conv2D(ParametrizedLayer):
    """2D convolution

    Args:
        pc (:py:class:`dynet.ParameterCollection`): Parameter collection to
            hold the parameters
        num_channels (int): Number of channels in the input image
        num_kernels (int): Number of kernels (essentially the output dimension)
        kernel_size (list, optional): Default kernel size. This is a list of
            two elements, one per dimension.
        activation (function, optional): activation function
            (default: ``identity``)
        dropout (float, optional):  Dropout rate (default 0)
        nobias (bool, optional): Omit the bias (default ``False``)
        zero_padded (bool, optional): Default padding behaviour. Pad
            the image with zeros so that the output has the same width/height
            (default ``True``)
        strides (list, optional): Default stride along each dimension
            (list of size 2, defaults to ``[1, 1]``).
    """

    def __init__(
        self,
        pc,
        num_channels,
        num_kernels,
        kernel_size,
        activation=identity,
        dropout_rate=0.0,
        nobias=False,
        zero_padded=True,
        strides=None,
        K=None,
        b=None,
    ):
        super(Conv2D, self).__init__(pc, "conv2d")
        # Hyper-parameters
        self.num_channels = num_channels
        self.num_kernels = num_kernels
        self.kernel_size = kernel_size
        self.activation = activation
        self.dropout_rate = dropout_rate
        self.nobias = nobias
        self.zero_padded = zero_padded
        self.strides = util._default_value(strides, [1, 1])
        # Parameters
        # Filters have shape:
        #   kernel_height x kernel_width x num_channels x num_kernels
        self.add_parameters(
            "K",
            (
                self.kernel_size[0],
                self.kernel_size[1],
                self.num_channels,
                self.num_kernels
            ),
            param=K,
        )
        if not self.nobias:
            self.add_parameters(
                "b",
                self.num_kernels,
                param=b,
                init=ZeroInit(),
            )

    def __call__(self, x, strides=None, zero_padded=None):
        """Forward pass

        Args:
            x (:py:class:`dynet.Expression`): Input image (3-d tensor) or
                matrix.
            zero_padded (bool, optional): Pad the image with zeros so that the
                output has the same width/height. If this is not specified,
                the default specified in the constructor is used.
            strides (list, optional): Stride along width/height. If this is not
                specified, the default specified in the constructor is used.

        Returns:
            :py:class:`dynet.Expression`: Convolved image.
        """
        # Dropout
        x = util.conditional_dropout(x, self.dropout_rate, not self.test)
        # Retrieve convolution arguments
        is_valid = not (
            self.zero_padded if zero_padded is None else zero_padded
        )
        strides = util._default_value(strides, [None, None])
        strides = [
            strides[0] or self.strides[0] or 1,
            strides[1] or self.strides[1] or 1
        ]
        # Convolution
        if self.nobias:
            output = dy.conv2d(
                x, self.K, stride=strides, is_valid=is_valid
            )
        else:
            output = dy.conv2d_bias(
                x, self.K, self.b, stride=strides, is_valid=is_valid
            )
        # Activation
        output = self.activation(output)
        # Final output
        return output
