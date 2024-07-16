"""
See COPYRIGHT.md for copyright information.
"""
from __future__ import annotations

import ast
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
from collections import OrderedDict, defaultdict
from importlib.metadata import EntryPoint
from pathlib import Path
from typing import Any, Iterator, Callable, TYPE_CHECKING

from arelle import FileSource
from arelle.EntryPointRef import EntryPointFactory
from arelle.Locale import getLanguageCodes
from arelle.UrlUtil import isAbsolute

if TYPE_CHECKING:
    from .Cntlr import Cntlr

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


class PluginContext:
    def __init__(self, cntlr):
        self._cntlr = cntlr
        self._pluginJsonFile = None
        self._pluginConfig = None
        self._pluginConfigChanged = False
        self._pluginTraceFileLogger = None
        self._modulePluginInfos = {}
        self._pluginMethodsForClasses = {}
        self._pluginBase = None
        self._EMPTYLIST = []
        self._entry_point_factory = EntryPointFactory(self)

    def init(self, loadPluginConfig: bool = True) -> None:
        if PLUGIN_TRACE_FILE:
            self._pluginTraceFileLogger = logging.getLogger(__name__)
            self._pluginTraceFileLogger.propagate = False
            handler = logging.FileHandler(PLUGIN_TRACE_FILE)
            formatter = logging.Formatter('%(asctime)s.%(msecs)03dz [%(levelname)s] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')
            handler.setFormatter(formatter)
            handler.setLevel(PLUGIN_TRACE_LEVEL)
            self._pluginTraceFileLogger.addHandler(handler)
        self._pluginConfigChanged = False
        self._pluginBase = self._cntlr.pluginDir + os.sep
        if loadPluginConfig:
            try:
                self._pluginJsonFile = self._cntlr.userAppDir + os.sep + "plugins.json"
                with io.open(self._pluginJsonFile, 'rt', encoding='utf-8') as f:
                    self._pluginConfig = json.load(f)
                self.freshenModuleInfos()
            except Exception:
                pass  # on GAE no userAppDir, will always come here
        if not self._pluginConfig:
            self._pluginConfig = {  # savable/reloadable plug in configuration
                "modules": {},  # dict of moduleInfos by module name
                "classes": {}  # dict by class name of list of class modules in execution order
            }
            self._pluginConfigChanged = False  # don't save until something is added to pluginConfig
        self._modulePluginInfos = {}  # dict of loaded module pluginInfo objects by module names
        self._pluginMethodsForClasses = {}  # dict by class of list of ordered callable function objects

    def reset(self) -> None:
        if self._modulePluginInfos:
            self._modulePluginInfos.clear()  # dict of loaded module pluginInfo objects by module names
        if self._pluginMethodsForClasses:
            self._pluginMethodsForClasses.clear()  # dict by class of list of ordered callable function objects

    def orderedPluginConfig(self):
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
            for moduleName, moduleInfo in sorted(self._pluginConfig['modules'].items())
        )
        classes_dict = OrderedDict(sorted(self._pluginConfig['classes'].items()))
        return OrderedDict((
            ('modules', modules_dict),
            ('classes', classes_dict)
        ))

    def save(self, cntlr) -> None:
        # TODO: Should probably be using self._cntlr?
        if self._pluginConfigChanged and cntlr.hasFileSystem and not cntlr.disablePersistentConfig:
            self._pluginJsonFile = cntlr.userAppDir + os.sep + "plugins.json"
            with io.open(self._pluginJsonFile, 'wt', encoding='utf-8') as f:
                jsonStr = str(json.dumps(self.orderedPluginConfig(), ensure_ascii=False, indent=2))  # might not be unicode in 2.7
                f.write(jsonStr)
            self._pluginConfigChanged = False

    def close(self):
        self._pluginConfig.clear()
        self._modulePluginInfos.clear()
        self._pluginMethodsForClasses.clear()

    def logPluginTrace(self, message: str, level: int) -> None:
        """
        If plugin trace file logging is configured, logs `message` to it.
        Only logs to controller logger if log is an error.
        :param message: Message to be logged
        :param level: Log level of message (e.g. logging.INFO)
        """
        if self._pluginTraceFileLogger:
            self._pluginTraceFileLogger.log(level, message)
        if level >= logging.ERROR:
            self._cntlr.addToLog(message=message, level=level, messageCode='arelle:pluginLoadingError')

    def modulesWithNewerFileDates(self):
        names = set()
        for moduleName, moduleInfo in self._pluginConfig["modules"].items():
            freshenedFilename = self._cntlr.webCache.getfilename(moduleInfo["moduleURL"], checkModifiedTime=True, normalize=True, base=self._pluginBase)
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
                    self.logPluginTrace(_msg, logging.ERROR)
            except Exception as err:
                _msg = _("Exception at plug-in method modulesWithNewerFileDates: {error}").format(error=err)
                self.logPluginTrace(_msg, logging.ERROR)
        return names

    def freshenModuleInfos(self):
        # for modules with different date-times, re-load module info
        missingEnabledModules = []
        for moduleName, moduleInfo in self._pluginConfig["modules"].items():
            moduleEnabled = moduleInfo["status"] == "enabled"
            freshenedFilename = self._cntlr.webCache.getfilename(moduleInfo["moduleURL"], checkModifiedTime=True, normalize=True, base=self._pluginBase)
            try:  # check if moduleInfo cached may differ from referenced moduleInfo
                if os.path.isdir(freshenedFilename):  # if freshenedFilename is a directory containing an __ini__.py file, open that instead
                    if os.path.isfile(os.path.join(freshenedFilename, "__init__.py")):
                        freshenedFilename = os.path.join(freshenedFilename, "__init__.py")
                elif not freshenedFilename.endswith(".py") and not os.path.exists(freshenedFilename) and os.path.exists(freshenedFilename + ".py"):
                    freshenedFilename += ".py"  # extension module without .py suffix
                if os.path.exists(freshenedFilename):
                    if moduleInfo["fileDate"] != time.strftime('%Y-%m-%dT%H:%M:%S UTC', time.gmtime(os.path.getmtime(freshenedFilename))):
                        freshenedModuleInfo = self.moduleModuleInfo(moduleURL=moduleInfo["moduleURL"], reload=True)
                        if freshenedModuleInfo is not None:
                            if freshenedModuleInfo["name"] == moduleName:
                                self._pluginConfig["modules"][moduleName] = freshenedModuleInfo
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
                    self.logPluginTrace(_msg, logging.ERROR)
            except Exception as err:
                _msg = _("Exception at plug-in method freshenModuleInfos: {error}").format(error=err)
                self.logPluginTrace(_msg, logging.ERROR)
        for moduleName in missingEnabledModules:
            self.removePluginModule(moduleName)
            # Try re-adding plugin modules by name (for plugins that moved from built-in to pip installed)
            moduleInfo = self.addPluginModule(moduleName)
            if moduleInfo:
                self._pluginConfig["modules"][moduleInfo["name"]] = moduleInfo
                self.loadModule(moduleInfo)
                self.logPluginTrace(_("Reloaded plugin that failed loading: {} {}").format(moduleName, moduleInfo), logging.INFO)
            else:
                self.logPluginTrace(_("Removed plugin that failed loading (plugin may have been archived): {}").format(moduleName), logging.ERROR)
        self.save(self._cntlr)

    @property
    def controller(self):
        return self._cntlr

    @property
    def pluginBase(self):
        return self._pluginBase

    def normalizeModuleFilename(self, moduleFilename: str) -> str | None:
        """
        Attempts to find python script as plugin entry point.
        A value will be returned
          if `moduleFilename` exists as-is,
          if `moduleFilename` is a directory containing __init__.py, or
          if `moduleFilename` with .py extension added exists
        :param moduleFilename:
        :return: Normalized filename, if exists
        """
        if os.path.isfile(moduleFilename):
            # moduleFilename exists as-is, use it
            return moduleFilename
        if os.path.isdir(moduleFilename):
            # moduleFilename is a directory, only valid script is __init__.py contained inside
            initPath = os.path.join(moduleFilename, "__init__.py")
            if os.path.isfile(initPath):
                return initPath
            else:
                return None
        if not moduleFilename.endswith(".py"):
            # moduleFilename is not a file or directory, try adding .py
            pyPath = moduleFilename + ".py"
            if os.path.exists(pyPath):
                return pyPath
        return None

    def getModuleFilename(self, moduleURL: str, reload: bool, normalize: bool, base: str | None) -> tuple[str | None, EntryPoint | None]:
        # TODO several directories, eg User Application Data
        moduleFilename = self._cntlr.webCache.getfilename(moduleURL, reload=reload, normalize=normalize, base=base)
        if moduleFilename:
            # `moduleURL` was mapped to a local filepath
            moduleFilename = self.normalizeModuleFilename(moduleFilename)
            if moduleFilename:
                # `moduleFilename` normalized to an existing script
                return moduleFilename, None
        # `moduleFilename` did not map to a local filepath or did not normalize to a script
        # Try using `moduleURL` to search for pip-installed entry point
        entryPointRef = self._entry_point_factory.get(moduleURL)
        if entryPointRef is not None:
            return entryPointRef.moduleFilename, entryPointRef.entryPoint
        return None, None

    def parsePluginInfo(self, moduleURL: str, moduleFilename: str, entryPoint: EntryPoint | None) -> dict | None:
        moduleDir, moduleName = os.path.split(moduleFilename)
        f = FileSource.openFileStream(self._cntlr, moduleFilename)
        tree = ast.parse(f.read(), filename=moduleFilename)
        constantStrings = {}
        functionDefNames = set()
        methodDefNamesByClass = defaultdict(set)
        moduleImports = []
        moduleInfo = {"name": None}
        isPlugin = False
        for item in tree.body:
            if isinstance(item, ast.Assign):
                attr = item.targets[0].id
                if attr == "__pluginInfo__":
                    isPlugin = True
                    f.close()
                    classMethods = []
                    importURLs = []
                    for i, key in enumerate(item.value.keys):
                        _key = key.value
                        _value = item.value.values[i]
                        _valueType = _value.__class__.__name__
                        if _key == "import":
                            if _valueType == 'Constant':
                                importURLs.append(_value.value)
                            elif _valueType in ("List", "Tuple"):
                                for elt in _value.elts:
                                    importURLs.append(elt.value)
                        elif _valueType == 'Constant':
                            moduleInfo[_key] = _value.value
                        elif _valueType == 'Name':
                            if _value.id in constantStrings:
                                moduleInfo[_key] = constantStrings[_value.id]
                            elif _value.id in functionDefNames:
                                classMethods.append(_key)
                        elif _valueType == 'Attribute':
                            if _value.attr in methodDefNamesByClass[_value.value.id]:
                                classMethods.append(_key)
                        elif _valueType in ("List", "Tuple"):
                            values = [elt.value for elt in _value.elts]
                            if _key == "imports":
                                importURLs = values
                            else:
                                moduleInfo[_key] = values

                    moduleInfo['classMethods'] = classMethods
                    moduleInfo['importURLs'] = importURLs
                    moduleInfo["moduleURL"] = moduleURL
                    moduleInfo["path"] = moduleFilename
                    moduleInfo["status"] = 'enabled'
                    moduleInfo["fileDate"] = time.strftime('%Y-%m-%dT%H:%M:%S UTC', time.gmtime(os.path.getmtime(moduleFilename)))
                    if entryPoint:
                        moduleInfo["moduleURL"] = moduleFilename  # pip-installed plugins need absolute filepath
                        moduleInfo["entryPoint"] = {
                            "module": getattr(entryPoint, 'module', None),  # TODO: Simplify after Python 3.8 retired
                            "name": entryPoint.name,
                            "version": entryPoint.dist.version if hasattr(entryPoint, 'dist') else None,
                        }
                        if not moduleInfo.get("version"):
                            moduleInfo["version"] = entryPoint.dist.version  # If no explicit version, retrieve from entry point
                elif isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):  # possible constant used in plugininfo, such as VERSION
                    for assignmentName in item.targets:
                        constantStrings[assignmentName.id] = item.value.value
            elif isinstance(item, ast.ImportFrom):
                if item.level == 1:  # starts with .
                    if item.module is None:  # from . import module1, module2, ...
                        for importee in item.names:
                            if importee.name == '*':  # import all submodules
                                for _file in os.listdir(moduleDir):
                                    if _file != moduleName and os.path.isfile(_file) and _file.endswith(".py"):
                                        moduleImports.append(_file)
                            elif (os.path.isfile(os.path.join(moduleDir, importee.name + ".py"))
                                  and importee.name not in moduleImports):
                                moduleImports.append(importee.name)
                    else:
                        modulePkgs = item.module.split('.')
                        modulePath = os.path.join(*modulePkgs)
                        if (os.path.isfile(os.path.join(moduleDir, modulePath) + ".py")
                                and modulePath not in moduleImports):
                            moduleImports.append(modulePath)
                        for importee in item.names:
                            _importeePfxName = os.path.join(modulePath, importee.name)
                            if (os.path.isfile(os.path.join(moduleDir, _importeePfxName) + ".py")
                                    and _importeePfxName not in moduleImports):
                                moduleImports.append(_importeePfxName)
            elif isinstance(item, ast.FunctionDef):  # possible functionDef used in plugininfo
                functionDefNames.add(item.name)
            elif isinstance(item, ast.ClassDef):  # possible ClassDef used in plugininfo
                for classItem in item.body:
                    if isinstance(classItem, ast.FunctionDef):
                        methodDefNamesByClass[item.name].add(classItem.name)
        moduleInfo["moduleImports"] = moduleImports
        f.close()
        return moduleInfo if isPlugin else None

    def moduleModuleInfo(self, moduleURL: str | None = None, entryPoint: EntryPoint | None = None, reload: bool = False, parentImportsSubtree: bool = False) -> dict | None:
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
            moduleFilename, entryPoint = self.getModuleFilename(moduleURL, reload=reload, normalize=True, base=self._pluginBase)

        if moduleFilename:
            try:
                self.logPluginTrace("Scanning module for plug-in info: {}".format(moduleFilename), logging.INFO)
                moduleInfo = self.parsePluginInfo(moduleURL, moduleFilename, entryPoint)
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
                            _importURL = _url  # moduleModuleInfo adjusts relative URL to plugin base
                    _importModuleInfo = self.moduleModuleInfo(moduleURL=_importURL, reload=reload, parentImportsSubtree=_moduleImportsSubtree)
                    if _importModuleInfo:
                        _importModuleInfo["isImported"] = True
                        imports.append(_importModuleInfo)
                moduleInfo["imports"] = imports
                self.logPluginTrace(f"Successful module plug-in info: {moduleFilename}", logging.INFO)
                return moduleInfo
            except Exception as err:
                _msg = _("Exception obtaining plug-in module info: {moduleFilename}\n{error}\n{traceback}").format(
                    error=err, moduleFilename=moduleFilename, traceback=traceback.format_tb(sys.exc_info()[2]))
                self.logPluginTrace(_msg, logging.ERROR)
        return None

    def moduleInfo(self, pluginInfo):
        moduleInfo = {}
        for name, value in pluginInfo.items():
            if isinstance(value, str):
                moduleInfo[name] = value
            elif isinstance(value, types.FunctionType):
                if 'classes' not in moduleInfo:
                    classes = []
                    moduleInfo['classes'] = classes
                else:
                    classes = moduleInfo['classes']
                classes.append(name)

    def loadModule(self, moduleInfo: dict[str, Any], packagePrefix: str = "") -> None:
        name = moduleInfo['name']
        moduleURL = moduleInfo['moduleURL']

        moduleName, moduleDir, packageImportPrefix = _get_name_dir_prefix(
            controller=self._cntlr,
            pluginBase=self._pluginBase,
            moduleURL=moduleURL,
            packagePrefix=packagePrefix,
        )

        if all(p is None for p in [moduleName, moduleDir, packageImportPrefix]):
            self._cntlr.addToLog(message=_ERROR_MESSAGE_IMPORT_TEMPLATE.format(name), level=logging.ERROR)
        else:
            try:
                module = _find_and_load_module(moduleDir=moduleDir, moduleName=moduleName)
                pluginInfo = module.__pluginInfo__.copy()
                elementSubstitutionClasses = None
                if name == pluginInfo.get('name'):
                    pluginInfo["moduleURL"] = moduleURL
                    self._modulePluginInfos[name] = pluginInfo
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
                                self._pluginConfig['modules'][name] = moduleInfo
                        elif isinstance(value, types.FunctionType):
                            classModuleNames = self._pluginConfig['classes'].setdefault(key, [])
                            if name and name not in classModuleNames:
                                classModuleNames.append(name)
                        if key == 'ModelObjectFactory.ElementSubstitutionClasses':
                            elementSubstitutionClasses = value
                    module._ = _gettext
                    self._pluginConfigChanged = True
                if elementSubstitutionClasses:
                    try:
                        from arelle.ModelObjectFactory import elementSubstitutionModelClass
                        elementSubstitutionModelClass.update(elementSubstitutionClasses)
                    except Exception as err:
                        _msg = _("Exception loading plug-in {name}: processing ModelObjectFactory.ElementSubstitutionClasses").format(
                            name=name, error=err)
                        self.logPluginTrace(_msg, logging.ERROR)
                for importModuleInfo in moduleInfo.get('imports', []):
                    self.loadModule(importModuleInfo, packageImportPrefix)
            except (AttributeError, ImportError, FileNotFoundError, ModuleNotFoundError, TypeError, SystemError) as err:
                # Send a summary of the error to the logger and retain the stacktrace for stderr
                self._cntlr.addToLog(message=_ERROR_MESSAGE_IMPORT_TEMPLATE.format(name), level=logging.ERROR)

                _msg = _("Exception loading plug-in {name}: {error}\n{traceback}").format(
                    name=name, error=err, traceback=traceback.format_tb(sys.exc_info()[2]))
                self.logPluginTrace(_msg, logging.ERROR)

    def pluginClassMethods(self, className: str) -> Iterator[Callable[..., Any]]:
        if not self._pluginConfig:
            return
        if className in self._pluginMethodsForClasses:
            pluginMethodsForClass = self._pluginMethodsForClasses[className]
        else:
            # load all modules for class
            pluginMethodsForClass = []
            modulesNamesLoaded = set()
            if className in self._pluginConfig["classes"]:
                for moduleName in self._pluginConfig["classes"].get(className):
                    if moduleName and moduleName in self._pluginConfig["modules"] and moduleName not in modulesNamesLoaded:
                        modulesNamesLoaded.add(moduleName)  # prevent multiply executing same class
                        moduleInfo = self._pluginConfig["modules"][moduleName]
                        if moduleInfo["status"] == "enabled":
                            if moduleName not in self._modulePluginInfos:
                                self.loadModule(moduleInfo)
                            if moduleName in self._modulePluginInfos:
                                pluginInfo = self._modulePluginInfos[moduleName]
                                if className in pluginInfo:
                                    pluginMethodsForClass.append(pluginInfo[className])
            self._pluginMethodsForClasses[className] = pluginMethodsForClass
        for method in pluginMethodsForClass:
            yield method

    def addPluginModule(self, name: str) -> dict[str, Any] | None:
        """
        Discover plugin entry points with given name.
        :param name: The name to search for
        :return: The module information dictionary, if added. Otherwise, None.
        """
        entryPointRef = self._entry_point_factory.get(name)
        pluginModuleInfo = None
        if entryPointRef:
            pluginModuleInfo = self._entry_point_factory.create_module_info(entryPointRef)
        if not pluginModuleInfo or not pluginModuleInfo.get("name"):
            pluginModuleInfo = self.moduleModuleInfo(moduleURL=name)
        return self.addPluginModuleInfo(pluginModuleInfo)

    def reloadPluginModule(self, name):
        if name in self._pluginConfig["modules"]:
            url = self._pluginConfig["modules"][name].get("moduleURL")
            if url:
                moduleInfo = self.moduleModuleInfo(moduleURL=url, reload=True)
                if moduleInfo:
                    self.addPluginModule(url)
                    return True
        return False

    def removePluginModule(self, name):
        moduleInfo = self._pluginConfig["modules"].get(name)
        if moduleInfo and name:
            def _removePluginModule(moduleInfo):
                _name = moduleInfo.get("name")
                if _name:
                    for classMethod in moduleInfo["classMethods"]:
                        classMethods = self._pluginConfig["classes"].get(classMethod)
                        if classMethods and _name and _name in classMethods:
                            classMethods.remove(_name)
                            if not classMethods:  # list has become unused
                                del self._pluginConfig["classes"][classMethod]  # remove class
                    for importModuleInfo in moduleInfo.get('imports', []):
                        _removePluginModule(importModuleInfo)
                    self._pluginConfig["modules"].pop(_name, None)

            _removePluginModule(moduleInfo)
            self._pluginConfigChanged = True
            return True
        return False  # unable to remove

    def addPluginModuleInfo(self, plugin_module_info: dict[str, Any]) -> dict[str, Any] | None:
        """
        Given a dictionary containing module information, loads plugin info into `pluginConfig`
        :param plugin_module_info: Dictionary of module info fields. See comment block in PluginManager.py for structure.
        :return: The module information dictionary, if added. Otherwise, None.
        """
        if not plugin_module_info or not plugin_module_info.get("name"):
            return None
        name = plugin_module_info["name"]
        self.removePluginModule(name)  # remove any prior entry for this module

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
                classMethods = self._pluginConfig["classes"].setdefault(classMethod, [])
                _name = subModuleInfo["name"]
                if _name and _name not in classMethods:
                    classMethods.append(_name)
            for importModuleInfo in subModuleInfo.get('imports', []):
                _addPluginSubModule(importModuleInfo)
            self._pluginConfig["modules"][_name] = subModuleInfo

        _addPluginSubModule(plugin_module_info)
        self._pluginConfigChanged = True
        return plugin_module_info
