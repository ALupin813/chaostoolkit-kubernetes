# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from chaoslib.exceptions import FailedProbe
from kubernetes import client, config
import pytest

from chaosk8s.probes import all_microservices_healthy, \
    microservice_available_and_healthy, microservice_is_not_available


@patch('chaosk8s.probes.client', autospec=True)
@patch('chaosk8s.probes.config', autospec=True)
def test_unhealthy_system_should_be_reported(config, client):
    pod = MagicMock()
    pod.status.phase = "Failed"

    result = MagicMock()
    result.items = [pod]

    v1 = MagicMock()
    v1.list_namespaced_pod.return_value = result
    client.CoreV1Api.return_value = v1

    with pytest.raises(FailedProbe) as excinfo:
        all_microservices_healthy()
    assert "the system is unhealthy" in str(excinfo)


@patch('chaosk8s.probes.client', autospec=True)
@patch('chaosk8s.probes.config', autospec=True)
def test_expecting_a_healthy_microservice_should_be_reported_when_not(config,
                                                                      client):
    result = MagicMock()
    result.items = []

    v1 = MagicMock()
    v1.list_namespaced_deployment.return_value = result
    client.AppsV1beta1Api.return_value = v1

    with pytest.raises(FailedProbe) as excinfo:
        microservice_available_and_healthy("mysvc")
    assert "microservice 'mysvc' was not found" in str(excinfo)

    deployment = MagicMock()
    deployment.spec.replicas = 2
    deployment.status.available_replicas = 1
    result.items.append(deployment)

    with pytest.raises(FailedProbe) as excinfo:
        microservice_available_and_healthy("mysvc")
    assert "microservice 'mysvc' is not healthy" in str(excinfo)


@patch('chaosk8s.probes.client', autospec=True)
@patch('chaosk8s.probes.config', autospec=True)
def test_expecting_microservice_is_there_when_it_should_not(config, client):
    deployment = MagicMock()
    result = MagicMock()
    result.items = [deployment]

    v1 = MagicMock()
    v1.list_namespaced_deployment.return_value = result
    client.AppsV1beta1Api.return_value = v1

    with pytest.raises(FailedProbe) as excinfo:
        microservice_is_not_available("mysvc")
    assert "microservice 'mysvc' looks healthy" in str(excinfo)
