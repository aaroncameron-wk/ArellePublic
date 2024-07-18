"""Tests for the plugin_context module."""
from __future__ import annotations
import os
import sys
from importlib.metadata import EntryPoint
from typing import Any

import pytest
from unittest.mock import Mock

from arelle.Cntlr import Cntlr
from arelle.core.plugins.CorePluginContext import CorePluginContext, _get_name_dir_prefix
from arelle.services.plugins.EntryPointRef import EntryPointRef
from arelle.services.plugins.PluginLocator import PluginLocator
from arelle.services.plugins.PluginParser import PluginParser


class MockEntryPoint(Mock):

    def __init__(self, name, **kwargs: Any):
        super().__init__(**kwargs)
        self._name = name

    def load(self):
        def _load():
            return self._name
        return _load


_MODULE_INFO_MAP = {
    'plugin1': {
        'classMethods': ['Method', 'Method1'],
        'importURLs': [],
        'moduleImports': [],
        'name': 'plugin1',
    },
    'plugin2': {
        'classMethods': ['Method', 'Method2'],
        'importURLs': [],
        'moduleImports': [],
        'name': 'plugin2',
    }
}

_ENTRY_POINT_REF_MAP = {
    name: EntryPointRef({name}, MockEntryPoint(name), name, module_info)
    for name, module_info in _MODULE_INFO_MAP.items()
}


class MockPluginLocator(PluginLocator):

    def get(self, plugin_base: str, search: str) -> EntryPointRef | None:
        return _ENTRY_POINT_REF_MAP.get(search)

    def normalize_module_filename(self, moduleFilename: str) -> str | None:
        return moduleFilename


class MockPluginParser(PluginParser):

    def parse_plugin_info(
        self,
        moduleURL: str,
        moduleFilename: str,
        entryPoint: EntryPoint | None,
    ) -> dict[str, Any] | None:
        return _MODULE_INFO_MAP.get(moduleFilename)


def _create_controller():
    return Mock(pluginDir='some_dir')


def _create_plugin_context(cntlr):
    cntlr = cntlr or _create_controller()
    plugin_context = CorePluginContext(cntlr, MockPluginLocator(), MockPluginParser())
    plugin_context.init(loadPluginConfig=False)
    return plugin_context


def test_plugin_context_init_first_pass():
    """
    Test that pluginConfig is correctly setup during init on fresh pass
    """
    controller = _create_controller()
    plugin_context = _create_plugin_context(controller)
    assert len(plugin_context._plugin_config) == 2
    assert 'modules' in plugin_context._plugin_config
    assert isinstance(plugin_context._plugin_config.get('modules'), dict)
    assert len(plugin_context._plugin_config.get('modules')) == 0
    assert 'classes' in plugin_context._plugin_config
    assert isinstance(plugin_context._plugin_config.get('classes'), dict)
    assert len(plugin_context._plugin_config.get('classes')) == 0
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    assert plugin_context.get_controller() == controller
    plugin_context.close()


def test_plugin_context_init_config_already_exists():
    """
    Test that pluginConfig is correctly setup during init on a second pass
    """
    controller = _create_controller()
    plugin_context = _create_plugin_context(controller)
    plugin_context.close()
    plugin_context.init(loadPluginConfig=False)
    assert len(plugin_context._plugin_config) == 2
    assert 'modules' in plugin_context._plugin_config
    assert isinstance(plugin_context._plugin_config.get('modules'), dict)
    assert len(plugin_context._plugin_config.get('modules')) == 0
    assert 'classes' in plugin_context._plugin_config
    assert isinstance(plugin_context._plugin_config.get('classes'), dict)
    assert len(plugin_context._plugin_config.get('classes')) == 0
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    assert plugin_context.get_controller() == controller
    plugin_context.close()


def test_plugin_context_close():
    """
    Test that pluginConfig, _module_plugin_infos and _methods are cleared when close is called
    """
    controller = _create_controller()
    plugin_context = _create_plugin_context(controller)
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    plugin_context._module_plugin_infos['module'] = 'plugin_info'
    plugin_context._methods['class'] = 'plugin_method'
    plugin_context.close()
    assert len(plugin_context._plugin_config) == 0
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    assert plugin_context.get_controller() == controller
    plugin_context.close()


def test_plugin_context_reset():
    """
    Test that _module_plugin_infos and _methods are cleared when close is called, pluginConfig remains unchanged
    """
    controller = _create_controller()
    plugin_context = _create_plugin_context(controller)
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    plugin_context._module_plugin_infos['module'] = 'plugin_info'
    plugin_context._methods['class'] = 'plugin_method'
    plugin_context.reset()
    assert len(plugin_context._plugin_config) == 2
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    assert plugin_context.get_controller() == controller
    plugin_context.close()


def test_plugin_contexts_concurrent():
    """
    Test that two plugin contexts can exist and manage their plugins concurrently.
    """
    controller = _create_controller()
    plugin_context1 = _create_plugin_context(controller)
    plugin_context1.add_plugin_module('plugin1')
    plugin_context2 = _create_plugin_context(controller)
    plugin_context2.add_plugin_module('plugin2')
    assert list(plugin_context1._plugin_config['modules']) == ['plugin1']
    assert list(plugin_context1._plugin_config['classes']) == ['Method', 'Method1']
    assert list(plugin_context2._plugin_config['modules']) == ['plugin2']
    assert list(plugin_context2._plugin_config['classes']) == ['Method', 'Method2']
    plugin_context1.close()
    plugin_context2.close()


@pytest.mark.parametrize(
    "test_data, expected_result",
    [
        # Test case 1
        (
            # Test data
            ("tests/unit_tests/arelle", "functionsMaths", "xyz"),
            # Expected result
            ("functionsMaths", "tests/unit_tests", "xyz")
        ),
        # Test case 2
        (
            # Test data
            ("arelle/plugin/", "xbrlDB/__init__.py", "xyz"),
            # Expected result
            ("xbrlDB", "arelle/plugin", "xbrlDB.")
        ),
        # Test case 3
        (
            # Test data
            ("plugin/xbrlDB", None, "xyz"),
            # Expected result
            (None, None, None)
        ),
    ]
)
def test_function_get_name_dir_prefix(
    test_data: tuple[str, str, str],
    expected_result: tuple[str, str, str],
):
    """Test util function get_name_dir_prefix."""
    class Controller(Cntlr):
        """Controller."""

        pluginDir = test_data[0]

        def __init__(self) -> None:
            """Init controller with logging."""
            super().__init__(logFileName="logToBuffer")

    controller = Controller()
    plugin_context = _create_plugin_context(controller)

    moduleName, moduleDir, packageImportPrefix = _get_name_dir_prefix(
        controller=controller,
        pluginBase=Controller.pluginDir,
        moduleURL=test_data[1],
        packagePrefix=test_data[2],
    )

    assert moduleName == expected_result[0]
    assert moduleDir == (None if expected_result[1] is None else os.path.normcase(expected_result[1]))
    assert packageImportPrefix == expected_result[2]
    plugin_context.close()


def test_function_loadModule():
    """
    Test helper function loadModule.

    This test asserts that a plugin module is loaded when running
    the function.
    """

    class Controller(Cntlr):
        """Controller."""

        pluginDir = "tests/unit_tests/arelle"

        def __init__(self) -> None:
            """Init controller with logging."""
            super().__init__(logFileName="logToBuffer")

    controller = Controller()
    plugin_context = _create_plugin_context(controller)

    plugin_context._load_module(
        moduleInfo={
            "name": "mock",
            "moduleURL": "functionsMath",
        }
    )

    all_modules_list: list[str] = [m.__name__ for m in sys.modules.values() if m]

    assert "arelle.formula.XPathContext" in all_modules_list
    assert "arelle.FunctionUtil" in all_modules_list
    assert "arelle.FunctionXs" in all_modules_list
    assert "isodate.isoduration" in all_modules_list
    assert "functionsMath" in all_modules_list

    plugin_context.close()
