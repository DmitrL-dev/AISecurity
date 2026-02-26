"""Tests for Value autograd engine."""

from micro_swarm.autograd import Value


class TestValueBasicOps:
    """Basic arithmetic operations."""

    def test_add(self):
        a = Value(2.0)
        b = Value(3.0)
        c = a + b
        assert c.data == 5.0

    def test_add_scalar(self):
        a = Value(2.0)
        c = a + 3.0
        assert c.data == 5.0

    def test_mul(self):
        a = Value(2.0)
        b = Value(3.0)
        c = a * b
        assert c.data == 6.0

    def test_mul_scalar(self):
        a = Value(4.0)
        c = a * 2.0
        assert c.data == 8.0

    def test_pow(self):
        a = Value(3.0)
        c = a ** 2
        assert abs(c.data - 9.0) < 1e-6

    def test_neg(self):
        a = Value(5.0)
        c = -a
        assert c.data == -5.0

    def test_sub(self):
        a = Value(5.0)
        b = Value(3.0)
        c = a - b
        assert abs(c.data - 2.0) < 1e-6

    def test_div(self):
        a = Value(6.0)
        b = Value(3.0)
        c = a / b
        assert abs(c.data - 2.0) < 1e-6

    def test_radd(self):
        a = Value(3.0)
        c = 2.0 + a
        assert c.data == 5.0

    def test_rmul(self):
        a = Value(3.0)
        c = 2.0 * a
        assert c.data == 6.0


class TestValueActivations:
    """Activation functions."""

    def test_relu_positive(self):
        a = Value(3.0)
        c = a.relu()
        assert c.data == 3.0

    def test_relu_negative(self):
        a = Value(-3.0)
        c = a.relu()
        assert c.data == 0.0

    def test_sigmoid_zero(self):
        a = Value(0.0)
        c = a.sigmoid()
        assert abs(c.data - 0.5) < 1e-6

    def test_sigmoid_range(self):
        for x in [-10, -1, 0, 1, 10]:
            c = Value(float(x)).sigmoid()
            assert 0.0 <= c.data <= 1.0

    def test_exp(self):
        a = Value(1.0)
        c = a.exp()
        assert abs(c.data - 2.718281828) < 1e-4

    def test_log(self):
        a = Value(1.0)
        c = a.log()
        assert abs(c.data) < 1e-6  # log(1) = 0


class TestValueGradients:
    """Gradient computation via backward."""

    def test_simple_grad(self):
        a = Value(2.0)
        b = Value(3.0)
        c = a * b
        c.backward()
        assert a.grad == 3.0  # dc/da = b
        assert b.grad == 2.0  # dc/db = a

    def test_chain_grad(self):
        a = Value(2.0)
        b = Value(3.0)
        c = a * b
        d = c + a
        d.backward()
        assert a.grad == 4.0  # dc/da = b + 1 = 4
        assert b.grad == 2.0  # dc/db = a = 2

    def test_sigmoid_grad(self):
        a = Value(0.0)
        s = a.sigmoid()
        s.backward()
        # sigmoid'(0) = 0.25
        assert abs(a.grad - 0.25) < 1e-6

    def test_relu_grad_positive(self):
        a = Value(3.0)
        r = a.relu()
        r.backward()
        assert a.grad == 1.0

    def test_relu_grad_negative(self):
        a = Value(-3.0)
        r = a.relu()
        r.backward()
        assert a.grad == 0.0

    def test_repr(self):
        a = Value(3.14)
        assert "3.14" in repr(a)
