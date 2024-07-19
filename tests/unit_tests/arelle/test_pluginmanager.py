"""Tests for the PluginManager module."""
from __future__ import annotations

import os
from unittest.mock import Mock

import pytest

from arelle import PluginManager
from arelle.Cntlr import Cntlr
from arelle.core.plugins.CorePluginContext import _get_name_dir_prefix


def test_plugin_manager_init_first_pass():
    """
    Test that _plugin_config is correctly setup during init on fresh pass
    """
    cntlr = Mock(pluginDir='some_dir')
    PluginManager.init(cntlr, loadPluginConfig=False)
    plugin_context = PluginManager.getContext()
    assert len(plugin_context._plugin_config) == 2
    assert 'modules' in plugin_context._plugin_config
    assert isinstance(plugin_context._plugin_config.get('modules'), dict)
    assert len(plugin_context._plugin_config.get('modules')) == 0
    assert 'classes' in plugin_context._plugin_config
    assert isinstance(plugin_context._plugin_config.get('classes'), dict)
    assert len(plugin_context._plugin_config.get('classes')) == 0
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    assert plugin_context.get_controller() == cntlr


def test_plugin_manager_init_config_already_exists():
    """
    Test that _plugin_config is correctly setup during init on a second pass
    """
    cntlr = Mock(pluginDir='some_dir')
    PluginManager.init(cntlr, loadPluginConfig=False)
    PluginManager.close()
    PluginManager.init(cntlr, loadPluginConfig=False)
    plugin_context = PluginManager.getContext()
    assert len(plugin_context._plugin_config) == 2
    assert 'modules' in plugin_context._plugin_config
    assert isinstance(plugin_context._plugin_config.get('modules'), dict)
    assert len(plugin_context._plugin_config.get('modules')) == 0
    assert 'classes' in plugin_context._plugin_config
    assert isinstance(plugin_context._plugin_config.get('classes'), dict)
    assert len(plugin_context._plugin_config.get('classes')) == 0
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    assert plugin_context.get_controller() == cntlr


def test_plugin_manager_close():
    """
    Test that _plugin_config, _module_plugin_infos and _methods are cleared when close is called
    """
    cntlr = Mock(pluginDir='some_dir')
    PluginManager.init(cntlr, loadPluginConfig=False)
    plugin_context = PluginManager.getContext()
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    plugin_context._module_plugin_infos['module'] = 'plugin_info'
    plugin_context._methods['class'] = 'plugin_method'
    PluginManager.close()
    plugin_context = PluginManager.getContext()
    assert len(plugin_context._plugin_config) == 0
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    assert plugin_context.get_controller() == cntlr


def test_plugin_manager_reset():
    """
    Test that _module_plugin_infos and _methods are cleared when close is called, _plugin_config remains unchanged
    """
    cntlr = Mock(pluginDir='some_dir')
    PluginManager.init(cntlr, loadPluginConfig=False)
    plugin_context = PluginManager.getContext()
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    plugin_context._module_plugin_infos['module'] = 'plugin_info'
    plugin_context._methods['class'] = 'plugin_method'
    PluginManager.reset()
    plugin_context = PluginManager.getContext()
    assert len(plugin_context._plugin_config) == 2
    assert len(plugin_context._module_plugin_infos) == 0
    assert len(plugin_context._methods) == 0
    assert plugin_context.get_controller() == cntlr


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

    cntlr = Controller()

    moduleName, moduleDir, packageImportPrefix = _get_name_dir_prefix(
        controller=cntlr,
        pluginBase=Controller.pluginDir,
        moduleURL=test_data[1],
        packagePrefix=test_data[2],
    )

    assert moduleName == expected_result[0]
    assert moduleDir == (None if expected_result[1] is None else os.path.normcase(expected_result[1]))
    assert packageImportPrefix == expected_result[2]

    PluginManager.close()


def teardown_function():
    PluginManager.close()
