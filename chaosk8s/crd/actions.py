import json
import os.path
from typing import Any, Dict

import yaml
from chaoslib.exceptions import ActivityFailed
from chaoslib.types import Secrets
from kubernetes import client
from kubernetes.client.rest import ApiException
from logzero import logger

from chaosk8s import create_k8s_api_client

__all__ = [
    "create_custom_object",
    "delete_custom_object",
    "create_cluster_custom_object",
    "delete_cluster_custom_object",
    "patch_custom_object",
    "replace_custom_object",
    "patch_cluster_custom_object",
    "replace_cluster_custom_object",
    "apply_from_json",
    "apply_from_yaml",
]


def apply_from_json(resource: str = None, secrets: Secrets = None) -> Dict[str, Any]:
    """
    Apply the given custom resource, given as a JSON string, to the cluster.
    """
    obj = json.loads(resource)
    api_version = obj.get("apiVersion")
    kind = obj.get("kind")
    ns = obj.get("metadata", {}).get("namespace", "default")

    if not api_version:
        raise ActivityFailed("missing apiVersion in resource")

    if not kind:
        raise ActivityFailed("missing kind in resource")

    group, version = api_version.rsplit("/", 1)
    plural = get_plural(kind)

    return create_custom_object(group, version, plural, ns, resource, secrets=secrets)


def apply_from_yaml(resource: str = None, secrets: Secrets = None) -> Dict[str, Any]:
    """
    Apply the given custom resource, given as a YAML string, to the cluster.
    """
    obj = yaml.safe_load(resource)

    api_version = obj.get("apiVersion")
    kind = obj.get("kind")
    ns = obj.get("metadata", {}).get("namespace", "default")

    if not api_version:
        raise ActivityFailed("missing apiVersion in resource")

    if not kind:
        raise ActivityFailed("missing kind in resource")

    group, version = api_version.rsplit("/", 1)
    plural = get_plural(kind)

    return create_custom_object(group, version, plural, ns, resource, secrets=secrets)


def create_custom_object(
    group: str,
    version: str,
    plural: str,
    ns: str = "default",
    resource: Dict[str, Any] = None,
    resource_as_yaml_file: str = None,
    secrets: Secrets = None,
) -> Dict[str, Any]:
    """
    Create a custom object in the given namespace. Its custom resource
    definition must already exists or this will fail with a 404.

    Read more about custom resources here:
    https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
    """  # noqa: E501
    api = client.CustomObjectsApi(create_k8s_api_client(secrets))
    body = load_body(resource, resource_as_yaml_file)

    try:
        r = api.create_namespaced_custom_object(
            group, version, ns, plural, body, _preload_content=False
        )
        return json.loads(r.data)
    except ApiException as x:
        if x.status == 409:
            logger.debug(f"Custom resource object {group}/{version} already exists")
            return json.loads(x.body)
        else:
            raise ActivityFailed(
                f"Failed to create custom resource object: '{x.reason}' {x.body}"
            )


def delete_custom_object(
    group: str,
    version: str,
    plural: str,
    name: str,
    ns: str = "default",
    secrets: Secrets = None,
) -> Dict[str, Any]:
    """
    Create a custom object cluster wide. Its custom resource
    definition must already exists or this will fail with a 404.

    Read more about custom resources here:
    https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
    """  # noqa: E501
    api = client.CustomObjectsApi(create_k8s_api_client(secrets))

    try:
        r = api.delete_namespaced_custom_object(
            group, version, ns, plural, name, _preload_content=False
        )
        return json.loads(r.data)
    except ApiException as x:
        raise ActivityFailed(
            f"Failed to delete custom resource object: '{x.reason}' {x.body}"
        )


def create_cluster_custom_object(
    group: str,
    version: str,
    plural: str,
    resource: Dict[str, Any] = None,
    resource_as_yaml_file: str = None,
    secrets: Secrets = None,
) -> Dict[str, Any]:
    """
    Delete a custom object in the given namespace.

    Read more about custom resources here:
    https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
    """  # noqa: E501
    api = client.CustomObjectsApi(create_k8s_api_client(secrets))
    body = load_body(resource, resource_as_yaml_file)

    try:
        r = api.create_cluster_custom_object(
            group, version, plural, body, _preload_content=False
        )
        return json.loads(r.data)
    except ApiException as x:
        if x.status == 409:
            logger.debug(f"Custom resource object {group}/{version} already exists")
            return json.loads(x.body)
        else:
            raise ActivityFailed(
                "Failed to create custom resource object: '{x.reason}' {x.body}"
            )


def delete_cluster_custom_object(
    group: str, version: str, plural: str, name: str, secrets: Secrets = None
) -> Dict[str, Any]:
    """
    Delete a custom object cluster wide.

    Read more about custom resources here:
    https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
    """  # noqa: E501
    api = client.CustomObjectsApi(create_k8s_api_client(secrets))

    try:
        r = api.delete_cluster_custom_object(
            group, version, plural, name, _preload_content=False
        )
        return json.loads(r.data)
    except ApiException as x:
        raise ActivityFailed(
            f"Failed to delete custom resource object: '{x.reason}' {x.body}"
        )


def patch_custom_object(
    group: str,
    version: str,
    plural: str,
    name: str,
    ns: str = "default",
    force: bool = False,
    resource: Dict[str, Any] = None,
    resource_as_yaml_file: str = None,
    secrets: Secrets = None,
) -> Dict[str, Any]:
    """
    Patch a custom object in the given namespace. The resource must be the
    updated version to apply. Force will re-acquire conflicting fields
    owned by others.

    The resource, or resource_as_yaml_file, must be a JSON Patch document.

    Read more about custom resources here:
    https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
    """  # noqa: E501
    api = client.CustomObjectsApi(create_k8s_api_client(secrets))
    body = load_body(resource, resource_as_yaml_file)

    try:
        # https://github.com/kubernetes-client/python/issues/1216
        api.api_client.set_default_header("Content-Type", "application/json-patch+json")
        r = api.patch_namespaced_custom_object(
            group, version, ns, plural, name, body, _preload_content=False
        )
        return json.loads(r.data)
    except ApiException as x:
        raise ActivityFailed(
            f"Failed to patch custom resource object: '{x.reason}' {x.body}"
        )


def replace_custom_object(
    group: str,
    version: str,
    plural: str,
    name: str,
    ns: str = "default",
    force: bool = False,
    resource: Dict[str, Any] = None,
    resource_as_yaml_file: str = None,
    secrets: Secrets = None,
) -> Dict[str, Any]:
    """
    Replace a custom object in the given namespace. The resource must be the
    new version to apply.

    Read more about custom resources here:
    https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
    """  # noqa: E501
    api = client.CustomObjectsApi(create_k8s_api_client(secrets))
    body = load_body(resource, resource_as_yaml_file)

    try:
        r = api.replace_namespaced_custom_object(
            group, version, ns, plural, name, body, force=force, _preload_content=False
        )
        return json.loads(r.data)
    except ApiException as x:
        raise ActivityFailed(
            f"Failed to replace custom resource object: '{x.reason}' {x.body}"
        )


def patch_cluster_custom_object(
    group: str,
    version: str,
    plural: str,
    name: str,
    force: bool = False,
    resource: Dict[str, Any] = None,
    resource_as_yaml_file: str = None,
    secrets: Secrets = None,
) -> Dict[str, Any]:
    """
    Patch a custom object cluster-wide. The resource must be the
    updated version to apply. Force will re-acquire conflicting fields
    owned by others.

    The resource, or resource_as_yaml_file, must be a JSON Patch document.

    Read more about custom resources here:
    https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
    """  # noqa: E501
    api = client.CustomObjectsApi(create_k8s_api_client(secrets))
    body = load_body(resource, resource_as_yaml_file)

    try:
        # https://github.com/kubernetes-client/python/issues/1216
        api.api_client.set_default_header("Content-Type", "application/json-patch+json")
        r = api.patch_cluster_custom_object(
            group, version, plural, name, body, _preload_content=False
        )
        return json.loads(r.data)
    except ApiException as x:
        raise ActivityFailed(
            f"Failed to patch custom resource object: '{x.reason}' {x.body}"
        )


def replace_cluster_custom_object(
    group: str,
    version: str,
    plural: str,
    name: str,
    force: bool = False,
    resource: Dict[str, Any] = None,
    resource_as_yaml_file: str = None,
    secrets: Secrets = None,
) -> Dict[str, Any]:
    """
    Replace a custom object in the given namespace. The resource must be the
    new version to apply.

    Read more about custom resources here:
    https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/
    """  # noqa: E501
    api = client.CustomObjectsApi(create_k8s_api_client(secrets))
    body = load_body(resource, resource_as_yaml_file)

    try:
        r = api.replace_cluster_custom_object(
            group, version, plural, name, body, force=force, _preload_content=False
        )
        return json.loads(r.data)
    except ApiException as x:
        raise ActivityFailed(
            f"Failed to replace custom resource object: '{x.reason}' {x.body}"
        )


###############################################################################
# Internal functions
###############################################################################
def load_body(
    body_as_object: Dict[str, Any] = None, body_as_yaml_file: str = None
) -> Dict[str, Any]:
    if (body_as_object is None) and (not body_as_yaml_file):
        raise ActivityFailed(
            "Either `body_as_object` or `body_as_yaml_file` must be set"
        )

    if body_as_object is not None:
        return body_as_object

    if not os.path.isfile(body_as_yaml_file):
        raise ActivityFailed(f"Path '{body_as_yaml_file}' is not a valid resource file")
    else:
        with open(body_as_yaml_file) as f:
            return yaml.safe_load(f.read())


# https://github.com/kubernetes/kubernetes/blob/v1.28.2/staging/src/k8s.io/apimachinery/pkg/api/meta/restmapper.go#L126
def get_plural(singular: str) -> str:
    singular = singular.lower()

    if singular == "endpoints":
        return singular

    last = singular[-1]
    if last == "s":
        return singular + "es"
    elif last == "y":
        return singular[:-1] + "ies"

    return singular + "s"
