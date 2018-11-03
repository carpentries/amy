from rest_framework.test import APITestCase

from workshops.tests.base import DummySubTestWhenTestsLaunchedInParallelMixin


class APITestBase(DummySubTestWhenTestsLaunchedInParallelMixin, APITestCase):
    """Base class for AMY API test cases."""
