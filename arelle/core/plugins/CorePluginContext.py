"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

import gettext
import importlib
import importlib.util
import io
import json
import logging
import os
import sys
import time
import traceback
import types
from collections import OrderedDict
from importlib.metadata import EntryPoint
from pathlib import Path
from typing import Any, Iterator, Callable, TYPE_CHECKING

from arelle.Locale import getLanguageCodes
from arelle.UrlUtil import isAbsolute
from arelle.services.plugins import PluginParser
from arelle.services.plugins.EntryPointRef import EntryPointRef
from arelle.services.plugins.PluginContext import PluginContext
from arelle.services.plugins.PluginLocator import PluginLocator

if TYPE_CHECKING:
    from arelle.Cntlr import Cntlr

_ERROR_MESSAGE_IMPORT_TEMPLATE = "Unable to load module {}"
PLUGIN_TRACE_FILE: str | None = None  # "c:/temp/pluginerr.txt"
PLUGIN_TRACE_LEVEL = logging.WARNING


def _get_name_dir_prefix(
        controller: Cntlr,
        pluginBase: str,
        moduleURL: str,
        packagePrefix: str = "",
) -> tuple[str, str, str] | tuple[None, None, None]:
    """Get the name, directory and prefix of a module."""
    moduleFilename: str
    moduleDir: str
    packageImportPrefix: str

    moduleFilename = controller.webCache.getfilename(
        url=moduleURL, normalize=True, base=pluginBase
    )

    if moduleFilename:
        if os.path.basename(moduleFilename) == "__init__.py" and os.path.isfile(
                moduleFilename
        ):
            moduleFilename = os.path.dirname(
                moduleFilename
            )  # want just the dirpart of package

        if os.path.isdir(moduleFilename) and os.path.isfile(
                os.path.join(moduleFilename, "__init__.py")
        ):
            moduleDir = os.path.dirname(moduleFilename)
            moduleName = os.path.basename(moduleFilename)
            packageImportPrefix = moduleName + "."
        else:
            moduleName = os.path.basename(moduleFilename).partition(".")[0]
            moduleDir = os.path.dirname(moduleFilename)
            packageImportPrefix = packagePrefix

        return moduleName, moduleDir, packageImportPrefix

    return None, None, None


def _get_location(moduleDir: str, moduleName: str) -> Path:
    """Get the file name of a plugin."""
    module_name_path = Path(f"{moduleDir}/{moduleName}.py")
    if os.path.isfile(module_name_path):
        return module_name_path

    return Path(f"{moduleDir}/{moduleName}/__init__.py")


def _find_and_load_module(moduleDir: str, moduleName: str) -> types.ModuleType | None:
    """Load a module based on name and directory."""
    location = _get_location(moduleDir=moduleDir, moduleName=moduleName)
    spec = importlib.util.spec_from_file_location(name=moduleName, location=location)

    # spec_from_file_location returns ModuleSpec or None.
    # spec.loader returns Loader or None.
    # We want to make sure neither of them are None before proceeding
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError("Unable to load module")

    module = importlib.util.module_from_spec(spec)
    sys.modules[moduleName] = module  # This line is required before exec_module
    spec.loader.exec_module(sys.modules[moduleName])

    return sys.modules[moduleName]


class CorePluginContext(PluginContext):
    def __init__(self, cntlr: Cntlr, plugin_locator: PluginLocator, plugin_parser: PluginParser):
        self._controller = cntlr
        self._plugin_locator = plugin_locator
        self._plugin_parser = plugin_parser
        self._json_file = None
        self._plugin_config = None
        self._plugin_config_changed = False
        self._trace_file_logger = None
        self._module_plugin_infos = {}
        self._methods = {}
        self._plugin_base = None

    def _create_module_info(self, entry_point_ref: EntryPointRef | None, filename: str | None = None) -> dict | None:
        """
        Creates a module information dictionary from the entry point ref.
        :return: A module inforomation dictionary
        """
        if entry_point_ref is not None:
            if entry_point_ref.entryPoint is not None:
                return self.generate_module_info(entryPoint=entry_point_ref.entryPoint)
            return self.generate_module_info(moduleURL=entry_point_ref.moduleFilename)
        return self.generate_module_info(moduleURL=filename)

    def init(self, loadPluginConfig: bool = True) -> None:
        if PLUGIN_TRACE_FILE:
            self._trace_file_logger = logging.getLogger(__name__)
            self._trace_file_logger.propagate = False
            handler = logging.FileHandler(PLUGIN_TRACE_FILE)
            formatter = logging.Formatter('%(asctime)s.%(msecs)03dz [%(levelname)s] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')
            handler.setFormatter(formatter)
            handler.setLevel(PLUGIN_TRACE_LEVEL)
            self._trace_file_logger.addHandler(handler)
        self._plugin_config_changed = False
        self._plugin_base = self._controller.pluginDir + os.sep
        if loadPluginConfig:
            try:
                self._json_file = self._controller.userAppDir + os.sep + "plugins.json"
                with io.open(self._json_file, 'rt', encoding='utf-8') as f:
                    self._plugin_config = json.load(f)
                self._freshen_module_infos()
            except Exception:
                pass  # on GAE no userAppDir, will always come here
        if not self._plugin_config:
            self._plugin_config = {  # savable/reloadable plug in configuration
                "modules": {},  # dict of moduleInfos by module name
                "classes": {}  # dict by class name of list of class modules in execution order
            }
            self._plugin_config_changed = False  # don't save until something is added to pluginConfig
        self._module_plugin_infos = {}  # dict of loaded module pluginInfo objects by module names
        self._methods = {}  # dict by class of list of ordered callable function objects

    def reset(self) -> None:
        if self._module_plugin_infos:
            self._module_plugin_infos.clear()  # dict of loaded module pluginInfo objects by module names
        if self._methods:
            self._methods.clear()  # dict by class of list of ordered callable function objects

    def _ordered_plugin_config(self):
        index_map = {
            'name': '01',
            'status': '02',
            'version': '03',
            'fileDate': '04',
            'description': '05',
            'moduleURL': '06',
            'localeURL': '07',
            'localeDomain': '08',
            'license': '09',
            'author': '10',
            'copyright': '11',
            'classMethods': '12'
        }
        modules_dict = OrderedDict(
            (
                moduleName,
                OrderedDict(sorted(moduleInfo.items(), key=lambda k: index_map.get(k[0], k[0])))
            )
            for moduleName, moduleInfo in sorted(self._plugin_config['modules'].items())
        )
        classes_dict = OrderedDict(sorted(self._plugin_config['classes'].items()))
        return OrderedDict((
            ('modules', modules_dict),
            ('classes', classes_dict)
        ))

    def save(self, cntlr) -> None:
        # TODO: Should probably be using self._controller?
        if self._plugin_config_changed and cntlr.hasFileSystem and not cntlr.disablePersistentConfig:
            self._json_file = cntlr.userAppDir + os.sep + "plugins.json"
            with io.open(self._json_file, 'wt', encoding='utf-8') as f:
                jsonStr = str(json.dumps(self._ordered_plugin_config(), ensure_ascii=False, indent=2))  # might not be unicode in 2.7
                f.write(jsonStr)
            self._plugin_config_changed = False

    def close(self):
        self._plugin_config.clear()
        self._module_plugin_infos.clear()
        self._methods.clear()

    def _log_plugin_trace(self, message: str, level: int) -> None:
        """
        If plugin trace file logging is configured, logs `message` to it.
        Only logs to controller logger if log is an error.
        :param message: Message to be logged
        :param level: Log level of message (e.g. logging.INFO)
        """
        if self._trace_file_logger:
            self._trace_file_logger.log(level, message)
        if level >= logging.ERROR:
            self._controller.addToLog(message=message, level=level, messageCode='arelle:pluginLoadingError')

    def modules_with_newer_file_dates(self):
        names = set()
        for moduleName, moduleInfo in self._plugin_config["modules"].items():
            freshenedFilename = self._controller.webCache.getfilename(moduleInfo["moduleURL"], checkModifiedTime=True, normalize=True, base=self._plugin_base)
            try:
                if os.path.isdir(freshenedFilename):  # if freshenedFilename is a directory containing an __init__.py file, open that instead
                    if os.path.isfile(os.path.join(freshenedFilename, "__init__.py")):
                        freshenedFilename = os.path.join(freshenedFilename, "__init__.py")
                elif not freshenedFilename.endswith(".py") and not os.path.exists(freshenedFilename) and os.path.exists(freshenedFilename + ".py"):
                    freshenedFilename += ".py"  # extension module without .py suffix
                if os.path.exists(freshenedFilename):
                    if moduleInfo["fileDate"] < time.strftime('%Y-%m-%dT%H:%M:%S UTC', time.gmtime(os.path.getmtime(freshenedFilename))):
                        names.add(moduleInfo["name"])
                else:
                    _msg = _("File not found for '{name}' plug-in when checking for updated module info. Path: '{path}'") \
                        .format(name=moduleName, path=freshenedFilename)
                    self._log_plugin_trace(_msg, logging.ERROR)
            except Exception as err:
                _msg = _("Exception at plug-in method modulesWithNewerFileDates: {error}").format(error=err)
                self._log_plugin_trace(_msg, logging.ERROR)
        return names

    def _freshen_module_infos(self):
        # for modules with different date-times, re-load module info
        missingEnabledModules = []
        for moduleName, moduleInfo in self._plugin_config["modules"].items():
            moduleEnabled = moduleInfo["status"] == "enabled"
            freshenedFilename = self._controller.webCache.getfilename(moduleInfo["moduleURL"], checkModifiedTime=True, normalize=True, base=self._plugin_base)
            try:  # check if moduleInfo cached may differ from referenced moduleInfo
                if os.path.isdir(freshenedFilename):  # if freshenedFilename is a directory containing an __ini__.py file, open that instead
                    if os.path.isfile(os.path.join(freshenedFilename, "__init__.py")):
                        freshenedFilename = os.path.join(freshenedFilename, "__init__.py")
                elif not freshenedFilename.endswith(".py") and not os.path.exists(freshenedFilename) and os.path.exists(freshenedFilename + ".py"):
                    freshenedFilename += ".py"  # extension module without .py suffix
                if os.path.exists(freshenedFilename):
                    if moduleInfo["fileDate"] != time.strftime('%Y-%m-%dT%H:%M:%S UTC', time.gmtime(os.path.getmtime(freshenedFilename))):
                        freshenedModuleInfo = self.generate_module_info(moduleURL=moduleInfo["moduleURL"], reload=True)
                        if freshenedModuleInfo is not None:
                            if freshenedModuleInfo["name"] == moduleName:
                                self._plugin_config["modules"][moduleName] = freshenedModuleInfo
                            else:
                                # Module has been re-named
                                if moduleEnabled:
                                    missingEnabledModules.append(moduleName)
                # User can avoid pruning by disabling plugin
                elif moduleEnabled:
                    missingEnabledModules.append(moduleName)
                else:
                    _msg = _("File not found for '{name}' plug-in when attempting to update module info. Path: '{path}'") \
                        .format(name=moduleName, path=freshenedFilename)
                    self._log_plugin_trace(_msg, logging.ERROR)
            except Exception as err:
                _msg = _("Exception at plug-in method freshen_module_infos: {error}").format(error=err)
                self._log_plugin_trace(_msg, logging.ERROR)
        for moduleName in missingEnabledModules:
            self.remove_plugin_module(moduleName)
            # Try re-adding plugin modules by name (for plugins that moved from built-in to pip installed)
            moduleInfo = self.add_plugin_module(moduleName)
            if moduleInfo:
                self._plugin_config["modules"][moduleInfo["name"]] = moduleInfo
                self._load_module(moduleInfo)
                self._log_plugin_trace(_("Reloaded plugin that failed loading: {} {}").format(moduleName, moduleInfo), logging.INFO)
            else:
                self._log_plugin_trace(_("Removed plugin that failed loading (plugin may have been archived): {}").format(moduleName), logging.ERROR)
        self.save(self._controller)

    def get_controller(self):
        return self._controller

    def get_plugin_base(self):
        return self._plugin_base

    def _get_module_filename(self, moduleURL: str, reload: bool, normalize: bool, base: str | None) -> tuple[str | None, EntryPoint | None]:
        # TODO several directories, eg User Application Data
        moduleFilename = self._controller.webCache.getfilename(moduleURL, reload=reload, normalize=normalize, base=base)
        if moduleFilename:
            # `moduleURL` was mapped to a local filepath
            moduleFilename = self._plugin_locator.normalize_module_filename(moduleFilename)
            if moduleFilename:
                # `moduleFilename` normalized to an existing script
                return moduleFilename, None
        # `moduleFilename` did not map to a local filepath or did not normalize to a script
        # Try using `moduleURL` to search for pip-installed entry point
        entryPointRef = self._plugin_locator.get(self._plugin_base, moduleURL)
        if entryPointRef is not None:
            return entryPointRef.moduleFilename, entryPointRef.entryPoint
        return None, None

    def generate_module_info(self, moduleURL: str | None = None, entryPoint: EntryPoint | None = None, reload: bool = False, parentImportsSubtree: bool = False) -> dict | None:
        """
        Generates a module info dict based on the provided `moduleURL` or `entryPoint`
        Exactly one of "moduleURL" or "entryPoint" must be provided, otherwise a RuntimeError will be thrown.

        When `moduleURL` is provided, it will be treated as a file path and will attempt to be normalized and
        mapped to an existing plugin based on file location. If `moduleURL` fails to be mapped to an existing
        plugin on its own, it will instead be used to search for an entry point. If found, this function will
        proceed as if that entry point was provided for `entryPoint`.

        When `entryPoint` is provided, it's location and other details will be used to generate the module info
        dictionary.

        :param moduleURL: A URL that loosely maps to the file location of a plugin (may be transformed)
        :param entryPoint: An `EntryPoint` instance
        :param reload:
        :param parentImportsSubtree:
        :return:s
        """
        if (moduleURL is None) == (entryPoint is None):
            raise RuntimeError('Exactly one of "moduleURL" or "entryPoint" must be provided')
        if entryPoint:
            # If entry point is provided, use it to retrieve `moduleFilename`
            moduleFilename = moduleURL = entryPoint.load()()
        else:
            # Otherwise, we will verify the path before continuing
            moduleFilename, entryPoint = self._get_module_filename(moduleURL, reload=reload, normalize=True, base=self._plugin_base)

        if moduleFilename:
            try:
                self._log_plugin_trace("Scanning module for plug-in info: {}".format(moduleFilename), logging.INFO)
                moduleInfo = self._plugin_parser.parse_plugin_info(moduleURL, moduleFilename, entryPoint)
                if moduleInfo is None:
                    return None

                moduleDir, moduleName = os.path.split(moduleFilename)
                importURLs = moduleInfo["importURLs"]
                del moduleInfo["importURLs"]
                moduleImports = moduleInfo["moduleImports"]
                del moduleInfo["moduleImports"]
                _moduleImportsSubtree = False
                mergedImportURLs = []

                for _url in importURLs:
                    if _url.startswith("module_import"):
                        for moduleImport in moduleImports:
                            mergedImportURLs.append(moduleImport + ".py")
                        if _url == "module_import_subtree":
                            _moduleImportsSubtree = True
                    elif _url == "module_subtree":
                        for _dir in os.listdir(moduleDir):
                            _subtreeModule = os.path.join(moduleDir, _dir)
                            if os.path.isdir(_subtreeModule) and _dir != "__pycache__":
                                mergedImportURLs.append(_subtreeModule)
                    else:
                        mergedImportURLs.append(_url)
                if parentImportsSubtree and not _moduleImportsSubtree:
                    _moduleImportsSubtree = True
                    for moduleImport in moduleImports:
                        mergedImportURLs.append(moduleImport + ".py")
                imports = []
                for _url in mergedImportURLs:
                    if isAbsolute(_url) or os.path.isabs(_url):
                        _importURL = _url  # URL is absolute http or local file system
                    else:  # check if exists relative to this module's directory
                        _importURL = os.path.join(os.path.dirname(moduleURL), os.path.normpath(_url))
                        if not os.path.exists(_importURL):  # not relative to this plugin, assume standard plugin base
                            _importURL = _url  # module_module_info adjusts relative URL to plugin base
                    _importModuleInfo = self.generate_module_info(moduleURL=_importURL, reload=reload, parentImportsSubtree=_moduleImportsSubtree)
                    if _importModuleInfo:
                        _importModuleInfo["isImported"] = True
                        imports.append(_importModuleInfo)
                moduleInfo["imports"] = imports
                self._log_plugin_trace(f"Successful module plug-in info: {moduleFilename}", logging.INFO)
                return moduleInfo
            except Exception as err:
                _msg = _("Exception obtaining plug-in module info: {moduleFilename}\n{error}\n{traceback}").format(
                    error=err, moduleFilename=moduleFilename, traceback=traceback.format_tb(sys.exc_info()[2]))
                self._log_plugin_trace(_msg, logging.ERROR)
        return None

    def _load_module(self, moduleInfo: dict[str, Any], packagePrefix: str = "") -> None:
        name = moduleInfo['name']
        moduleURL = moduleInfo['moduleURL']

        moduleName, moduleDir, packageImportPrefix = _get_name_dir_prefix(
            controller=self._controller,
            pluginBase=self._plugin_base,
            moduleURL=moduleURL,
            packagePrefix=packagePrefix,
        )

        if all(p is None for p in [moduleName, moduleDir, packageImportPrefix]):
            self._controller.addToLog(message=_ERROR_MESSAGE_IMPORT_TEMPLATE.format(name), level=logging.ERROR)
        else:
            try:
                module = _find_and_load_module(moduleDir=moduleDir, moduleName=moduleName)
                pluginInfo = module.__pluginInfo__.copy()
                elementSubstitutionClasses = None
                if name == pluginInfo.get('name'):
                    pluginInfo["moduleURL"] = moduleURL
                    self._module_plugin_infos[name] = pluginInfo
                    if 'localeURL' in pluginInfo:
                        # set L10N internationalization in loaded module
                        localeDir = os.path.dirname(module.__file__) + os.sep + pluginInfo['localeURL']
                        try:
                            _gettext = gettext.translation(pluginInfo['localeDomain'], localeDir, getLanguageCodes())
                        except IOError:
                            _gettext = lambda x: x  # no translation
                    else:
                        _gettext = lambda x: x
                    for key, value in pluginInfo.items():
                        if key == 'name':
                            if name:
                                self._plugin_config['modules'][name] = moduleInfo
                        elif isinstance(value, types.FunctionType):
                            classModuleNames = self._plugin_config['classes'].setdefault(key, [])
                            if name and name not in classModuleNames:
                                classModuleNames.append(name)
                        if key == 'ModelObjectFactory.ElementSubstitutionClasses':
                            elementSubstitutionClasses = value
                    module._ = _gettext
                    self._plugin_config_changed = True
                if elementSubstitutionClasses:
                    try:
                        from arelle.ModelObjectFactory import elementSubstitutionModelClass
                        elementSubstitutionModelClass.update(elementSubstitutionClasses)
                    except Exception as err:
                        _msg = _("Exception loading plug-in {name}: processing ModelObjectFactory.ElementSubstitutionClasses").format(
                            name=name, error=err)
                        self._log_plugin_trace(_msg, logging.ERROR)
                for importModuleInfo in moduleInfo.get('imports', []):
                    self._load_module(importModuleInfo, packageImportPrefix)
            except (AttributeError, ImportError, FileNotFoundError, ModuleNotFoundError, TypeError, SystemError) as err:
                # Send a summary of the error to the logger and retain the stacktrace for stderr
                self._controller.addToLog(message=_ERROR_MESSAGE_IMPORT_TEMPLATE.format(name), level=logging.ERROR)

                _msg = _("Exception loading plug-in {name}: {error}\n{traceback}").format(
                    name=name, error=err, traceback=traceback.format_tb(sys.exc_info()[2]))
                self._log_plugin_trace(_msg, logging.ERROR)

    def plugin_class_methods(self, className: str) -> Iterator[Callable[..., Any]]:
        if not self._plugin_config:
            return
        if className in self._methods:
            pluginMethodsForClass = self._methods[className]
        else:
            # load all modules for class
            pluginMethodsForClass = []
            modulesNamesLoaded = set()
            if className in self._plugin_config["classes"]:
                for moduleName in self._plugin_config["classes"].get(className):
                    if moduleName and moduleName in self._plugin_config["modules"] and moduleName not in modulesNamesLoaded:
                        modulesNamesLoaded.add(moduleName)  # prevent multiply executing same class
                        moduleInfo = self._plugin_config["modules"][moduleName]
                        if moduleInfo["status"] == "enabled":
                            if moduleName not in self._module_plugin_infos:
                                self._load_module(moduleInfo)
                            if moduleName in self._module_plugin_infos:
                                pluginInfo = self._module_plugin_infos[moduleName]
                                if className in pluginInfo:
                                    pluginMethodsForClass.append(pluginInfo[className])
            self._methods[className] = pluginMethodsForClass
        for method in pluginMethodsForClass:
            yield method

    def add_plugin_module(self, name: str) -> dict[str, Any] | None:
        """
        Discover plugin entry points with given name.
        :param name: The name to search for
        :return: The module information dictionary, if added. Otherwise, None.
        """
        entryPointRef = self._plugin_locator.get(self._plugin_base, name)
        plugin_module_info = None
        if entryPointRef:
            plugin_module_info = self._create_module_info(entryPointRef)
        if not plugin_module_info or not plugin_module_info.get("name"):
            plugin_module_info = self.generate_module_info(moduleURL=name)
        if not plugin_module_info or not plugin_module_info.get("name"):
            return None
        name = plugin_module_info["name"]
        self.remove_plugin_module(name)  # remove any prior entry for this module

        def _addPluginSubModule(subModuleInfo: dict[str, Any]):
            """
            Inline function for recursively exploring module imports
            :param subModuleInfo: Module information to add.
            :return:
            """
            _name = subModuleInfo.get("name")
            if not _name:
                return
            # add classes
            for classMethod in subModuleInfo["classMethods"]:
                classMethods = self._plugin_config["classes"].setdefault(classMethod, [])
                _name = subModuleInfo["name"]
                if _name and _name not in classMethods:
                    classMethods.append(_name)
            for importModuleInfo in subModuleInfo.get('imports', []):
                _addPluginSubModule(importModuleInfo)
            self._plugin_config["modules"][_name] = subModuleInfo

        _addPluginSubModule(plugin_module_info)
        self._plugin_config_changed = True
        return plugin_module_info

    def reload_plugin_module(self, name):
        if name in self._plugin_config["modules"]:
            url = self._plugin_config["modules"][name].get("moduleURL")
            if url:
                moduleInfo = self.generate_module_info(moduleURL=url, reload=True)
                if moduleInfo:
                    self.add_plugin_module(url)
                    return True
        return False

    def remove_plugin_module(self, name):
        moduleInfo = self._plugin_config["modules"].get(name)
        if moduleInfo and name:
            def _remove_plugin_module(moduleInfo):
                _name = moduleInfo.get("name")
                if _name:
                    for classMethod in moduleInfo["classMethods"]:
                        classMethods = self._plugin_config["classes"].get(classMethod)
                        if classMethods and _name and _name in classMethods:
                            classMethods.remove(_name)
                            if not classMethods:  # list has become unused
                                del self._plugin_config["classes"][classMethod]  # remove class
                    for importModuleInfo in moduleInfo.get('imports', []):
                        _remove_plugin_module(importModuleInfo)
                    self._plugin_config["modules"].pop(_name, None)

            _remove_plugin_module(moduleInfo)
            self._plugin_config_changed = True
            return True
        return False  # unable to remove

    def _add_plugin_module_info(self, plugin_module_info: dict[str, Any]) -> dict[str, Any] | None:
        """
        Given a dictionary containing module information, loads plugin info into `pluginConfig`
        :param plugin_module_info: Dictionary of module info fields. See comment block in PluginManager.py for structure.
        :return: The module information dictionary, if added. Otherwise, None.
        """
