"""Value — scalar autograd engine for MicroModel Swarm.

Pure Python reverse-mode automatic differentiation.
Inspired by Karpathy's micrograd with minor optimizations.
"""

from __future__ import annotations

import math


class Value:
    """Scalar value with autograd support.

    Tracks computation graph and computes gradients via backprop.
    Adapted from Karpathy's micrograd with minor optimizations.
    """

    __slots__ = ("data", "grad", "_children", "_local_grads")

    def __init__(
        self,
        data: float,
        children: tuple["Value", ...] = (),
        local_grads: tuple[float, ...] = (),
    ) -> None:
        self.data = data
        self.grad = 0.0
        self._children = children
        self._local_grads = local_grads

    def __add__(self, other: "Value | float") -> "Value":
        other = other if isinstance(other, Value) else Value(float(other))
        return Value(self.data + other.data, (self, other), (1.0, 1.0))

    def __mul__(self, other: "Value | float") -> "Value":
        other = other if isinstance(other, Value) else Value(float(other))
        return Value(
            self.data * other.data, (self, other), (other.data, self.data)
        )

    def __pow__(self, other: float) -> "Value":
        return Value(
            self.data**other,
            (self,),
            (other * self.data ** (other - 1),),
        )

    def log(self) -> "Value":
        return Value(
            math.log(self.data + 1e-10), (self,), (1.0 / (self.data + 1e-10),)
        )

    def exp(self) -> "Value":
        e = math.exp(min(self.data, 50.0))  # clamp to avoid overflow
        return Value(e, (self,), (e,))

    def relu(self) -> "Value":
        return Value(max(0.0, self.data), (self,), (float(self.data > 0),))

    def sigmoid(self) -> "Value":
        s = 1.0 / (1.0 + math.exp(-max(-50.0, min(50.0, self.data))))
        return Value(s, (self,), (s * (1 - s),))

    def __neg__(self) -> "Value":
        return self * -1

    def __radd__(self, other: float) -> "Value":
        return self + other

    def __sub__(self, other: "Value | float") -> "Value":
        return self + (-other)

    def __rsub__(self, other: float) -> "Value":
        return Value(float(other)) + (-self)

    def __rmul__(self, other: float) -> "Value":
        return self * other

    def __truediv__(self, other: "Value | float") -> "Value":
        other = other if isinstance(other, Value) else Value(float(other))
        return self * other ** -1

    def __rtruediv__(self, other: float) -> "Value":
        return Value(float(other)) * self ** -1

    def backward(self) -> None:
        """Compute gradients via reverse-mode autodiff."""
        topo: list[Value] = []
        visited: set[int] = set()

        def _build(v: Value) -> None:
            vid = id(v)
            if vid not in visited:
                visited.add(vid)
                for child in v._children:
                    _build(child)
                topo.append(v)

        _build(self)
        self.grad = 1.0
        for v in reversed(topo):
            for child, lg in zip(v._children, v._local_grads):
                child.grad += lg * v.grad

    def __repr__(self) -> str:
        return f"Value({self.data:.4f}, grad={self.grad:.4f})"
