"""The module defines the abstract interface for dealing tool dependency resolution plugins."""
from abc import (
    ABCMeta,
    abstractmethod,
    abstractproperty,
)

from galaxy.util.dictifiable import Dictifiable

from ..requirements import ToolRequirement


class DependencyResolver(Dictifiable, object):
    """Abstract description of a technique for resolving container images for tool execution."""

    # Keys for dictification.
    dict_collection_visible_keys = ['resolver_type', 'resolves_simple_dependencies']
    # A "simple" dependency is one that does not depend on the the tool
    # resolving the dependency. Classic tool shed dependencies are non-simple
    # because the repository install context is used in dependency resolution
    # so the same requirement tags in different tools will have very different
    # resolution.
    disabled = False
    resolves_simple_dependencies = True
    config_options = {}
    __metaclass__ = ABCMeta

    @abstractmethod
    def resolve( self, requirement, **kwds ):
        """Given inputs describing dependency in the abstract yield a Dependency object.

        The Dependency object describes various attributes (script, bin,
        version) used to build scripts with the dependency availble. Here
        script is the env.sh file to source before running a job, if that is
        not found the bin directory will be appended to the path (if it is
        not ``None``). Finally, version is the resolved tool dependency
        version (which may differ from requested version for instance if the
        request version is 'default'.)
        """


class MultipleDependencyResolver:
    """Variant of DependencyResolver that can optionally resolve multiple dependencies together."""

    @abstractmethod
    def resolve_all( self, requirements, **kwds ):
        """Given multiple requirements yield Dependency objects if and only if they may all be resolved together.
        """


class ListableDependencyResolver:
    """ Mix this into a ``DependencyResolver`` and implement to indicate
    the dependency resolver can iterate over its dependencies and generate
    requirements.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def list_dependencies(self):
        """ List the "simple" requirements that may be resolved "exact"-ly
        by this dependency resolver.
        """

    def _to_requirement(self, name, version=None):
        return ToolRequirement(name=name, type="package", version=version)


class SpecificationAwareDependencyResolver:
    """Mix this into a :class:`DependencyResolver` to implement URI specification matching.

    Allows adapting generic requirements to more specific URIs - to tailor name
    or version to specified resolution system.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def find_specification(self, specs):
        """Find closest matching specification for discovered resolver."""


class SpecificationPatternDependencyResolver:
    """Implement the :class:`SpecificationAwareDependencyResolver` with a regex pattern."""

    @abstractproperty
    def _specification_pattern(self):
        """Pattern of URI to match against."""

    def find_specification(self, specs):
        pattern = self._specification_pattern
        for spec in specs:
            if pattern.match(spec.uri):
                return spec
        return None

    def resolve_specs(self, requirement):
        name = requirement.name
        version = requirement.version
        specs = requirement.specs

        spec = self.find_specification(specs)
        if spec is not None:
            name = spec.short_name
            version = spec.version or version

            requirement = requirement.copy()
            requirement.name = name
            requirement.version = version

        return requirement


class InstallableDependencyResolver:
    """ Mix this into a ``DependencyResolver`` and implement to indicate
    the dependency resolver can attempt to install new dependencies.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def install_dependency(self, name, version, type, **kwds):
        """ Attempt to install this dependency if a recipe to do so
        has been registered in some way.
        """


class Dependency(Dictifiable, object):
    dict_collection_visible_keys = ['dependency_type', 'exact', 'name', 'version', 'cacheable']
    __metaclass__ = ABCMeta
    cacheable = False

    @abstractmethod
    def shell_commands( self, requirement ):
        """
        Return shell commands to enable this dependency.
        """

    @abstractproperty
    def exact( self ):
        """ Return true if version information wasn't discarded to resolve
        the dependency.
        """

    @property
    def resolver_msg(self):
        """
        Return a message describing this dependency
        """
        return "Using dependency %s version %s of type %s" % (self.name, self.version, self.dependency_type)


class NullDependency( Dependency ):
    dependency_type = None
    exact = True

    def __init__(self, version=None, name=None):
        self.version = version
        self.name = name

    @property
    def resolver_msg(self):
        """
        Return a message describing this dependency
        """
        return "Dependency %s not found." % self.name

    def shell_commands( self, requirement ):
        return None


class DependencyException(Exception):
    pass
