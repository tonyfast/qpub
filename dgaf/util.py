Path = type(__import__("pathlib").Path())


class File(Path):
    """a supercharged file object that make it is easy to dump and load data.

    the loaders and dumpers edit files in-place, these constraints may not apply to all systems.
    """

    def write(self, object):
        self.write_text(self.dump(object))

    def update(self, object):
        return self.write(merge(self.read(), object))

    def load(self):
        """a permissive method to load data from files and edit documents in place."""
        for cls in File.__subclasses__():
            if hasattr(cls, "_suffixes"):
                if self.suffix in cls._suffixes:
                    return cls.load(self)
        else:
            raise TypeError(f"Can't load type with suffix: {self.suffix}")

    def dump(self, object):
        """a permissive method to dump data from files and edit documents in place."""
        for cls in File.__subclasses__():
            if hasattr(cls, "_suffixes"):
                if self.suffix in cls._suffixes:
                    return cls.dump(self, object)
        else:
            raise TypeError(f"Can't dump type with suffix: {self.suffix}")

    __add__, read = update, load


class Convention(File):
    """a convention indicates explicit or implicit filename and directory conventions.

    the conventions were introduced to separate non-canonical content from canonical configuration files.
    if content and configurations are mixed they doit will experience break with cyclic graphs.
    """


LINT_DEFAULTS = {
    None: [
        dict(
            repo="https://github.com/pre-commit/pre-commit-hooks",
            rev="v2.3.0",
            hooks=[dict(id="end-of-file-fixer"), dict(id="trailing-whitespace")],
        )
    ],
    ".yml": [
        dict(
            repo="https://github.com/pre-commit/pre-commit-hooks",
            hooks=[dict(id="check-yaml")],
        )
    ],
    ".py": [
        dict(
            repo="https://github.com/psf/black",
            rev="19.3b0",
            hooks=[dict(id="black")],
        ),
        dict(
            repo="https://github.com/life4/flakehell",
            rev="v.0.7.0",
            hooks=[dict(id="flakehell")],
        ),
    ],
}

LINT_DEFAULTS[".yaml"] = LINT_DEFAULTS[".yml"]


def rough_source(nb):
    """extract a rough version of the source in notebook to infer files from"""

    if isinstance(nb, str):
        nb = __import__("json").loads(nb)

    return "\n".join(
        __import__("textwrap").dedent("".join(x["source"]))
        for x in nb.get("cells", [])
        if x["cell_type"] == "code"
    )


async def infer(file):
    """infer imports from different kinds of files."""
    async with __import__("aiofiles").open(file, "r") as f:
        if file.suffix not in {".py", ".ipynb", ".md", ".rst"}:
            return file, {}
        source = await f.read()
        if file.suffix == ".ipynb":
            source = rough_source(source)
        try:
            return (
                file,
                __import__("depfinder").main.get_imported_libs(source).describe(),
            )
        except SyntaxError:
            return file, {}


async def infer_files(files):
    return dict(
        await __import__("asyncio").gather(*(infer(file) for file in map(Path, files)))
    )


def gather_imports(files):
    """"""
    if "depfinder" not in __import__("sys").modules:
        yaml = __import__("yaml")

        dir = Path(__import__("appdirs").user_data_dir("qpub"))
        __import__("requests_cache").install_cache(str(dir / "qpub"))
        dir.mkdir(parents=True, exist_ok=True)
        if not hasattr(yaml, "CSafeLoader"):
            yaml.CSafeLoader = yaml.SafeLoader
        __import__("depfinder")

        __import__("requests_cache").uninstall_cache()
    return dict(__import__("asyncio").run(infer_files(files)))


def merge(*args):
    if not args:
        return {}
    if len(args) == 1:
        return args[0]
    a, b, *args = args
    if args:
        b = __import__("functools").reduce(merge, (b, *args))
    if hasattr(a, "items"):
        for k, v in a.items():
            if k in b:
                a[k] = merge(v, b[k])
        for k, v in b.items():
            if k not in a:
                try:
                    a[k] = v
                except ValueError as exception:
                    if hasattr(a, "add_section"):
                        a.add_section(k)
                        a[k].update(v)
                    else:
                        raise exception
        return a
    if isinstance(a, tuple):
        return a + tuple(x for x in b if x not in a)
    if isinstance(a, list):
        return a + list(x for x in b if x not in a)
    if isinstance(a, set):
        return list(sorted(set(a).union(b)))
    return a or b


def merged_imports(files):
    results = merge(*gather_imports(files).values())
    return sorted(
        set(list(results.get("required", [])) + list(results.get("questionable", [])))
    )


def import_to_pip(list):
    global IMPORT_TO_PIP
    if not IMPORT_TO_PIP:
        IMPORT_TO_PIP = {
            x["import_name"]: x["pypi_name"]
            for x in __import__("depfinder").utils.mapping_list
        }
    return [IMPORT_TO_PIP.get(x, x) for x in list]


def pypi_to_conda(list):
    global PIP_TO_CONDA
    if not PIP_TO_CONDA:
        PIP_TO_CONDA = {
            x["import_name"]: x["conda_name"]
            for x in __import__("depfinder").utils.mapping_list
        }
    return [PIP_TO_CONDA.get(x, x) for x in list]


# file loader loader/dumper functions


def ensure_trailing_eol(callable):
    """a decorator to comply with our linting opinion."""
    import functools

    @functools.wraps(callable)
    def main(object):
        str = callable(object)
        return str.rstrip() + "\n"

    return main


def load_configparser(str):
    object = __import__("configparser").ConfigParser(default_section=None)
    object.read_string(str)
    return expand_cfg(object)


def load_configupdater(str):
    object = __import__("configupdater").ConfigUpdater()
    object.read_string(str)
    return expand_cfg(object)


@ensure_trailing_eol
def dump_config__er(object):
    next = __import__("io").StringIO()
    object = compact_cfg(object)
    if isinstance(object, dict):
        import configparser

        parser = configparser.ConfigParser(default_section=None)
        parser.read_dict(object)
        object = parser
    object.write(next)
    return next.getvalue()


def expand_cfg(object):
    """special conditions for config files so configparser and configuupdates work together."""
    for main, section in object.items():
        for key, value in section.items():
            if isinstance(value, str) and value.startswith("\n"):
                value = __import__("textwrap").dedent(value).splitlines()[1:]
            object[main][key] = value
    return object


def compact_cfg(object):
    for main, section in object.items():
        for key, value in section.items():
            if isinstance(value, list):
                value = __import__("textwrap").indent("\n".join(value), " " * 4)
            object[main][key] = value
    return object


def load_text(str):
    return [x for x in str.splitlines()]


@ensure_trailing_eol
def dump_text(object):
    return "\n".join(object)


def load_toml(str):
    return __import__("toml").loads(str)


def load_tomlkit(str):
    return __import__("tomlkit").parse(str)


@ensure_trailing_eol
def dump_toml(object):
    try:
        tomlkit = __import__("tomlkit")
        return tomlkit.dumps(object)
    except ModuleNotFoundError:
        pass
    return __import__("toml").dumps(object)


def load_yaml(str):
    return __import__("yaml").safe_load(str)


def load_ruamel(str):
    object = __import__("ruamel.yaml").yaml.YAML()
    return object.load(str)


@ensure_trailing_eol
def dump_yaml(object):
    try:
        ruamel = __import__("ruamel.yaml").yaml
        if isinstance(object, ruamel.YAML):
            next = __import__("io").StringIO()
            object.dump(next)
            return next.getvalue()
    except ModuleNotFoundError:
        pass
    return __import__("yaml").safe_dump(object)


def to_dict(object):
    if hasattr(object, "items"):
        data = {}
        for k, v in object.items():
            if k is None:
                continue
            data[k] = to_dict(v)
        else:
            return data
    return object


class INI(File):
    """dump and load ini files in place."""

    _suffixes = ".ini", ".cfg"

    def load(self):
        # try:
        #     __import__("configupdater")
        #     callable = load_configupdater
        # except ModuleNotFoundError:
        #     callable = load_configparser
        try:
            return callable(self.read_text())
        except FileNotFoundError:
            return callable("")

    def dump(self, object):
        return dump_config__er(object)


class TOML(File):
    """dump and load toml files in place."""

    _suffixes = (".toml",)

    def load(self):
        try:
            __import__("tomlkit")
            callable = load_tomlkit
        except ModuleNotFoundError:
            callable = load_toml
        try:
            return callable(self.read_text())
        except FileNotFoundError:
            return callable("")

    def dump(self, object):
        return dump_toml(object)


class YML(File):
    """dump and load yml files in place."""

    _suffixes = ".yaml", ".yml"

    def load(self):
        try:
            __import__("ruamel.yaml")
            callable = load_ruamel
        except ModuleNotFoundError:
            callable = load_yaml
        try:
            return callable(self.read_text())
        except FileNotFoundError:
            return callable("{}")

    def dump(self, object):
        return dump_yaml(object)


IMPORT_TO_PIP = None
PIP_TO_CONDA = None
